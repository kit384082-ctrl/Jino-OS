#!/usr/bin/env python3
"""Boot an image and save what the graphics display is showing as a PNG.

The emulator has no window, so this is how the framebuffer console gets
looked at: boot, type something, then dump the pixels the kernel drew.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import simulate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("-o", "--output", default="screen.png")
    parser.add_argument("--keys", default="")
    parser.add_argument("--timer", type=int, default=5000)
    parser.add_argument("--instructions", type=int, default=80_000_000)
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("Pillow is needed to save a screenshot", file=sys.stderr)
        return 1

    keys = args.keys.encode().decode("unicode_escape").encode()
    machine = simulate.Machine(pathlib.Path(args.image).read_bytes(), keys)
    if args.timer:
        machine.enable_timer(args.timer)
    machine.run(args.instructions)

    if not machine.framebuffer:
        print("the kernel never switched to a framebuffer", file=sys.stderr)
        return 1

    width, height = simulate.FB_WIDTH, simulate.FB_HEIGHT
    pitch = simulate.FB_PITCH
    base = machine.framebuffer

    image = Image.new("RGB", (width, height))
    pixels = image.load()
    raw = bytes(machine.ram[base : base + pitch * height])

    for y in range(height):
        row = y * pitch
        for x in range(width):
            offset = row + x * 4
            blue = raw[offset]
            green = raw[offset + 1]
            red = raw[offset + 2]
            pixels[x, y] = (red, green, blue)

    if args.scale > 1:
        image = image.resize(
            (width * args.scale, height * args.scale), Image.NEAREST
        )

    image.save(args.output)
    print(f"wrote {args.output} ({image.width}x{image.height})")
    print(f"stopped: {machine.stop_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
