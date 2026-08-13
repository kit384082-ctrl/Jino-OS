"""The VBE framebuffer console.

The text buffer at 0xB8000 stays the record of what is on screen; the
framebuffer is painted from it.  These tests check the pixels actually
say what the text buffer says, because a console nobody can read is
worse than no console at all.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

from conftest import boot_with

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

GLYPH_W = 8
GLYPH_H = 16
CON_COLS = 80
CON_ROWS = 25

FONT_FIRST = 32
FONT_LAST = 126

DESKTOP_COLOUR = (0x1E, 0x3A, 0x5F)
BG_COLOUR = (0x0C, 0x10, 0x18)
TITLE_COLOUR = (0x2C, 0x50, 0x84)


def kernel_symbols() -> dict:
    """Symbol table of the linked kernel."""
    import subprocess

    nm = subprocess.run(
        ["nm", str(ROOT / "build" / "kernel.elf")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {
        parts[2]: int(parts[0], 16)
        for parts in (line.split() for line in nm.splitlines())
        if len(parts) == 3
    }


def parse_font(path) -> dict:
    """The glyph bitmaps, straight out of the generated source."""
    glyphs = {}
    for line in path.read_text().splitlines():
        if "db" not in line or ";" not in line:
            continue
        data, comment = line.split(";", 1)
        if "db" not in data:
            continue
        code = comment.split()[0]
        if not code.isdigit():
            continue
        rows = [
            int(value, 16)
            for value in data.split("db", 1)[1].strip().split(",")
        ]
        if len(rows) == GLYPH_H:
            glyphs[int(code)] = rows
    return glyphs


def pixel(machine, x: int, y: int) -> tuple[int, int, int]:
    """The colour at a screen position, as (r, g, b)."""
    import simulate

    offset = machine.framebuffer + y * simulate.FB_PITCH + x * 4
    blue, green, red = machine.ram[offset : offset + 3]
    return (red, green, blue)


def console_origin(machine) -> tuple[int, int]:
    """Top left corner of the console window, in pixels."""
    import simulate

    return (
        (simulate.FB_WIDTH - CON_COLS * GLYPH_W) // 2,
        (simulate.FB_HEIGHT - CON_ROWS * GLYPH_H) // 2,
    )


def cell_is_blank(machine, row: int, col: int) -> bool:
    """True when a character cell is entirely background."""
    origin_x, origin_y = console_origin(machine)
    for dy in range(GLYPH_H):
        for dx in range(GLYPH_W):
            here = pixel(
                machine, origin_x + col * GLYPH_W + dx, origin_y + row * GLYPH_H + dy
            )
            if here != BG_COLOUR:
                return False
    return True


@pytest.fixture(scope="module")
def graphical(image):
    """A booted machine that switched to the framebuffer."""
    machine = boot_with(image, timer=5000)
    assert machine.framebuffer, "the kernel never switched to a framebuffer"
    return machine


class TestModeSwitch:
    def test_the_video_step_reports_success(self, graphical):
        assert "video" in graphical.screen_text()

    def test_the_framebuffer_is_where_vbe_said(self, graphical):
        import simulate

        assert graphical.framebuffer == simulate.FB_BASE

    def test_boot_messages_survive_the_switch(self, graphical):
        # The switch happens part way through boot, so the lines from
        # before it have to be replayed rather than lost.  "video" is
        # the step that does the switching, so anything above it on
        # screen was drawn from the replayed text buffer.
        screen = graphical.screen_text()
        assert "video" in screen
        assert "task scheduler" in screen


class TestDesktop:
    def test_the_backdrop_is_painted(self, graphical):
        assert pixel(graphical, 4, 4) == DESKTOP_COLOUR
        assert pixel(graphical, 1000, 740) == DESKTOP_COLOUR

    def test_the_console_has_its_own_background(self, graphical):
        origin_x, origin_y = console_origin(graphical)
        # a spot inside the window that no text reaches
        assert pixel(graphical, origin_x + 600, origin_y + 8) == BG_COLOUR

    def test_the_title_bar_sits_above_the_console(self, graphical):
        origin_x, origin_y = console_origin(graphical)
        assert pixel(graphical, origin_x + 200, origin_y - 12) == TITLE_COLOUR


class TestTextIsDrawn:
    def test_the_glyph_table_is_complete(self):
        """Every codepoint in the range gets its own sixteen bytes.

        NASM treats a line ending in a backslash as a continuation, so
        a comment naming the '\\' glyph silently swallowed the line
        after it.  The table came up one glyph short and every
        character above it was drawn as its neighbour.
        """
        symbols = kernel_symbols()
        span = symbols["font_first"] - symbols["font_glyphs"]
        expected = (FONT_LAST - FONT_FIRST + 1) * GLYPH_H
        assert span == expected, (
            f"the glyph table holds {span // GLYPH_H} glyphs, "
            f"expected {expected // GLYPH_H}"
        )

    def test_each_character_is_drawn_as_itself(self, image):
        """The pixels on screen must match the glyph for that
        character, not the one next to it."""
        glyphs = parse_font(ROOT / "kernel" / "font.asm")

        printable = "".join(chr(c) for c in range(33, 127))
        first, second = printable[:47], printable[47:]
        machine = boot_with(
            image, keys=f"echo {first}\recho {second}\r", timer=5000
        )
        assert machine.framebuffer

        origin_x, origin_y = console_origin(machine)
        lines = machine.screen_lines()

        for chunk in (first, second):
            row = next(
                (i for i, line in enumerate(lines) if line.strip() == chunk),
                None,
            )
            assert row is not None, f"the shell never echoed {chunk!r}"

            for col, char in enumerate(chunk):
                want = glyphs[ord(char)]
                for dy in range(GLYPH_H):
                    bits = want[dy]
                    for dx in range(GLYPH_W):
                        lit = bool(bits >> (7 - dx) & 1)
                        here = pixel(
                            machine,
                            origin_x + col * GLYPH_W + dx,
                            origin_y + row * GLYPH_H + dy,
                        )
                        drawn = here != BG_COLOUR
                        assert drawn == lit, (
                            f"{char!r} at row {row} column {col}: pixel "
                            f"({dx}, {dy}) is {'set' if drawn else 'clear'}, "
                            f"expected {'set' if lit else 'clear'}"
                        )

    def test_the_drawn_row_matches_the_text_buffer(self, graphical):
        """Text and pixels must not drift apart."""
        lines = graphical.screen_lines()
        for row, line in enumerate(lines):
            for col, char in enumerate(line):
                if char == " ":
                    continue
                assert not cell_is_blank(graphical, row, col), (
                    f"row {row} column {col} holds {char!r} "
                    f"but nothing was drawn"
                )
                break  # one sample per row is enough


class TestCaret:
    def test_exactly_one_caret_is_on_screen(self, image):
        """The caret has to be rubbed out when it moves, including
        when a scroll drags it up a row."""
        machine = boot_with(image, keys="echo hi\r", timer=5000)
        assert machine.framebuffer

        origin_x, origin_y = console_origin(machine)
        lines = machine.screen_lines()

        carets = []
        for row in range(CON_ROWS):
            text = lines[row].ljust(CON_COLS)
            for col in range(CON_COLS):
                if text[col] != " ":
                    continue
                # the caret is drawn on the last two scanlines
                y = origin_y + row * GLYPH_H + GLYPH_H - 1
                x = origin_x + col * GLYPH_W + GLYPH_W // 2
                if pixel(machine, x, y) != BG_COLOUR:
                    carets.append((row, col))

        assert len(carets) == 1, f"expected one caret, found {carets}"


class TestFramebufferMemory:
    def test_the_framebuffer_is_not_handed_out_by_the_allocator(self, graphical):
        """The card owns that memory.  Allocating it to something else
        would put unrelated data on the screen."""
        import subprocess

        nm = subprocess.run(
            ["nm", str(ROOT / "build" / "kernel.elf")],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        symbols = {
            parts[2]: int(parts[0], 16)
            for parts in (line.split() for line in nm.splitlines())
            if len(parts) == 3
        }
        bitmap = symbols["bitmap"]

        def is_used(frame: int) -> bool:
            byte = graphical.uc.mem_read(bitmap + (frame >> 3), 1)[0]
            return bool(byte >> (frame & 7) & 1)

        import simulate

        pages = simulate.FB_HEIGHT * simulate.FB_PITCH // 4096
        first = graphical.framebuffer >> 12

        assert is_used(first), "the first framebuffer page is allocatable"
        assert is_used(first + pages - 1), "the last framebuffer page is allocatable"
        assert not is_used(first + pages), "reserved past the end of the framebuffer"
