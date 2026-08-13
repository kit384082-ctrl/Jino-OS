#!/usr/bin/env python3
"""Wrap the disk image in a bootable ISO 9660 (El Torito) CD image.

The disk image is exactly a 1.44 MiB floppy, so the CD boots it in
floppy emulation mode: the firmware maps it as drive 00h and the INT 13h
reads stage1 already makes work unchanged.  That is the whole reason
this is the emulation mode chosen -- no-emulation booting hands over
2048-byte sectors, which the bootloader would have to be taught about.

Written out by hand because the usual tools (xorriso, genisoimage) are
not something to depend on for one 32 KiB descriptor set.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import struct
import sys

SECTOR = 2048  # ISO 9660 logical block
FLOPPY_BYTES = 1474560  # 1.44 MiB, what floppy emulation expects

# Fixed positions in the descriptor set.  Everything before the boot
# image is a single sector each, so the layout is easiest to read as
# constants rather than a running total.
LBA_PVD = 16
LBA_BOOT_RECORD = 17
LBA_TERMINATOR = 18
LBA_BOOT_CATALOG = 19
LBA_PATH_TABLE_L = 20
LBA_PATH_TABLE_M = 21
LBA_ROOT_DIR = 22
LBA_BOOT_IMAGE = 23


def both_endian_16(value: int) -> bytes:
    """A 16-bit number, little endian then big endian (ECMA-119 7.2.3)."""
    return struct.pack("<H", value) + struct.pack(">H", value)


def both_endian_32(value: int) -> bytes:
    """A 32-bit number, little endian then big endian (ECMA-119 7.3.3)."""
    return struct.pack("<I", value) + struct.pack(">I", value)


def ascii_field(text: str, width: int, pad: bytes = b" ") -> bytes:
    """A fixed width identifier field, space padded and truncated."""
    raw = text.encode("ascii", "replace")[:width]
    return raw + pad * (width - len(raw))


def directory_timestamp(when: datetime.datetime) -> bytes:
    """The 7 byte form used inside directory records (ECMA-119 9.1.5)."""
    return struct.pack(
        "BBBBBBb",
        when.year - 1900,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second,
        0,  # offset from GMT in 15 minute intervals
    )


def volume_timestamp(when: datetime.datetime) -> bytes:
    """The 17 byte form used in volume descriptors (ECMA-119 8.4.26)."""
    return (
        f"{when.year:04d}{when.month:02d}{when.day:02d}"
        f"{when.hour:02d}{when.minute:02d}{when.second:02d}00"
    ).encode("ascii") + bytes([0])


def directory_record(
    name: bytes,
    extent: int,
    length: int,
    when: datetime.datetime,
    is_directory: bool,
) -> bytes:
    """One entry in a directory (ECMA-119 9.1)."""
    record = bytearray()
    record += b"\x00"  # length, filled in once it is known
    record += b"\x00"  # extended attribute record length
    record += both_endian_32(extent)
    record += both_endian_32(length)
    record += directory_timestamp(when)
    record += bytes([0x02 if is_directory else 0x00])  # file flags
    record += b"\x00"  # file unit size, non-interleaved
    record += b"\x00"  # interleave gap size
    record += both_endian_16(1)  # volume sequence number
    record += bytes([len(name)])
    record += name
    if len(record) % 2:  # records are padded to an even length
        record += b"\x00"
    record[0] = len(record)
    return bytes(record)


def primary_volume_descriptor(
    total_sectors: int,
    path_table_size: int,
    root_record: bytes,
    when: datetime.datetime,
    volume_id: str,
) -> bytes:
    """The volume descriptor that describes the disc (ECMA-119 8.4)."""
    pvd = bytearray(SECTOR)
    pvd[0] = 1  # primary volume descriptor
    pvd[1:6] = b"CD001"
    pvd[6] = 1  # version
    pvd[8:40] = ascii_field("JINO-OS", 32)
    pvd[40:72] = ascii_field(volume_id, 32)
    pvd[80:88] = both_endian_32(total_sectors)
    pvd[120:124] = both_endian_16(1)  # volume set size
    pvd[124:128] = both_endian_16(1)  # volume sequence number
    pvd[128:132] = both_endian_16(SECTOR)
    pvd[132:140] = both_endian_32(path_table_size)
    pvd[140:144] = struct.pack("<I", LBA_PATH_TABLE_L)
    pvd[144:148] = struct.pack("<I", 0)  # no optional L path table
    pvd[148:152] = struct.pack(">I", LBA_PATH_TABLE_M)
    pvd[152:156] = struct.pack(">I", 0)  # no optional M path table
    pvd[156 : 156 + len(root_record)] = root_record
    pvd[190:318] = ascii_field("JINO-OS", 128)
    pvd[318:446] = ascii_field("JINO-OS", 128)
    pvd[446:574] = ascii_field("TOOLS/MKISO.PY", 128)
    pvd[574:702] = ascii_field("JINO-OS", 128)
    pvd[702:739] = ascii_field("", 37)
    pvd[739:776] = ascii_field("", 37)
    pvd[776:813] = ascii_field("", 37)
    stamp = volume_timestamp(when)
    pvd[813:830] = stamp  # creation
    pvd[830:847] = stamp  # modification
    pvd[847:864] = b"0" * 16 + bytes([0])  # never expires
    pvd[864:881] = stamp  # effective
    pvd[881] = 1  # file structure version
    return bytes(pvd)


def boot_record_descriptor() -> bytes:
    """Points the firmware at the boot catalogue (El Torito 2.0)."""
    descriptor = bytearray(SECTOR)
    descriptor[0] = 0  # boot record
    descriptor[1:6] = b"CD001"
    descriptor[6] = 1  # version
    descriptor[7:39] = ascii_field("EL TORITO SPECIFICATION", 32, b"\x00")
    descriptor[71:75] = struct.pack("<I", LBA_BOOT_CATALOG)
    return bytes(descriptor)


def terminator_descriptor() -> bytes:
    """Ends the volume descriptor set (ECMA-119 8.3)."""
    descriptor = bytearray(SECTOR)
    descriptor[0] = 0xFF
    descriptor[1:6] = b"CD001"
    descriptor[6] = 1
    return bytes(descriptor)


def boot_catalog(boot_image_lba: int) -> bytes:
    """Validation entry plus the default entry (El Torito 2.1)."""
    catalog = bytearray(SECTOR)

    validation = bytearray(32)
    validation[0] = 0x01  # header id
    validation[1] = 0x00  # platform: 80x86
    validation[4:28] = ascii_field("JINO-OS", 24, b"\x00")
    validation[30] = 0x55
    validation[31] = 0xAA
    # The 16 words of the entry have to sum to zero modulo 2^16.
    total = sum(struct.unpack("<16H", bytes(validation)))
    validation[28:30] = struct.pack("<H", (-total) & 0xFFFF)

    default = bytearray(32)
    default[0] = 0x88  # bootable
    default[1] = 0x02  # 1.44 MiB floppy emulation
    default[2:4] = struct.pack("<H", 0)  # load segment: the 0x7C00 default
    default[4] = 0x00  # system type, unused under emulation
    default[6:8] = struct.pack("<H", 1)  # sectors to load before handing over
    default[8:12] = struct.pack("<I", boot_image_lba)

    catalog[0:32] = validation
    catalog[32:64] = default
    return bytes(catalog)


def path_tables(root_extent: int) -> tuple[bytes, bytes, int]:
    """The little and big endian path tables (ECMA-119 9.4)."""

    def table(endian: str) -> bytes:
        record = bytearray()
        record += bytes([1])  # length of the directory identifier
        record += bytes([0])  # extended attribute record length
        record += struct.pack(endian + "I", root_extent)
        record += struct.pack(endian + "H", 1)  # the root's parent is itself
        record += b"\x00"  # the root's identifier is a single null
        record += b"\x00"  # padded to an even length
        return bytes(record)

    little = table("<")
    return little, table(">"), len(little)


def build(image: bytes, volume_id: str, when: datetime.datetime) -> bytes:
    """Assemble the ISO around a raw disk image."""
    if len(image) != FLOPPY_BYTES:
        raise SystemExit(
            f"floppy emulation needs exactly {FLOPPY_BYTES} bytes, "
            f"the image is {len(image)}"
        )

    image_sectors = (len(image) + SECTOR - 1) // SECTOR
    total_sectors = LBA_BOOT_IMAGE + image_sectors

    # The root directory holds ".", ".." and the image itself, so the
    # disc is readable as a filesystem and not only bootable.
    root_entries = (
        directory_record(b"\x00", LBA_ROOT_DIR, SECTOR, when, True)
        + directory_record(b"\x01", LBA_ROOT_DIR, SECTOR, when, True)
        + directory_record(
            b"JINO.IMG;1", LBA_BOOT_IMAGE, len(image), when, False
        )
    )
    if len(root_entries) > SECTOR:
        raise SystemExit("the root directory outgrew its sector")
    root_directory = root_entries + bytes(SECTOR - len(root_entries))

    # The record describing the root, as it appears inside the PVD.
    root_record = directory_record(b"\x00", LBA_ROOT_DIR, SECTOR, when, True)

    table_l, table_m, table_size = path_tables(LBA_ROOT_DIR)

    iso = bytearray()
    iso += bytes(SECTOR * LBA_PVD)  # system area, unused
    iso += primary_volume_descriptor(
        total_sectors, table_size, root_record, when, volume_id
    )
    iso += boot_record_descriptor()
    iso += terminator_descriptor()
    iso += boot_catalog(LBA_BOOT_IMAGE)
    iso += table_l + bytes(SECTOR - len(table_l))
    iso += table_m + bytes(SECTOR - len(table_m))
    iso += root_directory
    iso += image + bytes(image_sectors * SECTOR - len(image))

    assert len(iso) == total_sectors * SECTOR, "the layout does not add up"
    return bytes(iso)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="the raw disk image")
    parser.add_argument("--out", required=True, help="the ISO to write")
    parser.add_argument("--volume-id", default="JINO_OS")
    args = parser.parse_args()

    # Honour SOURCE_DATE_EPOCH so the build can be reproducible.
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = (
        datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc)
        if epoch
        else datetime.datetime.now(datetime.timezone.utc)
    )

    image = pathlib.Path(args.image).read_bytes()
    iso = build(image, args.volume_id, when)

    out = pathlib.Path(args.out)
    out.write_bytes(iso)
    print(
        f"  iso    {len(iso)} bytes  "
        f"({len(iso) // SECTOR} sectors, el torito floppy emulation)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
