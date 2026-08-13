; =====================================================================
;  Jino-OS  ::  idt.asm — Interrupt Descriptor Table
; ---------------------------------------------------------------------
;  256 gates: the 32 architectural exceptions, the 16 remapped IRQs and
;  a software interrupt (0x80) reserved for system calls.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  idt_init
                global  idt_set_gate
                global  idt_register_handler
                global  idt_handlers
                global  irq_handlers
                global  idt_enable
                global  idt_disable

                extern  isr_stub_table
                extern  irq_stub_table
                extern  syscall_stub

IDT_ENTRIES     equ     256

; gate type/attribute bytes
GATE_INT32_K    equ     0x8E            ; present, ring 0, 32-bit interrupt
GATE_INT32_U    equ     0xEE            ; present, ring 3, 32-bit interrupt
GATE_TRAP32_K   equ     0x8F            ; present, ring 0, 32-bit trap

                section .text

; ---------------------------------------------------------------------
; idt_init — install every stub and load IDTR.
; ---------------------------------------------------------------------
idt_init:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                ; ---- clear the table ---------------------------------
                mov     edi, idt
                mov     ecx, IDT_ENTRIES * 8 / 4
                xor     eax, eax
                rep     stosd

                ; ---- exceptions 0..31 --------------------------------
                xor     ebx, ebx                ; vector number
.exceptions:
                mov     esi, [isr_stub_table + ebx * 4]
                push    dword GATE_INT32_K
                push    dword SEG_KCODE
                push    esi
                push    ebx
                call    idt_set_gate
                add     esp, 16
                inc     ebx
                cmp     ebx, 32
                jb      .exceptions

                ; ---- hardware IRQs, vectors 32..47 -------------------
                xor     ebx, ebx
.irqs:
                mov     esi, [irq_stub_table + ebx * 4]
                lea     eax, [ebx + 32]
                push    dword GATE_INT32_K
                push    dword SEG_KCODE
                push    esi
                push    eax
                call    idt_set_gate
                add     esp, 16
                inc     ebx
                cmp     ebx, 16
                jb      .irqs

                ; ---- the syscall gate, callable from user mode -------
                push    dword GATE_INT32_U
                push    dword SEG_KCODE
                push    dword syscall_stub
                push    dword 0x80
                call    idt_set_gate
                add     esp, 16

                ; ---- load ---------------------------------------------
                mov     word [idt_descriptor], IDT_ENTRIES * 8 - 1
                mov     dword [idt_descriptor + 2], idt
                lidt    [idt_descriptor]

                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; idt_set_gate(vector, handler, selector, flags)
; ---------------------------------------------------------------------
idt_set_gate:
                push    ebp
                mov     ebp, esp
                push    edi

                mov     edi, [ebp + 8]          ; vector
                and     edi, 0xFF
                shl     edi, 3
                add     edi, idt

                mov     eax, [ebp + 12]         ; handler address
                mov     [edi + 0], ax           ; offset 15:0
                mov     edx, [ebp + 16]         ; selector
                mov     [edi + 2], dx
                mov     byte [edi + 4], 0       ; always zero
                mov     edx, [ebp + 20]         ; type/attributes
                mov     [edi + 5], dl
                shr     eax, 16
                mov     [edi + 6], ax           ; offset 31:16

                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; idt_register_handler(vector, callback)
;   Callback receives a pointer to the saved register frame in EAX and
;   is invoked from the common dispatcher in isr.asm.
; ---------------------------------------------------------------------
idt_register_handler:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                and     eax, 0xFF
                mov     edx, [ebp + 12]
                cmp     eax, 32
                jae     .irq_slot
                mov     [idt_handlers + eax * 4], edx
                jmp     .done
.irq_slot:
                cmp     eax, 48
                jae     .other
                sub     eax, 32
                mov     [irq_handlers + eax * 4], edx
                jmp     .done
.other:
                mov     [idt_handlers + eax * 4], edx
.done:
                pop     ebp
                ret

; ---------------------------------------------------------------------
idt_enable:
                sti
                ret

idt_disable:
                cli
                ret

; ---------------------------------------------------------------------
                section .bss
                alignb  8
idt:            resb    IDT_ENTRIES * 8
idt_descriptor: resb    6
                alignb  4
idt_handlers:   resd    IDT_ENTRIES     ; exception + software callbacks
irq_handlers:   resd    16              ; hardware IRQ callbacks
