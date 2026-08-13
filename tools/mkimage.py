#!/usr/bin/env python3
"""Assemble the Jino-OS boot image.

The layout is deliberately simple, since the bootloader reads raw LBAs
rather than going through a filesystem:

    LBA 0            stage1 (the master boot record)
    LBA 1..8         stage2
    LBA 9..          the kernel image

The result is padded out to a 1.44 MiB floppy so it can be booted either
as a floppy or as a hard disk image.
"""

import argparse
import sys

SECTOR = 512
FLOPPY_SIZE = 1474560  # 1.44 MiB


def read(path):
    with open(path, "rb") as handle:
        return handle.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1", required=True)
    parser.add_argument("--stage2", required=True)
    parser.add_argument("--stage2-lba", type=int, default=1)
    parser.add_argument("--stage2-sectors", type=int, default=8)
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--kernel-lba", type=int, default=9)
    parser.add_argument("--out", required=True)
    parser.add_argument("--size", type=int, default=FLOPPY_SIZE)
    parser.add_argument(
        "--fs-lba",
        type=int,
        default=256,
        help="first sector of the filesystem; the kernel must stay below it",
    )
    args = parser.parse_args()

    stage1 = read(args.stage1)
    stage2 = read(args.stage2)
    kernel = read(args.kernel)

    # --- sanity checks ------------------------------------------------
    if len(stage1) != SECTOR:
        sys.exit(f"stage1 must be exactly {SECTOR} bytes, got {len(stage1)}")

    if stage1[510:512] != b"\x55\xaa":
        sys.exit("stage1 is missing the 0xAA55 boot signature")

    stage2_capacity = args.stage2_sectors * SECTOR
    if len(stage2) > stage2_capacity:
        sys.exit(
            f"stage2 is {len(stage2)} bytes but only {stage2_capacity} "
            f"({args.stage2_sectors} sectors) are reserved for it"
        )

    kernel_sectors = (len(kernel) + SECTOR - 1) // SECTOR
    if args.kernel_lba < args.stage2_lba + args.stage2_sectors:
        sys.exit("the kernel would overlap stage2")

    # The filesystem lives at a fixed offset, so a kernel that grows past
    # it would be overwritten by the first file written.  Catch that here
    # rather than at run time.
    kernel_end = args.kernel_lba + kernel_sectors
    if args.fs_lba and kernel_end > args.fs_lba:
        sys.exit(
            f"the kernel ends at LBA {kernel_end} but the filesystem starts "
            f"at LBA {args.fs_lba}; raise FS_SUPER_LBA in kernel/fs.asm "
            f"or shrink the kernel"
        )

    # --- lay the image out --------------------------------------------
    image = bytearray(args.size)

    def place(data, lba):
        offset = lba * SECTOR
        end = offset + len(data)
        if end > len(image):
            image.extend(b"\x00" * (end - len(image)))
        image[offset:end] = data

    place(stage1, 0)
    place(stage2, args.stage2_lba)
    place(kernel, args.kernel_lba)

    with open(args.out, "wb") as handle:
        handle.write(image)

    print(
        f"image  : {args.out}\n"
        f"  stage1 {len(stage1):>7} bytes  -> LBA 0\n"
        f"  stage2 {len(stage2):>7} bytes  -> LBA {args.stage2_lba}"
        f" ({args.stage2_sectors} sectors reserved)\n"
        f"  kernel {len(kernel):>7} bytes  -> LBA {args.kernel_lba}"
        f" ({kernel_sectors} sectors, {args.fs_lba - kernel_end} spare"
        f" before the filesystem)\n"
        f"  total  {len(image):>7} bytes"
    )


if __name__ == "__main__":
    main()
