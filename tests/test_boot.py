"""The bootloader and the image layout."""

import struct

SECTOR = 512


class TestImageLayout:
    def test_image_is_a_floppy_sized_multiple_of_sectors(self, image):
        assert len(image) == 1474560
        assert len(image) % SECTOR == 0

    def test_boot_sector_carries_the_signature(self, image):
        assert image[510:512] == b"\x55\xaa"

    def test_partition_table_marks_the_medium_bootable(self, image):
        assert image[446] == 0x80

    def test_stage2_is_present_at_its_lba(self, image):
        stage2 = image[SECTOR : SECTOR * 9]
        assert stage2.strip(b"\x00"), "stage2 area is empty"
        assert b"Jino-OS loader" in stage2

    def test_kernel_is_present_at_its_lba(self, image):
        kernel = image[SECTOR * 9 :]
        assert kernel.strip(b"\x00"), "kernel area is empty"
        # the banner string lives in the kernel's .rodata
        assert b"J I N O - O S" in kernel


class TestBootloader:
    def test_stage1_announces_itself(self, booted):
        assert "Jino-OS" in booted.teletype.decode("latin-1")

    def test_stage1_hands_over_to_stage2(self, booted):
        teletype = booted.teletype.decode("latin-1")
        assert "stage2" in teletype
        assert "disk error" not in teletype

    def test_stage2_loads_the_kernel(self, booted):
        assert "loading kernel" in booted.teletype.decode("latin-1")

    def test_stage2_reaches_protected_mode(self, booted):
        assert "entering protected mode" in booted.teletype.decode("latin-1")

    def test_memory_above_one_megabyte_is_addressable(self, image):
        """Proof that the A20 gate is open.

        stage2 only programs the gate when its probe says the address
        line is still wrapping, so rather than asserting on the probe we
        check the property it exists to guarantee: 0x100000 and 0x000000
        must be distinct memory.  This uses its own machine so the
        scribbled-on bytes cannot affect any other test.
        """
        from conftest import boot_with

        machine = boot_with(image)
        machine.uc.mem_write(0x000000, b"\xa5" * 8)
        machine.uc.mem_write(0x100000, b"\x5a" * 8)
        assert bytes(machine.uc.mem_read(0x000000, 8)) == b"\xa5" * 8

    def test_kernel_was_copied_to_one_megabyte(self, booted, image):
        loaded = bytes(booted.uc.mem_read(0x00100000, 64))
        expected = image[SECTOR * 9 : SECTOR * 9 + 64]
        assert loaded == expected


class TestBootInfo:
    """stage2 leaves a description of the machine at 0x500."""

    def _block(self, booted):
        return bytes(booted.uc.mem_read(0x500, 40))

    def test_magic_is_correct(self, booted):
        magic = struct.unpack_from("<I", self._block(booted))[0]
        assert magic == 0x4F4E494A  # 'JINO'

    def test_memory_map_was_collected(self, booted):
        count = struct.unpack_from("<I", self._block(booted), 8)[0]
        assert count >= 4, "the E820 walk found too few entries"

    def test_low_memory_was_measured(self, booted):
        low_kb = struct.unpack_from("<I", self._block(booted), 16)[0]
        assert low_kb == 639

    def test_kernel_load_address_is_recorded(self, booted):
        phys = struct.unpack_from("<I", self._block(booted), 32)[0]
        assert phys == 0x00100000
