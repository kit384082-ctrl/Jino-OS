"""JinoFS: formatting, files, reuse of space, and surviving a reboot."""

from __future__ import annotations

import re

import pytest

from conftest import boot_with

pytestmark = pytest.mark.usefixtures("image")


def fs_session(image, keys):
    """Format a volume, then run `keys` against it."""
    return boot_with(image, "format\r" + keys, timer=5_000, ata=True)


class TestFormatting:
    @staticmethod
    @pytest.fixture(scope="class")
    def formatted(image):
        return fs_session(image, "df\r")

    def test_format_reports_success(self, formatted):
        assert "filesystem ready" in formatted.screen_text()

    def test_a_fresh_volume_is_empty(self, formatted):
        assert "0 file(s)" in formatted.screen_text()

    def test_an_unformatted_disk_is_not_mounted(self, image):
        machine = boot_with(image, "ls\r", timer=5_000, ata=True)
        assert "no filesystem mounted" in machine.screen_text()

    def test_format_needs_a_disk(self, image):
        """Without a drive the command has to decline, not fault."""
        machine = boot_with(image, "format\r", timer=5_000)
        assert "no disk available" in machine.screen_text()
        assert "KERNEL PANIC" not in machine.serial_text()


class TestFiles:
    @staticmethod
    @pytest.fixture(scope="class")
    def stored(image):
        return fs_session(image, "write greeting hello world\rls\rcat greeting\r")

    def test_write_reports_the_byte_count(self, stored):
        # "hello world" plus the newline the shell appends
        assert "wrote greeting (12 bytes)" in stored.screen_text()

    def test_the_file_appears_in_the_listing(self, stored):
        assert re.search(r"greeting\s+12\s+\d+", stored.screen_text())

    def test_the_contents_come_back(self, stored):
        assert "hello world" in stored.screen_text()

    def test_cat_does_not_double_space(self, stored):
        """The stored newline should not be doubled on the way out."""
        screen = stored.screen_text()
        body = screen[screen.index("cat greeting") :]
        assert "hello world\njino>" in body

    def test_arguments_are_joined_with_single_spaces(self, image):
        machine = fs_session(image, "write s a b c\rcat s\r")
        assert "\na b c\n" in machine.screen_text()

    def test_reading_a_missing_file_is_reported(self, image):
        machine = fs_session(image, "cat absent\r")
        assert "no such file: absent" in machine.screen_text()

    def test_an_over_long_name_is_refused(self, image):
        machine = fs_session(image, "write averyveryverylongfilename x\r")
        assert "write failed" in machine.screen_text()

    def test_several_files_coexist(self, image):
        machine = fs_session(image, "write a one\rwrite b two\rwrite c three\rdf\r")
        assert "3 file(s)" in machine.screen_text()

    def test_files_get_distinct_sectors(self, image):
        machine = fs_session(image, "write a one\rwrite b two\rls\r")
        lbas = re.findall(r"^\s+\w+\s+\d+\s+(\d+)$", machine.screen_text(), re.M)
        assert len(lbas) == 2
        assert lbas[0] != lbas[1]


class TestDeletion:
    @staticmethod
    @pytest.fixture(scope="class")
    def deleted(image):
        return fs_session(image, "write doomed bye\rrm doomed\rls\rcat doomed\r")

    def test_delete_is_acknowledged(self, deleted):
        assert "removed doomed" in deleted.screen_text()

    def test_the_file_leaves_the_listing(self, deleted):
        assert "no files" in deleted.screen_text()

    def test_the_contents_are_gone(self, deleted):
        assert "no such file: doomed" in deleted.screen_text()

    def test_deleting_a_missing_file_is_reported(self, image):
        machine = fs_session(image, "rm ghost\r")
        assert "no such file: ghost" in machine.screen_text()

    def test_space_is_returned(self, image):
        """A delete has to hand its sectors back to the free pool."""
        machine = fs_session(image, "df\rwrite big hello\rdf\rrm big\rdf\r")
        free = [int(n) for n in re.findall(r"(\d+) bytes free", machine.screen_text())]
        assert len(free) == 3
        assert free[1] < free[0]
        assert free[2] == free[0]

    def test_freed_space_is_reused(self, image):
        """The sector of a deleted file should be handed out again."""
        machine = fs_session(image, "write a one\rls\rrm a\rwrite b two\rls\r")
        lbas = re.findall(r"^\s+\w+\s+\d+\s+(\d+)$", machine.screen_text(), re.M)
        assert lbas[0] == lbas[-1]


class TestOverwrite:
    def test_writing_the_same_name_replaces_it(self, image):
        machine = fs_session(image, "write note first\rwrite note second\rcat note\r")
        screen = machine.screen_text()
        body = screen[screen.index("cat note") :]
        assert "second" in body
        assert "first" not in body

    def test_replacing_does_not_leak_space(self, image):
        machine = fs_session(image, "write note first\rdf\rwrite note second\rdf\r")
        counts = re.findall(r"jinofs: (\d+) file\(s\), (\d+) bytes used", machine.screen_text())
        assert counts[0] == counts[1]

    def test_a_shorter_replacement_does_not_leave_a_tail(self, image):
        """The unused part of the last sector must be zero filled."""
        machine = fs_session(
            image, "write n aaaaaaaaaaaaaaaaaaaa\rwrite n bb\rcat n\r"
        )
        screen = machine.screen_text()
        body = screen[screen.index("cat n") :]
        assert "aaaa" not in body


class TestPersistence:
    """The point of a filesystem: the data outlives the machine."""

    @staticmethod
    @pytest.fixture(scope="class")
    def rebooted(image):
        from simulate import Machine

        first = Machine(
            image, keystrokes=b"format\rwrite survivor still here\r", ata=True
        )
        first.enable_timer(5_000)
        first.run()

        second = Machine(bytes(first.disk), keystrokes=b"ls\rcat survivor\r", ata=True)
        second.enable_timer(5_000)
        return second.run()

    def test_the_volume_mounts_by_itself(self, rebooted):
        assert "no filesystem mounted" not in rebooted.screen_text()

    def test_the_banner_reports_the_stored_file(self, rebooted):
        assert "jinofs: 1 file(s)" in rebooted.screen_text()

    def test_the_file_is_still_listed(self, rebooted):
        assert "survivor" in rebooted.screen_text()

    def test_the_contents_survived(self, rebooted):
        assert "still here" in rebooted.screen_text()

    def test_the_reboot_was_clean(self, rebooted):
        assert "KERNEL PANIC" not in rebooted.serial_text()


class TestLayout:
    def test_the_volume_clears_the_kernel(self, image):
        """
        The filesystem sits at a fixed LBA; if the kernel ever grows into
        it, writing a file would corrupt the kernel on disk.
        """
        from simulate import Machine

        machine = Machine(image, keystrokes=b"format\rwrite f data\r", ata=True)
        machine.enable_timer(5_000)
        machine.run()

        changed = [
            lba
            for lba in range(len(image) // 512)
            if image[lba * 512 : (lba + 1) * 512]
            != bytes(machine.disk[lba * 512 : (lba + 1) * 512])
        ]
        assert changed, "the write never reached the disk"
        assert min(changed) >= 256, f"the filesystem wrote over the kernel at {changed}"
