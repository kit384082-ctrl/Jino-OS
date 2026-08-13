# Changelog

## 1.0 — 2026-08-13

The first release. An x86 operating system — bootloader and kernel —
written entirely in assembly, booting a PC from a raw disk image or a
CD and landing in an interactive shell.

### Boot

- Two stage bootloader. A 512 byte MBR that reads stage2 with the INT
  13h LBA extensions and falls back to CHS geometry, so the same image
  boots from a floppy, a USB stick or an IDE/SATA disk.
- stage2 queries the memory map (E820, falling back to E801 and INT
  12h), opens the A20 gate, loads the kernel above 1 MiB through unreal
  mode, sets a VBE graphics mode and enters protected mode.
- A hand-off block at physical `0x500` carries the boot drive, the
  memory map and the framebuffer's geometry to the kernel.
- A bootable CD image in El Torito floppy emulation, so the same
  bootloader works unchanged from optical media.

### Kernel

- Flat segmentation with a TSS for ring-0 stack switching, a 256 gate
  IDT, the 8259A pair remapped clear of the CPU exceptions, and the
  8254 timer at 100 Hz.
- Physical memory: a bitmap allocator over 4 KiB frames built from the
  E820 map, with contiguous multi-page allocation.
- Virtual memory: two-level page tables identity mapping the low
  16 MiB, and a page-fault handler that decodes the error code.
- A first-fit kernel heap with boundary tags, splitting on allocation
  and coalescing on free.
- Round-robin tasks, both cooperative and preemptive.
- Ring 3: a real privilege drop through `iret`, nine system calls
  through `int 0x80`, and every pointer arriving from user space
  checked against the span the program was given.
- Drivers for the PS/2 keyboard, the MC146818 clock, ATA disks in
  28-bit LBA PIO mode, and a 16550 UART.
- JinoFS: a superblock, a 64 entry directory and contiguous files,
  mounted at boot and surviving a restart.
- A shell with 31 commands, and a panic handler that dumps the
  registers, the control registers and a stack trace.

### Display

- A 1024x768x32 framebuffer console drawn into a desktop, with a
  window frame, a title bar and a painted caret. The 80x25 text buffer
  stays the record of what is on screen and the framebuffer is painted
  from it, so the console degrades to text mode if the mode set fails.
- An 8x16 font covering codepoints 32 to 126, generated from DejaVu
  Sans Mono.

### Tooling

- `tools/mkimage.py` builds the disk image and refuses to let the
  kernel grow into the filesystem.
- `tools/mkiso.py` writes the ISO 9660 / El Torito image by hand.
- `tools/simulate.py` boots the real image under Unicorn, supplying the
  BIOS the bootloader needs and modelling the devices the kernel talks
  to. It boots the ISO the way firmware does, by extracting the
  emulated floppy from the boot catalogue.
- `tools/screenshot.py` saves what the display is showing as a PNG.
- 170 tests, asserting on what the system prints and does rather than
  on its source.
