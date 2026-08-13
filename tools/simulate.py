#!/usr/bin/env python3
"""Boot a Jino-OS image inside a software x86 emulator.

QEMU is not always available, so this harness drives the image through
Unicorn (the QEMU CPU core exposed as a library) and provides just
enough of a PC around it: BIOS interrupts in real mode, then the port
level devices the kernel talks to once it is in protected mode.

It is used both for interactive smoke testing (`make sim`) and by the
test suite, which asserts on the console output.

    python3 tools/simulate.py build/jino.img
"""

from __future__ import annotations

import argparse
import ctypes
import sys

try:
    from unicorn import (
        Uc,
        UC_ARCH_X86,
        UC_MODE_16,
        UC_MODE_32,
        UC_HOOK_INTR,
        UC_HOOK_CODE,
        UC_HOOK_INSN,
        UC_HOOK_MEM_UNMAPPED,
        UC_PROT_ALL,
        UcError,
    )
    from unicorn.x86_const import (
        UC_X86_INS_IN,
        UC_X86_INS_OUT,
        UC_X86_REG_AX,
        UC_X86_REG_AH,
        UC_X86_REG_AL,
        UC_X86_REG_BX,
        UC_X86_REG_BL,
        UC_X86_REG_CX,
        UC_X86_REG_CL,
        UC_X86_REG_DX,
        UC_X86_REG_DH,
        UC_X86_REG_DL,
        UC_X86_REG_DI,
        UC_X86_REG_SI,
        UC_X86_REG_EAX,
        UC_X86_REG_EBX,
        UC_X86_REG_ECX,
        UC_X86_REG_EDX,
        UC_X86_REG_ESI,
        UC_X86_REG_EDI,
        UC_X86_REG_EBP,
        UC_X86_REG_EIP,
        UC_X86_REG_ESP,
        UC_X86_REG_CS,
        UC_X86_REG_FS,
        UC_X86_REG_GS,
        UC_X86_REG_DS,
        UC_X86_REG_ES,
        UC_X86_REG_SS,
        UC_X86_REG_EFLAGS,
        UC_X86_REG_CR0,
        UC_X86_REG_CR3,
        UC_X86_REG_IDTR,
        UC_X86_REG_GDTR,
        UC_X86_REG_TR,
    )
except ImportError:  # pragma: no cover - the harness is optional
    sys.exit(
        "the 'unicorn' package is required for the simulator:\n"
        "    pip install unicorn"
    )


SECTOR = 512
MEM_SIZE = 64 * 1024 * 1024

# Kernel selectors, mirroring kernel/kernel.inc.
SEG_KCODE = 0x08
SEG_KDATA = 0x10

# Scratch below the boot sector, used to iret the user CPU into ring 3.
# Its previous contents are restored afterwards, so the guest never sees
# the borrowed memory change.
TRAMPOLINE = 0x00007000
VGA_BASE = 0xB8000
VGA_WIDTH = 80
VGA_HEIGHT = 25

CF = 1 << 0
ZF = 1 << 6


class Machine:
    """A very small PC: memory, a disk, a screen and a serial port."""

    def __init__(
        self,
        image: bytes,
        keystrokes: bytes = b"",
        memory_mb: int = 64,
        ata: bool = False,
    ):
        self.disk = bytearray(image)
        self.memory_mb = memory_mb
        self.ata_enabled = ata
        self.serial_out = bytearray()
        self.teletype = bytearray()
        self.keystrokes = bytearray(keystrokes)
        self.port_log: list[tuple[str, int, int]] = []
        self.halted = False
        self.a20 = False
        self._timer_period = 0
        self._timer_countdown = 0
        self._halt_sites = frozenset()
        self.halt_count = 0
        self._idle_watermark = -1
        self.idle = False
        # how many idle halts to tolerate before declaring the machine
        # quiescent and stopping the run
        self.idle_halts = 2000

        # device state
        self.crtc_index = 0
        self.cursor = 0
        self.pic_masks = [0xFF, 0xFF]
        self.pic_init_stage = [0, 0]
        self.cmos_index = 0
        self.cmos = self._default_cmos()
        # ATA (IDE) drive on the primary channel
        self.ata_regs = {}
        self.ata_buffer = bytearray()
        self.ata_pos = 0
        self.ata_status = 0x50 if self.ata_enabled else 0x00  # RDY | DSC
        self.ata_lba_mid = 0
        self.ata_lba_hi = 0
        self._budget = 0
        self._int80_sites = frozenset()
        self._iret_sites = frozenset()
        self.user_uc = None
        self.instructions = 0
        self.ata_writing = False
        self.ata_write_lba = 0
        self.ata_write_bytes = 0

        # 16550 UART state
        self.uart_lcr = 0
        self.uart_mcr = 0
        self.uart_ier = 0
        self.uart_divisor = 0
        self.uart_rx = bytearray()

        # Guest RAM lives in a buffer we own rather than inside Unicorn,
        # so that a second CPU can be attached to the very same bytes.
        # See _run_user for why ring 3 needs a CPU of its own.
        self.ram = ctypes.create_string_buffer(MEM_SIZE)

        self.uc = Uc(UC_ARCH_X86, UC_MODE_16)
        self.uc.mem_map_ptr(
            0, MEM_SIZE, UC_PROT_ALL, ctypes.addressof(self.ram)
        )
        self.uc.mem_write(0x7C00, bytes(self.disk[:SECTOR]))

        self.uc.hook_add(UC_HOOK_INTR, self._on_interrupt)
        self.uc.hook_add(UC_HOOK_INSN, self._on_in, None, 1, 0, UC_X86_INS_IN)
        self.uc.hook_add(UC_HOOK_INSN, self._on_out, None, 1, 0, UC_X86_INS_OUT)
        self.uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._on_unmapped)

        for reg in (UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_CS):
            self.uc.reg_write(reg, 0)
        self.uc.reg_write(UC_X86_REG_ESP, 0x7C00)
        self.uc.reg_write(UC_X86_REG_DX, 0x80)  # boot drive

    # ------------------------------------------------------------ CMOS
    def _default_cmos(self):
        values = [0] * 128
        # 2026-08-13 12:34:56, stored in BCD as a real chip would
        def bcd(n):
            return ((n // 10) << 4) | (n % 10)

        values[0x00] = bcd(56)  # seconds
        values[0x02] = bcd(34)  # minutes
        values[0x04] = bcd(12)  # hours
        values[0x06] = bcd(4)   # weekday
        values[0x07] = bcd(13)  # day
        values[0x08] = bcd(8)   # month
        values[0x09] = bcd(26)  # year
        values[0x0A] = 0x26     # status A: no update in progress
        values[0x0B] = 0x02     # status B: 24 hour, BCD
        values[0x32] = bcd(20)  # century
        return values

    # -------------------------------------------------------- interrupts
    def _on_interrupt(self, uc, intno, user_data):
        if self._protected_mode():
            # Unicorn does not walk the guest IDT for us, so once the
            # kernel is in protected mode we deliver the vector to its
            # own handler exactly as the CPU would.
            self._dispatch_through_idt(uc, intno)
            return

        handler = {
            0x10: self._int10,
            0x12: self._int12,
            0x13: self._int13,
            0x15: self._int15,
            0x16: self._int16,
            0x19: self._int19,
        }.get(intno)

        if handler is not None:
            handler(uc)

    def _protected_mode(self):
        return bool(self.uc.reg_read(UC_X86_REG_CR0) & 1)

    # Vectors that arrive with an error code already pushed.
    ERROR_CODE_VECTORS = frozenset({8, 10, 11, 12, 13, 14, 17, 21, 29, 30})

    def _dispatch_through_idt(self, uc, intno):
        base, limit = uc.reg_read(UC_X86_REG_IDTR)[1:3]
        offset = intno * 8
        if offset + 7 > limit:
            self.halted = True
            self.fault = f"vector {intno} is outside the IDT limit"
            uc.emu_stop()
            return

        entry = uc.mem_read(base + offset, 8)
        selector = int.from_bytes(entry[2:4], "little")
        flags = entry[5]
        handler = int.from_bytes(entry[0:2], "little") | (
            int.from_bytes(entry[6:8], "little") << 16
        )

        if not flags & 0x80 or handler == 0:  # the present bit
            self.halted = True
            self.fault = f"no handler installed for vector {intno}"
            uc.emu_stop()
            return

        eflags = uc.reg_read(UC_X86_REG_EFLAGS)
        eip = uc.reg_read(UC_X86_REG_EIP)
        cs = uc.reg_read(UC_X86_REG_CS)
        esp = uc.reg_read(UC_X86_REG_ESP)

        # Build the stack frame the iret at the end of the stub expects.
        frame = [eflags, cs, eip]
        if intno in self.ERROR_CODE_VECTORS:
            frame.append(0)  # a plausible error code

        for value in frame:
            esp -= 4
            uc.mem_write(esp, int(value & 0xFFFFFFFF).to_bytes(4, "little"))

        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_CS, selector)
        # an interrupt gate clears IF, a trap gate leaves it alone
        if flags & 0x0F == 0x0E:
            uc.reg_write(UC_X86_REG_EFLAGS, eflags & ~(1 << 9))
        uc.reg_write(UC_X86_REG_EIP, handler)

    def _tss_stack(self, uc):
        """Read esp0/ss0 out of the TSS the task register points at."""
        # Unicorn hands back the descriptor as (selector, base, limit,
        # flags), so the GDT walk is already done for us.
        selector, base, limit = uc.reg_read(UC_X86_REG_TR)[:3]
        if not selector or limit < 11:
            return None, None
        esp0 = int.from_bytes(uc.mem_read(base + 4, 4), "little")
        ss0 = int.from_bytes(uc.mem_read(base + 8, 2), "little")
        return esp0, ss0

    def _make_user_cpu(self):
        """A second CPU, wired to the same RAM, for running ring 3 code."""
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map_ptr(0, MEM_SIZE, UC_PROT_ALL, ctypes.addressof(self.ram))

        # It runs with the kernel's descriptor tables and page tables, so
        # user code sees exactly the memory the kernel mapped for it.
        uc.reg_write(UC_X86_REG_GDTR, self.uc.reg_read(UC_X86_REG_GDTR))
        uc.reg_write(UC_X86_REG_IDTR, self.uc.reg_read(UC_X86_REG_IDTR))
        uc.reg_write(UC_X86_REG_CR3, self.uc.reg_read(UC_X86_REG_CR3))

        uc.hook_add(UC_HOOK_INSN, self._on_in, None, 1, 0, UC_X86_INS_IN)
        uc.hook_add(UC_HOOK_INSN, self._on_out, None, 1, 0, UC_X86_INS_OUT)
        return uc

    def _run_user(self, frame, budget):
        """
        Execute ring 3 code and return the syscall that interrupted it.

        Unicorn will happily iret down to ring 3, but a CPU that has run
        there is spoiled for good: every later attempt to load a code
        segment is refused and instructions start decoding as 16-bit,
        whatever is done to CS, CR0 or the descriptor tables.  Restoring
        a saved context does not undo it either.

        So user code gets a CPU of its own, mapped onto the same guest
        RAM.  The kernel's CPU never leaves ring 0 and stays healthy,
        while this one can be thrown away and rebuilt whenever it breaks.
        """
        uc = self._make_user_cpu()
        self.user_uc = uc

        # A stack segment can only be loaded at a matching privilege
        # level, so ring 3 cannot simply be assigned into the registers.
        # This CPU has to get there the way the hardware does: start it
        # in ring 0 and let it iret down, from a scratch trampoline that
        # is put back the way it was afterwards.
        uc.reg_write(UC_X86_REG_CS, SEG_KCODE)
        uc.reg_write(UC_X86_REG_SS, SEG_KDATA)
        uc.reg_write(UC_X86_REG_DS, SEG_KDATA)
        uc.reg_write(UC_X86_REG_ESP, TRAMPOLINE + 0x80)

        # Paging goes on once CR3 is set: while it is enabled Unicorn
        # walks the page tables to load a descriptor, so the GDT has to
        # be reachable through them first.
        uc.reg_write(UC_X86_REG_CR0, self.uc.reg_read(UC_X86_REG_CR0))

        for register, value in frame.get("regs", {}).items():
            uc.reg_write(register, value)

        saved_scratch = bytes(uc.mem_read(TRAMPOLINE, 0x84))
        uc.mem_write(TRAMPOLINE, b"\xCF")  # iret
        esp = TRAMPOLINE + 0x80
        for value in (
            frame["ss"], frame["esp"], frame["eflags"],
            frame["cs"], frame["eip"],
        ):
            esp -= 4
            uc.mem_write(esp, int(value & 0xFFFFFFFF).to_bytes(4, "little"))
        uc.reg_write(UC_X86_REG_ESP, esp)

        # Stop on the int 0x80 before it executes: the CPU cannot service
        # the gate itself, so the kernel side has to be run by hand.
        syscall = {}

        def on_code(uc, address, size, user_data):
            self.instructions += 1
            if size == 2 and address in self._int80_sites:
                syscall["return_eip"] = address + size
                uc.emu_stop()

        uc.hook_add(UC_HOOK_CODE, on_code)

        try:
            uc.emu_start(TRAMPOLINE, 0, 0, budget)
        except UcError as exc:
            uc.mem_write(TRAMPOLINE, saved_scratch)
            eip = uc.reg_read(UC_X86_REG_EIP)
            self.stop_reason = f"{exc} at eip=0x{eip:08x} (ring 3)"
            return None

        uc.mem_write(TRAMPOLINE, saved_scratch)

        if "return_eip" not in syscall:
            self.stop_reason = "instruction budget exhausted"
            return None

        syscall["regs"] = {
            reg: uc.reg_read(reg)
            for reg in (
                UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI,
                UC_X86_REG_EBP,
            )
        }
        syscall["cs"] = uc.reg_read(UC_X86_REG_CS)
        syscall["ss"] = uc.reg_read(UC_X86_REG_SS)
        syscall["esp"] = uc.reg_read(UC_X86_REG_ESP)
        syscall["eflags"] = uc.reg_read(UC_X86_REG_EFLAGS)
        return syscall

    def _user_excursion(self, frame):
        """
        Run ring 3 until it makes a syscall, then enter the kernel.

        Called from the instruction hook in place of the iret that would
        have dropped into user mode.  The kernel CPU keeps running: on
        the way out its EIP is simply pointed at the int 0x80 handler,
        so from the kernel's side the gate looks like it was taken.
        """
        before = self.instructions
        syscall = self._run_user(frame, max(self._budget, 1))
        self._budget -= self.instructions - before

        if syscall is None or self._budget <= 0:
            self.uc.emu_stop()
            return

        handler = self._enter_ring0(syscall)
        if handler is None:
            self.uc.emu_stop()
            return

        # Resume the kernel at the handler.  Writing EIP from inside the
        # hook makes execution continue there once it returns.
        #
        # Only one excursion is handled here.  What happens next is the
        # kernel's decision: if it irets back to ring 3 the hook lands in
        # here again, and if the call was exit it simply never does.
        self.uc.reg_write(UC_X86_REG_EIP, handler)

    def _vector_handler(self, vector):
        """Offset and gate flags for an IDT entry, or (None, None)."""
        base, limit = self.uc.reg_read(UC_X86_REG_IDTR)[1:3]
        offset = vector * 8
        if offset + 7 > limit:
            return None, None
        entry = self.uc.mem_read(base + offset, 8)
        flags = entry[5]
        if not flags & 0x80:
            return None, None
        handler = int.from_bytes(entry[0:2], "little") | (
            int.from_bytes(entry[6:8], "little") << 16
        )
        return handler, flags

    def _enter_ring0(self, syscall):
        """
        Deliver a ring 3 syscall to the kernel CPU as int 0x80 would.

        The kernel CPU never executed the gate, so the frame it expects
        has to be laid out on the ring 0 stack from the TSS by hand.
        """
        uc = self.uc

        handler, flags = self._vector_handler(0x80)
        if handler is None:
            self.halted = True
            self.fault = "no handler installed for vector 0x80"
            return None

        if (flags >> 5) & 3 != 3:
            self.halted = True
            self.fault = "int 0x80 is not reachable from ring 3"
            return None

        esp0, ss0 = self._tss_stack(uc)
        if esp0 is None:
            self.halted = True
            self.fault = "no TSS loaded for a ring 3 interrupt"
            return None

        # The frame a privilege-changing interrupt pushes, which the
        # stub's iret consumes on the way back out to user mode.
        esp = esp0
        for value in (
            syscall["ss"],
            syscall["esp"],
            syscall["eflags"],
            syscall["cs"],
            syscall["return_eip"],
        ):
            esp -= 4
            uc.mem_write(esp, int(value & 0xFFFFFFFF).to_bytes(4, "little"))

        # Only reload SS if it really changes.  Writing a segment
        # register mid-run makes Unicorn rebuild its cached descriptor
        # and it comes back as a 16-bit stack, which quietly truncates
        # every push that follows.  The kernel CPU never left ring 0, so
        # its SS is already the one the handler wants.
        if uc.reg_read(UC_X86_REG_SS) != ss0:
            uc.reg_write(UC_X86_REG_SS, ss0)
        uc.reg_write(UC_X86_REG_ESP, esp)
        for register, value in syscall["regs"].items():
            uc.reg_write(register, value)

        # An interrupt gate clears IF; a trap gate leaves it alone.
        if flags & 0x0F == 0x0E:
            uc.reg_write(
                UC_X86_REG_EFLAGS, uc.reg_read(UC_X86_REG_EFLAGS) & ~(1 << 9)
            )

        return handler

    def _set_carry(self, uc, on):
        flags = uc.reg_read(UC_X86_REG_EFLAGS)
        flags = (flags | CF) if on else (flags & ~CF)
        uc.reg_write(UC_X86_REG_EFLAGS, flags)

    # ---- INT 10h : video -------------------------------------------
    def _int10(self, uc):
        ah = uc.reg_read(UC_X86_REG_AH)
        if ah == 0x0E:
            self.teletype.append(uc.reg_read(UC_X86_REG_AL))

    # ---- INT 12h : conventional memory size ------------------------
    def _int12(self, uc):
        uc.reg_write(UC_X86_REG_AX, 639)

    # ---- INT 13h : disk --------------------------------------------
    def _int13(self, uc):
        ah = uc.reg_read(UC_X86_REG_AH)

        if ah == 0x41:  # extensions installation check
            if uc.reg_read(UC_X86_REG_BX) == 0x55AA:
                uc.reg_write(UC_X86_REG_BX, 0xAA55)
                uc.reg_write(UC_X86_REG_CX, 0x0001)
                uc.reg_write(UC_X86_REG_AH, 0x30)
                self._set_carry(uc, False)
            else:
                self._set_carry(uc, True)
            return

        if ah == 0x42:  # extended read
            ds = uc.reg_read(UC_X86_REG_DS)
            si = uc.reg_read(UC_X86_REG_SI)
            packet = uc.mem_read((ds << 4) + si, 16)
            count = int.from_bytes(packet[2:4], "little")
            offset = int.from_bytes(packet[4:6], "little")
            segment = int.from_bytes(packet[6:8], "little")
            lba = int.from_bytes(packet[8:16], "little")

            data = self._read_disk(lba, count)
            uc.mem_write((segment << 4) + offset, data)
            uc.reg_write(UC_X86_REG_AH, 0)
            self._set_carry(uc, False)
            return

        if ah == 0x08:  # drive parameters
            uc.reg_write(UC_X86_REG_CX, (0x50 << 8) | 18)  # cyl 80, 18 spt
            uc.reg_write(UC_X86_REG_DH, 1)                 # two heads
            uc.reg_write(UC_X86_REG_DL, 1)
            uc.reg_write(UC_X86_REG_AH, 0)
            self._set_carry(uc, False)
            return

        if ah == 0x02:  # CHS read
            al = uc.reg_read(UC_X86_REG_AL)
            cx = uc.reg_read(UC_X86_REG_CX)
            dh = uc.reg_read(UC_X86_REG_DH)
            sector = cx & 0x3F
            cylinder = ((cx >> 8) & 0xFF) | ((cx & 0xC0) << 2)
            lba = (cylinder * 2 + dh) * 18 + (sector - 1)

            es = uc.reg_read(UC_X86_REG_ES)
            bx = uc.reg_read(UC_X86_REG_BX)
            data = self._read_disk(lba, al)
            uc.mem_write((es << 4) + bx, data)
            uc.reg_write(UC_X86_REG_AH, 0)
            uc.reg_write(UC_X86_REG_AL, al)
            self._set_carry(uc, False)
            return

        self._set_carry(uc, True)

    def _read_disk(self, lba, count):
        start = lba * SECTOR
        end = start + count * SECTOR
        data = bytes(self.disk[start:end])
        if len(data) < count * SECTOR:
            data += b"\x00" * (count * SECTOR - len(data))
        return data

    # ---- INT 15h : miscellaneous system services -------------------
    def _int15(self, uc):
        ax = uc.reg_read(UC_X86_REG_AX)
        eax = uc.reg_read(UC_X86_REG_EAX)

        if ax == 0x2401:  # enable A20
            self.a20 = True
            uc.reg_write(UC_X86_REG_AH, 0)
            self._set_carry(uc, False)
            return

        if ax == 0xE801:  # extended memory size
            above_1m = min((self.memory_mb - 1) * 1024, 15 * 1024)
            above_16m = max(self.memory_mb - 16, 0) * 1024 // 64
            uc.reg_write(UC_X86_REG_AX, above_1m)
            uc.reg_write(UC_X86_REG_BX, above_16m)
            uc.reg_write(UC_X86_REG_CX, above_1m)
            uc.reg_write(UC_X86_REG_DX, above_16m)
            self._set_carry(uc, False)
            return

        if eax == 0xE820:  # the memory map
            self._e820(uc)
            return

        self._set_carry(uc, True)

    def _e820(self, uc):
        entries = [
            (0x00000000, 0x0009FC00, 1),                 # low RAM
            (0x0009FC00, 0x00000400, 2),                 # EBDA
            (0x000F0000, 0x00010000, 2),                 # BIOS ROM
            (0x00100000, (self.memory_mb - 1) << 20, 1), # extended RAM
            (0xFFFC0000, 0x00040000, 2),                 # firmware
        ]

        index = uc.reg_read(UC_X86_REG_EBX)
        if index >= len(entries):
            self._set_carry(uc, True)
            return

        base, length, kind = entries[index]
        di = uc.reg_read(UC_X86_REG_DI)
        es = uc.reg_read(UC_X86_REG_ES)
        record = (
            base.to_bytes(8, "little")
            + length.to_bytes(8, "little")
            + kind.to_bytes(4, "little")
            + (1).to_bytes(4, "little")
        )
        uc.mem_write((es << 4) + di, record)

        uc.reg_write(UC_X86_REG_EAX, 0x534D4150)
        uc.reg_write(UC_X86_REG_ECX, 24)
        nxt = index + 1
        uc.reg_write(UC_X86_REG_EBX, 0 if nxt >= len(entries) else nxt)
        self._set_carry(uc, False)

    # ---- INT 16h : keyboard ----------------------------------------
    def _int16(self, uc):
        ah = uc.reg_read(UC_X86_REG_AH)
        if ah in (0x00, 0x10):
            key = self.keystrokes.pop(0) if self.keystrokes else 0x0D
            uc.reg_write(UC_X86_REG_AX, (0x1C << 8) | key)
        elif ah in (0x01, 0x11):
            if self.keystrokes:
                self._set_flag(uc, ZF, False)
                uc.reg_write(UC_X86_REG_AX, (0x1C << 8) | self.keystrokes[0])
            else:
                self._set_flag(uc, ZF, True)

    def _set_flag(self, uc, mask, on):
        flags = uc.reg_read(UC_X86_REG_EFLAGS)
        flags = (flags | mask) if on else (flags & ~mask)
        uc.reg_write(UC_X86_REG_EFLAGS, flags)

    # ---- INT 19h : reboot ------------------------------------------
    def _int19(self, uc):
        self.halted = True
        uc.emu_stop()

    # ----------------------------------------------------------- ports
    def _on_in(self, uc, port, size, user_data):
        # Unicorn takes the value the CPU reads from this return value.
        mask = {1: 0xFF, 2: 0xFFFF, 4: 0xFFFFFFFF}[size]
        return self._read_port(port, size) & mask

    def _on_out(self, uc, port, size, value, user_data):
        self._write_port(port, size, value)

    def _read_port(self, port, size):
        # ---- 16550 UART on COM1 -------------------------------------
        if port == 0x3F8:
            if self.uart_lcr & 0x80:  # DLAB: divisor low byte
                return self.uart_divisor & 0xFF
            if self.uart_rx:
                return self.uart_rx.pop(0)
            return 0
        if port == 0x3F9:
            if self.uart_lcr & 0x80:  # DLAB: divisor high byte
                return (self.uart_divisor >> 8) & 0xFF
            return self.uart_ier
        if port == 0x3FA:  # interrupt identification / FIFO status
            return 0xC1
        if port == 0x3FB:
            return self.uart_lcr
        if port == 0x3FC:
            return self.uart_mcr
        if port == 0x3FD:  # line status
            status = 0x60  # transmitter holding + shift register empty
            if self.uart_rx:
                status |= 0x01  # data ready
            return status
        if port == 0x3FE:  # modem status
            return 0xB0
        if port == 0x3FF:  # scratch
            return 0

        # ---- interrupt controller ----------------------------------
        if port == 0x21:
            return self.pic_masks[0]
        if port == 0xA1:
            return self.pic_masks[1]

        # ---- keyboard controller -----------------------------------
        if port == 0x64:
            return 0x1C | (0x01 if self.keystrokes else 0x00)
        if port == 0x60:
            return self.keystrokes.pop(0) if self.keystrokes else 0

        # ---- fast A20 ----------------------------------------------
        if port == 0x92:
            return 0x02 if self.a20 else 0x00

        # ---- CMOS ---------------------------------------------------
        if port == 0x71:
            return self.cmos[self.cmos_index & 0x7F]

        # ---- CRT controller -----------------------------------------
        if port == 0x3D5:
            return 0

        # ---- ATA (IDE) primary channel ------------------------------
        if 0x1F0 <= port <= 0x1F7 or port == 0x3F6:
            return self._ata_read(port, size)

        return 0

    # ------------------------------------------------------------- ATA
    def _ata_read(self, port, size):
        if not self.ata_enabled:
            return 0x00  # a floating bus means "nothing attached"

        if port == 0x1F0:  # data register, always 16 bits wide
            if self.ata_pos + 1 < len(self.ata_buffer):
                word = int.from_bytes(
                    self.ata_buffer[self.ata_pos : self.ata_pos + 2], "little"
                )
                self.ata_pos += 2
                if self.ata_pos >= len(self.ata_buffer):
                    self.ata_status &= ~0x08  # DRQ down, transfer complete
                return word
            return 0

        if port == 0x1F4:
            return self.ata_lba_mid
        if port == 0x1F5:
            return self.ata_lba_hi
        if port in (0x1F7, 0x3F6):  # status / alternate status
            return self.ata_status

        return self.ata_regs.get(port, 0)

    def _ata_write(self, port, value):
        # The data register carries the payload of a WRITE SECTORS, not a
        # register value, so it is handled before anything else.
        if port == 0x1F0:
            if self.ata_writing:
                self.ata_buffer += (value & 0xFFFF).to_bytes(2, "little")
                if len(self.ata_buffer) >= self.ata_write_bytes:
                    start = self.ata_write_lba * SECTOR
                    end = start + self.ata_write_bytes
                    if end > len(self.disk):
                        self.disk.extend(b"\x00" * (end - len(self.disk)))
                    self.disk[start:end] = self.ata_buffer[: self.ata_write_bytes]
                    self.ata_writing = False
                    self.ata_status = 0x50  # DRQ down, transfer complete
            return

        self.ata_regs[port] = value & 0xFF

        if port != 0x1F7:
            return

        command = value & 0xFF
        if command == 0xEC:  # IDENTIFY
            self.ata_buffer = self._identify_block()
            self.ata_pos = 0
            self.ata_lba_mid = 0
            self.ata_lba_hi = 0
            self.ata_status = 0x58  # RDY | DSC | DRQ
        elif command == 0x20:  # READ SECTORS
            count = self.ata_regs.get(0x1F2, 1) or 256
            lba = (
                self.ata_regs.get(0x1F3, 0)
                | (self.ata_regs.get(0x1F4, 0) << 8)
                | (self.ata_regs.get(0x1F5, 0) << 16)
                | ((self.ata_regs.get(0x1F6, 0) & 0x0F) << 24)
            )
            self.ata_buffer = bytearray(self._read_disk(lba, count))
            self.ata_pos = 0
            self.ata_status = 0x58
        elif command == 0x30:  # WRITE SECTORS
            count = self.ata_regs.get(0x1F2, 1) or 256
            self.ata_write_lba = (
                self.ata_regs.get(0x1F3, 0)
                | (self.ata_regs.get(0x1F4, 0) << 8)
                | (self.ata_regs.get(0x1F5, 0) << 16)
                | ((self.ata_regs.get(0x1F6, 0) & 0x0F) << 24)
            )
            self.ata_write_bytes = count * SECTOR
            self.ata_buffer = bytearray()
            self.ata_writing = True
            self.ata_status = 0x58  # RDY | DSC | DRQ, waiting for data
        elif command == 0xE7:  # FLUSH CACHE
            self.ata_status = 0x50
        else:
            self.ata_status = 0x51  # ERR for anything we do not implement

    def _identify_block(self):
        words = [0] * 256
        words[0] = 0x0040  # not removable, ATA device

        total_sectors = len(self.disk) // SECTOR
        words[60] = total_sectors & 0xFFFF
        words[61] = (total_sectors >> 16) & 0xFFFF

        def put_string(start, text, length):
            padded = text.ljust(length)[:length]
            for i in range(0, length, 2):
                # the ATA spec stores strings byte swapped
                words[start + i // 2] = (ord(padded[i]) << 8) | ord(padded[i + 1])

        put_string(27, "JINO VIRTUAL DISK", 40)  # model
        put_string(10, "JINO0001", 20)           # serial number

        block = bytearray()
        for word in words:
            block += word.to_bytes(2, "little")
        return block

    def _write_port(self, port, size, value):
        self.port_log.append(("out", port, value))

        # ---- 16550 UART on COM1 -------------------------------------
        if port == 0x3F8:
            if self.uart_lcr & 0x80:
                self.uart_divisor = (self.uart_divisor & 0xFF00) | (value & 0xFF)
            elif self.uart_mcr & 0x10:
                # loopback mode: the byte comes straight back to the
                # receiver, which is exactly what serial_init probes for
                self.uart_rx.append(value & 0xFF)
            else:
                self.serial_out.append(value & 0xFF)
            return
        if port == 0x3F9:
            if self.uart_lcr & 0x80:
                self.uart_divisor = (self.uart_divisor & 0x00FF) | (
                    (value & 0xFF) << 8
                )
            else:
                self.uart_ier = value & 0xFF
            return
        if port == 0x3FA:  # FIFO control
            return
        if port == 0x3FB:
            self.uart_lcr = value & 0xFF
            return
        if port == 0x3FC:
            was_loopback = bool(self.uart_mcr & 0x10)
            self.uart_mcr = value & 0xFF
            if was_loopback and not (self.uart_mcr & 0x10):
                # leaving loopback: drop the probe byte and let the
                # queued keystrokes become readable
                self.uart_rx.clear()
                self.uart_rx.extend(self.keystrokes)
                self.keystrokes.clear()
            return

        # ---- interrupt controller ----------------------------------
        if port == 0x21:
            if self.pic_init_stage[0]:
                self.pic_init_stage[0] -= 1
            else:
                self.pic_masks[0] = value
            return
        if port == 0xA1:
            if self.pic_init_stage[1]:
                self.pic_init_stage[1] -= 1
            else:
                self.pic_masks[1] = value
            return
        if port == 0x20 and value & 0x10:
            self.pic_init_stage[0] = 3
            return
        if port == 0xA0 and value & 0x10:
            self.pic_init_stage[1] = 3
            return

        # ---- fast A20 ----------------------------------------------
        if port == 0x92:
            self.a20 = bool(value & 0x02)
            return

        # ---- CMOS ---------------------------------------------------
        if port == 0x70:
            self.cmos_index = value & 0x7F
            return
        if port == 0x71:
            self.cmos[self.cmos_index & 0x7F] = value & 0xFF
            return

        # ---- ATA (IDE) primary channel ------------------------------
        if 0x1F0 <= port <= 0x1F7 or port == 0x3F6:
            if self.ata_enabled:
                self._ata_write(port, value)
            return

        # ---- CRT controller ------------------------------------------
        if port == 0x3D4:
            self.crtc_index = value
            return
        if port == 0x3D5:
            if self.crtc_index == 0x0E:
                self.cursor = (self.cursor & 0x00FF) | ((value & 0xFF) << 8)
            elif self.crtc_index == 0x0F:
                self.cursor = (self.cursor & 0xFF00) | (value & 0xFF)
            return

    # --------------------------------------------------------- faults
    def _on_unmapped(self, uc, access, address, size, value, user_data):
        eip = uc.reg_read(UC_X86_REG_EIP)
        print(
            f"[sim] unmapped memory access at 0x{address:08x} "
            f"(eip 0x{eip:08x})",
            file=sys.stderr,
        )
        return False

    # ------------------------------------------------------- timer IRQ
    def enable_timer(self, period=200_000):
        """Deliver IRQ0 every `period` instructions.

        Unicorn has no notion of time, so the periodic tick that drives
        the kernel's uptime counter has to be injected by hand.
        """
        self._timer_period = period
        self._timer_countdown = period
        self._halt_sites = self._find_halt_instructions()
        self._int80_sites = self._find_int80_instructions()
        self._iret_sites = self._find_opcode_sites(b"\xCF")
        self.uc.hook_add(UC_HOOK_CODE, self._on_instruction)
        return self

    def _find_halt_instructions(self):
        """Addresses of the `hlt` opcodes in the loaded kernel image.

        Scanning once up front means the per-instruction hook only has
        to do a set lookup rather than read guest memory every time.
        """
        kernel = self.disk[9 * SECTOR :]
        base = 0x00100000
        return {base + i for i, byte in enumerate(kernel) if byte == 0xF4}

    def _find_opcode_sites(self, opcode):
        """Addresses in the loaded kernel image holding a given opcode."""
        kernel = self.disk[9 * SECTOR :]
        base = 0x00100000
        return frozenset(
            base + i for i in range(len(kernel)) if kernel[i : i + 1] == opcode
        )

    def _find_int80_instructions(self):
        """Addresses of the `int 0x80` opcodes in the loaded kernel image.

        A syscall issued from ring 3 has to be intercepted before the
        instruction executes; see _enter_ring0 for why.
        """
        kernel = self.disk[9 * SECTOR :]
        base = 0x00100000
        return {
            base + i
            for i in range(len(kernel) - 1)
            if kernel[i] == 0xCD and kernel[i + 1] == 0x80
        }

    def _on_instruction(self, uc, address, size, user_data):
        # This runs for every instruction, so it has to stay cheap: the
        # common case must be a decrement and a comparison.
        self.instructions += 1
        self._timer_countdown -= 1

        if size == 1 and address in self._iret_sites:
            # An iret whose frame targets a ring 3 selector would drop
            # this CPU to user mode, which Unicorn never recovers from.
            # Run the excursion on the user CPU instead and rewrite this
            # one's state so it carries straight on into the syscall.
            #
            # It all has to happen here rather than from run(): stopping
            # and restarting emu_start puts the CPU back into the 16-bit
            # mode it was created with, whatever CS says.
            esp = uc.reg_read(UC_X86_REG_ESP)
            frame = uc.mem_read(esp, 20)
            if int.from_bytes(frame[4:8], "little") & 3 == 3:
                uc.reg_write(UC_X86_REG_ESP, esp + 20)
                self._user_excursion({
                    "eip": int.from_bytes(frame[0:4], "little"),
                    "cs": int.from_bytes(frame[4:8], "little"),
                    "eflags": int.from_bytes(frame[8:12], "little"),
                    "esp": int.from_bytes(frame[12:16], "little"),
                    "ss": int.from_bytes(frame[16:20], "little"),
                    # The general registers the stub's popa just
                    # restored, which is how a syscall's return value
                    # finds its way back to the caller.
                    "regs": {
                        reg: uc.reg_read(reg)
                        for reg in (
                            UC_X86_REG_EAX, UC_X86_REG_EBX,
                            UC_X86_REG_ECX, UC_X86_REG_EDX,
                            UC_X86_REG_ESI, UC_X86_REG_EDI,
                            UC_X86_REG_EBP,
                        )
                    },
                })
                return

        if size == 1 and address in self._halt_sites:
            # `hlt` would end emulation, so do what the hardware does:
            # idle until the next interrupt.  Stepping over it and
            # forcing the tick due keeps the kernel's sleep loops moving.
            uc.reg_write(UC_X86_REG_EIP, address + 1)
            self._timer_countdown = 0

            # Once the kernel is only idling - no input left and nothing
            # being printed - there is nothing more to observe, so stop
            # rather than burn through the whole instruction budget.
            self.halt_count += 1
            produced = len(self.serial_out) + len(self.uart_rx)
            if produced != self._idle_watermark:
                self._idle_watermark = produced
                self.halt_count = 0
            elif self.halt_count > self.idle_halts:
                self.idle = True
                uc.emu_stop()
                return

        if self._timer_countdown > 0:
            return
        self._timer_countdown = self._timer_period

        if not self._protected_mode():
            return
        if not uc.reg_read(UC_X86_REG_EFLAGS) & (1 << 9):  # IF
            return
        if self.pic_masks[0] & 0x01:  # IRQ0 masked at the PIC
            return

        self._dispatch_through_idt(uc, 32)

    # ------------------------------------------------------------ run
    def run(self, max_instructions=80_000_000):
        """Emulate the machine until the instruction budget runs out."""
        self._budget = max_instructions
        try:
            self.uc.emu_start(0x7C00, 0, 0, max_instructions)
        except UcError as exc:
            eip = self.uc.reg_read(UC_X86_REG_EIP)
            self.stop_reason = f"{exc} at eip=0x{eip:08x}"
        else:
            self.stop_reason = "instruction budget exhausted"

        if self.idle:
            self.stop_reason = "idle: waiting for input"
        return self

    def screen_lines(self):
        raw = self.uc.mem_read(VGA_BASE, VGA_WIDTH * VGA_HEIGHT * 2)
        lines = []
        for row in range(VGA_HEIGHT):
            chars = []
            for col in range(VGA_WIDTH):
                index = (row * VGA_WIDTH + col) * 2
                byte = raw[index]
                chars.append(chr(byte) if 32 <= byte < 127 else " ")
            lines.append("".join(chars).rstrip())
        return lines

    def screen_text(self):
        return "\n".join(self.screen_lines())

    def serial_text(self):
        return self.serial_out.decode("latin-1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", default="build/jino.img")
    parser.add_argument("--keys", default="", help="keystrokes to feed the shell")
    parser.add_argument("--memory", type=int, default=64, help="RAM in MiB")
    parser.add_argument(
        "--instructions",
        type=int,
        default=80_000_000,
        help="emulation budget",
    )
    parser.add_argument("--serial", action="store_true", help="show serial output")
    parser.add_argument(
        "--ata", action="store_true", help="attach the image as an IDE drive"
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="write any changes the guest made back to the image file",
    )
    parser.add_argument(
        "--timer",
        type=int,
        default=0,
        help="deliver IRQ0 every N instructions (0 disables it)",
    )
    args = parser.parse_args()

    with open(args.image, "rb") as handle:
        image = handle.read()

    keys = args.keys.encode().decode("unicode_escape").encode("latin-1")
    machine = Machine(
        image, keystrokes=keys, memory_mb=args.memory, ata=args.ata
    )
    if args.timer:
        machine.enable_timer(args.timer)
    machine.run(args.instructions)

    if args.persist:
        if not args.ata:
            print("--persist needs --ata, nothing was written")
        elif bytes(machine.disk) != image:
            with open(args.image, "wb") as handle:
                handle.write(bytes(machine.disk))
            print(f"wrote the guest's changes back to {args.image}")

    print("=" * 72)
    print("VGA text screen")
    print("=" * 72)
    print(machine.screen_text())
    print("=" * 72)
    print(f"stopped: {machine.stop_reason}")

    if args.serial:
        print("-" * 72)
        print("serial output")
        print("-" * 72)
        print(machine.serial_text())

    if machine.teletype:
        print("-" * 72)
        print("BIOS teletype (bootloader)")
        print("-" * 72)
        print(machine.teletype.decode("latin-1"))


if __name__ == "__main__":
    main()
