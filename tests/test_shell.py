"""The interactive shell and its commands."""

import re

import pytest

from conftest import boot_with


def screen_after(image, keys, **kwargs):
    return boot_with(image, keys, **kwargs).screen_text()


class TestShellBasics:
    def test_prompt_appears(self, booted):
        assert "jino>" in booted.screen_text()

    def test_input_is_echoed(self, image):
        assert "jino> uname" in screen_after(image, "uname\r")

    def test_unknown_commands_are_reported(self, image):
        output = screen_after(image, "definitelynotacommand\r")
        assert "unknown command" in output

    def test_backspace_edits_the_line(self, image):
        # type "unamex", erase the x, then run it
        output = screen_after(image, "unamex\x08\r")
        assert "Jino-OS 1.0 i386" in output

    def test_empty_line_is_ignored(self, image):
        output = screen_after(image, "\r\r\runame\r")
        assert "unknown command" not in output
        assert "Jino-OS 1.0" in output

    def test_several_commands_in_sequence(self, image):
        output = screen_after(image, "uname\rabout\r")
        assert "Jino-OS 1.0 i386" in output
        assert "written entirely in assembly" in output


class TestCommands:
    def test_help_lists_the_commands(self, image):
        output = screen_after(image, "help\r")
        for command in ("help", "clear", "mem", "cpu", "uptime", "ps"):
            assert command in output

    def test_echo_repeats_its_arguments(self, image):
        output = screen_after(image, "echo hello world\r")
        assert "hello world" in output

    def test_uname_identifies_the_system(self, image):
        assert "Jino-OS 1.0 i386 (assembly)" in screen_after(image, "uname\r")

    def test_clear_wipes_the_screen(self, image):
        output = screen_after(image, "uname\rclear\r")
        assert "Jino-OS 1.0 i386" not in output
        assert "jino>" in output

    def test_mem_reports_all_three_pools(self, image):
        output = screen_after(image, "mem\r")
        assert "physical :" in output
        assert "heap     :" in output
        assert "paging   : enabled" in output

    def test_memmap_lists_the_e820_regions(self, image):
        output = screen_after(image, "memmap\r")
        assert "base" in output and "length" in output
        assert "usable" in output
        assert "reserved" in output

    def test_cpu_prints_the_vendor(self, image):
        assert "cpu: vendor" in screen_after(image, "cpu\r")

    def test_date_formats_the_clock(self, image):
        output = screen_after(image, "date\r")
        # the emulated CMOS is set to 2026-08-13 12:34:56
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", output)
        assert "2026-08-13" in output

    def test_ps_lists_the_kernel_task(self, image):
        output = screen_after(image, "ps\r")
        assert "kernel" in output
        assert "running" in output

    def test_disk_reports_when_no_drive_is_attached(self, image):
        assert "no drive detected" in screen_after(image, "disk\r")

    def test_colors_prints_the_palette(self, image):
        output = screen_after(image, "colors\r")
        assert "palette:" in output
        assert "0123456789abcdef" in output


class TestHeapCommands:
    def test_alloc_returns_a_pointer(self, image):
        output = screen_after(image, "alloc 128\r")
        match = re.search(r"allocated (\d+) bytes at 0x([0-9a-f]{8})", output)
        assert match, f"unexpected output: {output}"
        assert int(match.group(1)) == 128
        assert int(match.group(2), 16) != 0

    def test_allocation_is_visible_in_the_heap_listing(self, image):
        output = screen_after(image, "alloc 256\rheap\r")
        assert "used" in output
        assert "free" in output
        assert "heap is consistent" in output

    def test_free_releases_the_block(self, image):
        output = screen_after(image, "alloc 64\rfree\r")
        assert "freed 0x" in output

    def test_freeing_nothing_is_reported(self, image):
        assert "nothing to free" in screen_after(image, "free\r")

    def test_heap_stays_consistent_across_churn(self, image):
        keys = "alloc 100\rfree\ralloc 200\rfree\ralloc 300\rfree\rheap\r"
        output = screen_after(image, keys)
        assert "heap is consistent" in output
        assert "CORRUPTED" not in output

    def test_freed_memory_is_reused(self, image):
        """The same block should come back after a free."""
        output = screen_after(image, "alloc 128\rfree\ralloc 128\r")
        addresses = re.findall(r"allocated \d+ bytes at 0x([0-9a-f]{8})", output)
        assert len(addresses) == 2
        assert addresses[0] == addresses[1]

    def test_usage_message_without_an_argument(self, image):
        assert "usage: alloc" in screen_after(image, "alloc\r")


class TestMemoryCommands:
    def test_peek_reads_memory(self, image):
        # 0x500 holds the boot info magic, 'JINO' == 0x4f4e494a
        output = screen_after(image, "peek 1280\r")
        assert "0x4f4e494a" in output

    def test_virt_translates_an_identity_mapped_page(self, image):
        output = screen_after(image, "virt 1048576\r")
        assert "0x00100000 -> physical 0x00100000" in output

    def test_virt_reports_unmapped_addresses(self, image):
        # far above the 16 MiB the kernel identity maps
        output = screen_after(image, "virt 0x40000000\r")
        assert "is not mapped" in output

    def test_peek_needs_an_argument(self, image):
        assert "usage: peek" in screen_after(image, "peek\r")


class TestTimer:
    def test_uptime_advances_once_the_timer_runs(self, image):
        output = screen_after(image, "uptime\r", timer=20_000)
        match = re.search(r"(\d+) timer ticks", output)
        assert match, f"unexpected output: {output}"
        assert int(match.group(1)) > 0

    def test_uptime_is_zero_without_a_timer(self, image):
        output = screen_after(image, "uptime\r")
        assert "0 timer ticks" in output

    def test_sleep_returns_to_the_prompt(self, image):
        """sleep parks the CPU on hlt until the timer wakes it."""
        output = screen_after(image, "sleep 20\runame\r", timer=5_000)
        assert "Jino-OS 1.0 i386" in output

    def test_sleep_actually_waits(self, image):
        """The uptime either side of a sleep has to move."""
        machine = boot_with(image, "uptime\rsleep 50\ruptime\r", timer=5_000)
        ticks = [int(m) for m in re.findall(r"(\d+) timer ticks", machine.screen_text())]
        assert len(ticks) == 2
        assert ticks[1] > ticks[0]
