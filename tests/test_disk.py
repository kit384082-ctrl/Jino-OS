"""The ATA (IDE) driver, exercised against an emulated drive."""

import pytest

SECTOR = 512


@pytest.fixture(scope="module")
def with_disk(image):
    """A machine whose image is also attached as an IDE drive."""
    from simulate import Machine

    return Machine(image, keystrokes=b"disk\rread 0\r", ata=True).run()


class TestDetection:
    def test_drive_is_detected_at_boot(self, with_disk):
        assert "ata0:" in with_disk.serial_text()
        assert "no drive detected" not in with_disk.serial_text()

    def test_model_string_is_decoded(self, with_disk):
        """The model comes back byte swapped and space padded."""
        assert "JINO VIRTUAL DISK" in with_disk.serial_text()

    def test_capacity_is_reported(self, with_disk):
        line = next(l for l in with_disk.serial_text().splitlines() if "ata0:" in l)
        assert "2880 sectors" in line  # a 1.44 MiB floppy image

    def test_disk_command_reports_the_drive(self, with_disk):
        assert "JINO VIRTUAL DISK" in with_disk.screen_text()


class TestSectorReads:
    def test_read_command_dumps_a_sector(self, with_disk):
        assert "sector 0:" in with_disk.screen_text()

    def test_first_bytes_match_the_boot_sector(self, with_disk, image):
        """The dump must agree with the real contents of LBA 0."""
        screen = with_disk.screen_text()
        line = next(l for l in screen.splitlines() if l.strip().startswith("0000"))
        printed = line.split()[1:17]
        expected = [f"{byte:02x}" for byte in image[:16]]
        assert printed == expected

    def test_dump_is_truncated_for_readability(self, with_disk):
        assert "first 128 bytes shown" in with_disk.screen_text()


class TestWithoutADisk:
    def test_reads_are_refused_when_no_drive_is_present(self, image):
        from conftest import boot_with

        output = boot_with(image, "read 0\r").screen_text()
        assert "no disk available" in output
