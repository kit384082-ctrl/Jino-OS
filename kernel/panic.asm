; =====================================================================
;  Jino-OS  ::  panic.asm — fatal error reporting
; ---------------------------------------------------------------------
;  Prints the CPU state, decodes the exception and stops the machine.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  panic
                global  panic_from_exception
                global  dump_registers
                global  stack_trace

                extern  kprintf
                extern  vga_set_color
                extern  vga_clear
                extern  cpu_read_cr0
                extern  cpu_read_cr2
                extern  cpu_read_cr3
                extern  cpu_read_cr4

; the trap frame layout produced by isr.asm
FRAME_GS        equ     0
FRAME_FS        equ     4
FRAME_ES        equ     8
FRAME_DS        equ     12
FRAME_EDI       equ     16
FRAME_ESI       equ     20
FRAME_EBP       equ     24
FRAME_ESPD      equ     28
FRAME_EBX       equ     32
FRAME_EDX       equ     36
FRAME_ECX       equ     40
FRAME_EAX       equ     44
FRAME_INTNO     equ     48
FRAME_ERRCODE   equ     52
FRAME_EIP       equ     56
FRAME_CS        equ     60
FRAME_EFLAGS    equ     64
FRAME_USERESP   equ     68
FRAME_SS        equ     72

                section .text

; ---------------------------------------------------------------------
; panic(message) — never returns
; ---------------------------------------------------------------------
panic:
                cli
                push    ebp
                mov     ebp, esp

                push    dword VGA_ATTR(COLOR_WHITE, COLOR_RED)
                call    vga_set_color
                add     esp, 4

                push    dword msg_banner
                call    kprintf
                add     esp, 4

                push    dword [ebp + 8]
                push    dword fmt_panic
                call    kprintf
                add     esp, 8

                call    dump_control_registers

                push    dword msg_halted
                call    kprintf
                add     esp, 4

.halt:
                cli
                hlt
                jmp     .halt

; ---------------------------------------------------------------------
; panic_from_exception(frame) — called by the ISR dispatcher for any
;                               exception without its own handler.
; ---------------------------------------------------------------------
panic_from_exception:
                cli
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi

                mov     esi, [ebp + 8]          ; trap frame

                push    dword VGA_ATTR(COLOR_WHITE, COLOR_RED)
                call    vga_set_color
                add     esp, 4

                push    dword msg_banner
                call    kprintf
                add     esp, 4

                ; ---- which exception was it? -------------------------
                mov     eax, [esi + FRAME_INTNO]
                mov     ebx, eax
                cmp     eax, 32
                jb      .known
                mov     ebx, 32                 ; the "unknown" slot
.known:
                mov     edx, [exception_names + ebx * 4]

                push    dword [esi + FRAME_ERRCODE]
                push    edx
                push    dword [esi + FRAME_INTNO]
                push    dword fmt_exception
                call    kprintf
                add     esp, 16

                push    esi
                call    dump_registers
                add     esp, 4

                call    dump_control_registers

                ; ---- a short stack trace -----------------------------
                push    dword [esi + FRAME_EBP]
                call    stack_trace
                add     esp, 4

                push    dword msg_halted
                call    kprintf
                add     esp, 4
.halt:
                cli
                hlt
                jmp     .halt

; ---------------------------------------------------------------------
; dump_registers(frame)
; ---------------------------------------------------------------------
dump_registers:
                push    ebp
                mov     ebp, esp
                push    esi
                mov     esi, [ebp + 8]

                push    dword [esi + FRAME_EDX]
                push    dword [esi + FRAME_ECX]
                push    dword [esi + FRAME_EBX]
                push    dword [esi + FRAME_EAX]
                push    dword fmt_regs1
                call    kprintf
                add     esp, 20

                push    dword [esi + FRAME_EDI]
                push    dword [esi + FRAME_ESI]
                push    dword [esi + FRAME_EBP]
                push    dword [esi + FRAME_ESPD]
                push    dword fmt_regs2
                call    kprintf
                add     esp, 20

                push    dword [esi + FRAME_EFLAGS]
                push    dword [esi + FRAME_CS]
                push    dword [esi + FRAME_EIP]
                push    dword fmt_regs3
                call    kprintf
                add     esp, 16

                push    dword [esi + FRAME_GS]
                push    dword [esi + FRAME_FS]
                push    dword [esi + FRAME_ES]
                push    dword [esi + FRAME_DS]
                push    dword fmt_regs4
                call    kprintf
                add     esp, 20

                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; dump_control_registers
; ---------------------------------------------------------------------
dump_control_registers:
                push    ebx
                push    esi
                push    edi

                call    cpu_read_cr0
                mov     ebx, eax
                call    cpu_read_cr2
                mov     esi, eax
                call    cpu_read_cr3
                mov     edi, eax
                call    cpu_read_cr4

                push    eax
                push    edi
                push    esi
                push    ebx
                push    dword fmt_cregs
                call    kprintf
                add     esp, 20

                pop     edi
                pop     esi
                pop     ebx
                ret

; ---------------------------------------------------------------------
; stack_trace(ebp) — walk the saved frame pointers.
; ---------------------------------------------------------------------
stack_trace:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi

                push    dword msg_trace
                call    kprintf
                add     esp, 4

                mov     esi, [ebp + 8]
                xor     ebx, ebx
.loop:
                test    esi, esi
                jz      .done
                cmp     ebx, 12                 ; keep it short
                jae     .done

                ; a frame pointer below 1 MiB is not plausible here
                cmp     esi, KERNEL_PHYS_BASE
                jb      .done
                cmp     esi, 0xF0000000
                ja      .done

                mov     eax, [esi + 4]          ; the return address
                test    eax, eax
                jz      .done

                push    eax
                push    ebx
                push    dword fmt_frame
                call    kprintf
                add     esp, 12

                mov     eax, [esi]              ; the caller's frame
                cmp     eax, esi                ; guard against loops
                jbe     .done
                mov     esi, eax
                inc     ebx
                jmp     .loop
.done:
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
msg_banner:     db      10, "=== KERNEL PANIC ===============================================", 10, 0
fmt_panic:      db      "  %s", 10, 0
fmt_exception:  db      "  exception %u: %s (error code 0x%x)", 10, 0
fmt_regs1:      db      "  eax %08x  ebx %08x  ecx %08x  edx %08x", 10, 0
fmt_regs2:      db      "  esp %08x  ebp %08x  esi %08x  edi %08x", 10, 0
fmt_regs3:      db      "  eip %08x  cs  %04x      eflags %08x", 10, 0
fmt_regs4:      db      "  ds  %04x      es  %04x      fs  %04x      gs %04x", 10, 0
fmt_cregs:      db      "  cr0 %08x  cr2 %08x  cr3 %08x  cr4 %08x", 10, 0
msg_trace:      db      "  call trace:", 10, 0
fmt_frame:      db      "    [%u] 0x%08x", 10, 0
msg_halted:     db      "  system halted.", 10, "================================================================", 10, 0

e00:  db "divide by zero", 0
e01:  db "debug", 0
e02:  db "non-maskable interrupt", 0
e03:  db "breakpoint", 0
e04:  db "overflow", 0
e05:  db "bound range exceeded", 0
e06:  db "invalid opcode", 0
e07:  db "device not available", 0
e08:  db "double fault", 0
e09:  db "coprocessor segment overrun", 0
e10:  db "invalid TSS", 0
e11:  db "segment not present", 0
e12:  db "stack-segment fault", 0
e13:  db "general protection fault", 0
e14:  db "page fault", 0
e15:  db "reserved", 0
e16:  db "x87 floating point exception", 0
e17:  db "alignment check", 0
e18:  db "machine check", 0
e19:  db "SIMD floating point exception", 0
e20:  db "virtualisation exception", 0
e21:  db "control protection exception", 0
e22:  db "reserved", 0
e30:  db "security exception", 0
eun:  db "unknown exception", 0

                align   4
exception_names:
                dd e00, e01, e02, e03, e04, e05, e06, e07
                dd e08, e09, e10, e11, e12, e13, e14, e15
                dd e16, e17, e18, e19, e20, e21, e22, e22
                dd e22, e22, e22, e22, e22, e22, e30, e22
                dd eun
