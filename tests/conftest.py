"""Shared fixtures: build the image once and boot it under the emulator."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGE = ROOT / "build" / "jino.img"

sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture(scope="session")
def image() -> bytes:
    """Build the OS image and hand back its bytes."""
    subprocess.run(["make", "--quiet"], cwd=ROOT, check=True)
    assert IMAGE.exists(), "the build did not produce an image"
    return IMAGE.read_bytes()


@pytest.fixture(scope="session")
def booted(image):
    """A machine that has finished booting and is sitting at the prompt."""
    from simulate import Machine

    return Machine(image).run()


def boot_with(
    image,
    keys: str = "",
    timer: int = 0,
    instructions=80_000_000,
    ata: bool = False,
):
    """Boot a fresh machine, optionally typing `keys` into the shell."""
    from simulate import Machine

    machine = Machine(image, keystrokes=keys.encode("latin-1"), ata=ata)
    if timer:
        machine.enable_timer(timer)
    return machine.run(instructions)
