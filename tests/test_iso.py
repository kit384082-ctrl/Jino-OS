"""The bootable CD image.

Checking the descriptors are well formed is not the same as checking the
disc boots, so the last test here boots it the way firmware does: pull
the emulated floppy out of the boot catalogue and run that.
"""

from __future__ import annotations

import pathlib
import struct
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

SECTOR = 2048
LBA_PVD = 16
LBA_BOOT_RECORD = 17
LBA_TERMINATOR = 18


@pytest.fixture(scope="module")
def iso(image) -> bytes:
    """Build the ISO and hand back its bytes."""
    subprocess.run(["make", "--quiet", "iso"], cwd=ROOT, check=True)
    path = ROOT / "build" / "jino.iso"
    assert path.exists(), "the build did not produce an ISO"
    return path.read_bytes()


def sector(iso: bytes, lba: int) -> bytes:
    return iso[lba * SECTOR : (lba + 1) * SECTOR]


class TestStructure:
    def test_the_size_is_a_whole_number_of_sectors(self, iso):
        assert len(iso) % SECTOR == 0

    def test_the_system_area_is_reserved(self, iso):
        # The first 16 sectors belong to the firmware, not to us.
        assert iso[: 16 * SECTOR] == bytes(16 * SECTOR)

    def test_the_primary_volume_descriptor_is_present(self, iso):
        pvd = sector(iso, LBA_PVD)
        assert pvd[0] == 1
        assert pvd[1:6] == b"CD001"
        assert pvd[6] == 1

    def test_the_volume_is_named(self, iso):
        pvd = sector(iso, LBA_PVD)
        assert pvd[40:72].decode("ascii").strip() == "JINO_OS"

    def test_the_recorded_size_matches_the_file(self, iso):
        pvd = sector(iso, LBA_PVD)
        little = struct.unpack("<I", pvd[80:84])[0]
        big = struct.unpack(">I", pvd[84:88])[0]
        assert little == big == len(iso) // SECTOR

    def test_the_logical_block_size_is_2048(self, iso):
        pvd = sector(iso, LBA_PVD)
        assert struct.unpack("<H", pvd[128:130])[0] == SECTOR

    def test_the_descriptor_set_is_terminated(self, iso):
        terminator = sector(iso, LBA_TERMINATOR)
        assert terminator[0] == 0xFF
        assert terminator[1:6] == b"CD001"


class TestElTorito:
    def test_the_boot_record_names_the_specification(self, iso):
        record = sector(iso, LBA_BOOT_RECORD)
        assert record[0] == 0
        assert record[1:6] == b"CD001"
        assert record[7:30].rstrip(b"\x00") == b"EL TORITO SPECIFICATION"

    def test_the_validation_entry_checksums_to_zero(self, iso):
        record = sector(iso, LBA_BOOT_RECORD)
        catalog_lba = struct.unpack("<I", record[71:75])[0]
        validation = iso[catalog_lba * SECTOR : catalog_lba * SECTOR + 32]

        assert validation[0] == 0x01, "not a validation entry"
        assert validation[1] == 0x00, "the platform is not 80x86"
        assert validation[30:32] == b"\x55\xaa", "the key bytes are wrong"

        words = struct.unpack("<16H", validation)
        assert sum(words) & 0xFFFF == 0, "the firmware would reject this"

    def test_the_default_entry_boots_a_floppy(self, iso):
        record = sector(iso, LBA_BOOT_RECORD)
        catalog_lba = struct.unpack("<I", record[71:75])[0]
        entry = iso[catalog_lba * SECTOR + 32 : catalog_lba * SECTOR + 64]

        assert entry[0] == 0x88, "the entry is not marked bootable"
        assert entry[1] == 0x02, "not 1.44 MiB floppy emulation"

    def test_the_boot_image_is_the_disk_image(self, iso, image):
        record = sector(iso, LBA_BOOT_RECORD)
        catalog_lba = struct.unpack("<I", record[71:75])[0]
        entry = iso[catalog_lba * SECTOR + 32 : catalog_lba * SECTOR + 64]
        start = struct.unpack("<I", entry[8:12])[0] * SECTOR

        assert iso[start : start + len(image)] == image
        assert iso[start + 510 : start + 512] == b"\x55\xaa"


class TestItActuallyBoots:
    def test_the_iso_boots_to_a_shell(self, iso):
        """The point of the whole file: burn this and it runs."""
        from simulate import Machine

        machine = Machine(iso, keystrokes=b"uname\r")
        machine.enable_timer(5000)
        machine.run()

        screen = machine.screen_text()
        assert "Jino-OS 1.0 i386 (assembly)" in screen
        assert "jino>" in screen

    def test_booting_the_iso_matches_booting_the_disk(self, iso, image):
        """The CD and the raw image are the same system."""
        from simulate import Machine

        from_iso = Machine(iso).run().screen_text()
        from_image = Machine(image).run().screen_text()
        assert from_iso == from_image
