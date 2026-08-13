# Jino-OS

A small x86 operating system — bootloader and kernel — written entirely
in assembly (NASM, Intel syntax). It boots a PC from a raw disk image,
brings the processor from 16-bit real mode up to 32-bit protected mode
with paging, and lands you in an interactive shell.

```
                    J I N O - O S   v 1 . 0
        an x86 operating system written in pure assembly

  global descriptor table     [ ok ]
  interrupt descriptor table  [ ok ]
  interrupt controller        [ ok ]
  interval timer              [ ok ]
  physical memory manager     [ ok ]
  paging                      [ ok ]
  kernel heap                 [ ok ]
  ps/2 keyboard               [ ok ]
  real time clock             [ ok ]
  cpu identification          [ ok ]
  ata storage                 [ ok ]
  jinofs filesystem           [ ok ]
  task scheduler              [ ok ]

cpu: vendor GenuineIntel
cpu: family 6, model 60, stepping 4
cpu: features fpu tsc msr pae apic pge cmov mmx fxsr sse sse2 pse
ata0: JINO VIRTUAL DISK, 2880 sectors (1 MiB)
jinofs: 1 file(s), 512 bytes used, 261632 bytes free
memory: 65148 KiB usable (16287 pages), kernel 1248 KiB, heap 1048576 bytes

system ready.

jino>
```

## Building and running

```sh
make            # assemble everything and produce build/jino.img
make run        # boot the image under QEMU
make sim        # boot it under the bundled software emulator
make test       # run the test suite (101 tests)
make info       # print the sizes of each component
make clean
```

The only hard requirements are **NASM**, **GNU ld** and **Python 3**.
QEMU is optional — `make sim` and the tests use a self-contained
emulator built on Unicorn:

```sh
pip install -r requirements-dev.txt
```

If your Python lives in a virtualenv, point make at it:
`make test PYTHON=/path/to/venv/bin/python`.

Writing the image to real hardware is just a copy, because the layout is
raw sectors rather than a filesystem:

```sh
sudo dd if=build/jino.img of=/dev/sdX bs=512 conv=fsync
```

## How it boots

| Stage | Mode | What happens |
| --- | --- | --- |
| `boot/stage1.asm` | 16-bit real | The 512-byte MBR. Sets up a stack, reads stage2 off the boot device (INT 13h LBA extensions, with a CHS fallback) and jumps to it. |
| `boot/stage2.asm` | 16-bit → 32-bit | Queries the memory map (E820, with E801/INT 12h fallbacks), opens the A20 gate, copies the kernel above 1 MiB through unreal mode, installs a flat GDT and enters protected mode. |
| `kernel/entry.asm` | 32-bit protected | Clears `.bss`, checks the CPU is at least a 486, and calls `kmain`. |
| `kernel/kmain.asm` | 32-bit protected | Initialises every subsystem in dependency order, then starts the shell. |

The loader leaves a small hand-off block at physical `0x500`
(`boot/bootinfo.inc`) describing the boot drive, the memory map and
where the kernel was placed.

### Disk layout

```
LBA 0        stage1 (512 bytes, ends in 0xAA55)
LBA 1..8     stage2
LBA 9..      the kernel image
LBA 256      JinoFS superblock
LBA 257..260 the directory, 64 entries
LBA 261..    file data
```

The filesystem starts at a fixed offset, so `tools/mkimage.py` fails the
build if the kernel ever grows into it rather than letting the first
file written corrupt the kernel on disk.

## Files

`jinofs` is deliberately simple: files are stored contiguously, so a
read is a single ATA request and the directory doubles as the allocation
map. The directory is cached while mounted and written back after every
change.

```
jino> format
creating a filesystem on ata0...
filesystem ready
jino> write diary the disk remembers
wrote diary (19 bytes)
jino> ls
  name              size   lba
  diary               19   261
1 file(s)
jino> cat diary
the disk remembers
```

A volume is mounted automatically at boot, so the contents survive a
restart. To keep what the guest wrote when running under the emulator,
add `--persist`:

```sh
python3 tools/simulate.py disk.img --keys 'write notes hello\r' --ata --persist
```

## What the kernel does

| Area | File | Notes |
| --- | --- | --- |
| Segmentation | `gdt.asm` | Flat 4 GiB kernel and user segments plus a TSS for ring-0 stack switching. |
| Interrupts | `idt.asm`, `isr.asm` | 256 gates: 32 exception stubs, 16 IRQ stubs and `int 0x80` for system calls, all funnelled into a common dispatcher with a documented register frame. |
| Interrupt controller | `pic.asm` | Remaps the 8259A pair to vectors 32–47 so the IRQs stop colliding with CPU exceptions. |
| Timer | `pit.asm` | 8254 channel 0 at 100 Hz; drives uptime, `sleep` and preemption. |
| Physical memory | `pmm.asm` | Bitmap allocator over 4 KiB frames, built from the E820 map, with contiguous multi-page allocation. |
| Virtual memory | `paging.asm` | Two-level page tables, identity mapping the low 16 MiB, plus a decoded page-fault handler. |
| Heap | `heap.asm` | First-fit free list with boundary tags, splitting on allocation and coalescing on free. |
| Tasks | `task.asm` | Round-robin kernel threads, cooperative (`yield`) and preemptive (timer driven). |
| Console | `vga.asm` | 80×25 text mode: scrolling, colour attributes, hardware cursor. |
| Serial | `serial.asm` | 16550 UART on COM1, so the whole session can be captured headless. |
| Keyboard | `keyboard.asm` | Scan code set 1, modifier tracking, extended keys, circular buffer, line editing. |
| Storage | `ata.asm` | 28-bit LBA PIO reads and writes, with IDENTIFY parsing. |
| Filesystem | `fs.asm` | JinoFS: a superblock, a 64 entry directory and contiguous files, mounted at boot and surviving a reboot. |
| Clock | `rtc.asm` | MC146818 with BCD and 12/24-hour handling, read twice to avoid update races. |
| Formatting | `printf.asm` | `%d %u %x %X %o %b %c %s %p %%`, width, zero padding and left alignment. |
| Diagnostics | `panic.asm` | Named exceptions, full register and control register dump, and a stack trace. |

## The shell

`help` lists everything. A few worth trying:

| Command | Description |
| --- | --- |
| `mem`, `memmap`, `heap` | Memory statistics, the BIOS map, and the live heap block list. |
| `cpu`, `uname`, `date`, `uptime` | Machine identification and clocks. |
| `alloc <n>`, `free` | Allocate and release heap memory, visible in `heap`. |
| `peek <addr>`, `virt <addr>` | Read memory; translate a virtual address through the page tables. |
| `ls`, `cat`, `write`, `rm` | List, read, store and delete files. |
| `format`, `df` | Create a filesystem and show how full it is. |
| `disk`, `read <lba>` | ATA drive information and a sector hex dump. |
| `ps`, `spawn`, `preempt` | List tasks, run a cooperative worker, demonstrate preemption. |
| `crash`, `panic` | Deliberately fault, to exercise the exception handler. |

## Testing

The suite boots the real image in an emulator and asserts on what the
system actually prints and does — not on the source.

```sh
make test
```

It covers the image layout and boot signature, each bootloader stage,
the hand-off block, every subsystem reporting ready, protected mode and
paging being live, the shell commands, heap behaviour (including reuse
and coalescing after a free), the ATA driver against an emulated drive,
task creation, teardown and preemptive scheduling, and the filesystem —
including that a file written on one boot is still readable on the next,
and that the volume never overlaps the kernel.

`tools/simulate.py` is the emulator behind this. It supplies the BIOS
interrupts the bootloader needs, then models the devices the kernel
talks to — PIC, PIT, UART, CMOS, CRTC and an IDE drive — and walks the
kernel's own IDT so exceptions and IRQs reach the handlers it installed.
Run it directly to poke at the system:

```sh
python3 tools/simulate.py build/jino.img --keys 'mem\rps\r' --timer 5000 --ata --serial
```

## Layout

```
boot/     stage1.asm  stage2.asm  bootinfo.inc
kernel/   entry.asm  kmain.asm  and the subsystems listed above
          kernel.inc  linker.ld
tools/    mkimage.py  simulate.py
tests/    test_boot.py  test_kernel.py  test_shell.py
          test_disk.py  test_tasks.py   test_fs.py
```

## Licence

MIT — see `LICENSE`.
