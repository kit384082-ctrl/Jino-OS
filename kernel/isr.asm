; =====================================================================
;  Jino-OS  ::  isr.asm — interrupt entry points and dispatch
; ---------------------------------------------------------------------
;  Every vector gets a small stub that normalises the stack into a
;  common "register frame" and then calls one dispatcher.  The frame
;  layout below is shared with panic.asm and task.asm; offsets are
;  relative to the frame pointer handed to the callbacks:
;
;      +0   gs  fs  es  ds                          (16 bytes)
;      +16  edi esi ebp esp_dummy ebx edx ecx eax   (pusha, 32 bytes)
;      +48  int_no
;      +52  err_code
;      +56  eip  cs  eflags                         (pushed by the CPU)
;      +68  useresp  ss                             (only on ring change)
; =====================================================================

                bits    32
%include "kernel.inc"

                global  isr_stub_table
                global  irq_stub_table
                global  syscall_stub
                global  isr_common
                global  irq_common

                extern  idt_handlers
                extern  irq_handlers
                extern  pic_send_eoi
                extern  panic_from_exception
                extern  syscall_dispatch
                extern  task_resched_if_needed

; Frame offsets, used by everything that inspects a trap frame.
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
;  Stub generators
; ---------------------------------------------------------------------

; Exceptions that the CPU does *not* push an error code for.
%macro ISR_NOERR 1
isr_stub_%1:
                cli
                push    dword 0                 ; dummy error code
                push    dword %1
                jmp     isr_common
%endmacro

; Exceptions that arrive with an error code already on the stack.
%macro ISR_ERR 1
isr_stub_%1:
                cli
                push    dword %1
                jmp     isr_common
%endmacro

%macro IRQ_STUB 2
irq_stub_%1:
                cli
                push    dword 0
                push    dword %2
                jmp     irq_common
%endmacro

; ---- the 32 architectural exceptions --------------------------------
ISR_NOERR 0       ; divide by zero
ISR_NOERR 1       ; debug
ISR_NOERR 2       ; non-maskable interrupt
ISR_NOERR 3       ; breakpoint
ISR_NOERR 4       ; overflow
ISR_NOERR 5       ; bound range exceeded
ISR_NOERR 6       ; invalid opcode
ISR_NOERR 7       ; device not available
ISR_ERR   8       ; double fault
ISR_NOERR 9       ; coprocessor segment overrun
ISR_ERR   10      ; invalid TSS
ISR_ERR   11      ; segment not present
ISR_ERR   12      ; stack-segment fault
ISR_ERR   13      ; general protection fault
ISR_ERR   14      ; page fault
ISR_NOERR 15      ; reserved
ISR_NOERR 16      ; x87 floating point
ISR_ERR   17      ; alignment check
ISR_NOERR 18      ; machine check
ISR_NOERR 19      ; SIMD floating point
ISR_NOERR 20      ; virtualisation
ISR_ERR   21      ; control protection
ISR_NOERR 22
ISR_NOERR 23
ISR_NOERR 24
ISR_NOERR 25
ISR_NOERR 26
ISR_NOERR 27
ISR_NOERR 28
ISR_NOERR 29
ISR_ERR   30      ; security exception
ISR_NOERR 31

; ---- the 16 remapped hardware interrupts ----------------------------
IRQ_STUB 0,  32   ; programmable interval timer
IRQ_STUB 1,  33   ; keyboard
IRQ_STUB 2,  34   ; cascade
IRQ_STUB 3,  35   ; COM2
IRQ_STUB 4,  36   ; COM1
IRQ_STUB 5,  37   ; LPT2
IRQ_STUB 6,  38   ; floppy
IRQ_STUB 7,  39   ; LPT1 / spurious
IRQ_STUB 8,  40   ; real time clock
IRQ_STUB 9,  41
IRQ_STUB 10, 42
IRQ_STUB 11, 43
IRQ_STUB 12, 44   ; PS/2 mouse
IRQ_STUB 13, 45   ; FPU
IRQ_STUB 14, 46   ; primary ATA
IRQ_STUB 15, 47   ; secondary ATA

; ---------------------------------------------------------------------
; isr_common — shared exception path
; ---------------------------------------------------------------------
isr_common:
                pusha
                mov     ax, ds
                push    eax                     ; ds  (as a dword)
                mov     ax, es
                push    eax
                mov     ax, fs
                push    eax
                mov     ax, gs
                push    eax

                mov     ax, SEG_KDATA
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax

                mov     eax, esp                ; pointer to the frame
                push    eax

                mov     ebx, [esp + 4 + FRAME_INTNO]
                cmp     ebx, 32
                jae     .unhandled
                mov     edx, [idt_handlers + ebx * 4]
                test    edx, edx
                jz      .unhandled
                call    edx
                jmp     .return

.unhandled:
                call    panic_from_exception

.return:
                add     esp, 4                  ; drop the frame pointer

                pop     eax
                mov     gs, ax
                pop     eax
                mov     fs, ax
                pop     eax
                mov     es, ax
                pop     eax
                mov     ds, ax
                popa
                add     esp, 8                  ; int_no + err_code
                iret

; ---------------------------------------------------------------------
; irq_common — shared hardware interrupt path
; ---------------------------------------------------------------------
irq_common:
                pusha
                mov     ax, ds
                push    eax
                mov     ax, es
                push    eax
                mov     ax, fs
                push    eax
                mov     ax, gs
                push    eax

                mov     ax, SEG_KDATA
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax

                mov     eax, esp
                push    eax

                mov     ebx, [esp + 4 + FRAME_INTNO]
                sub     ebx, 32
                cmp     ebx, 16
                jae     .eoi
                mov     edx, [irq_handlers + ebx * 4]
                test    edx, edx
                jz      .eoi
                call    edx

.eoi:
                mov     eax, [esp + FRAME_INTNO + 4]
                sub     eax, 32
                push    eax
                call    pic_send_eoi
                add     esp, 4

                add     esp, 4                  ; drop the frame pointer

                ; The interrupt is fully acknowledged now, so this is
                ; the safe point at which to switch tasks.
                call    task_resched_if_needed

                pop     eax
                mov     gs, ax
                pop     eax
                mov     fs, ax
                pop     eax
                mov     es, ax
                pop     eax
                mov     ds, ax
                popa
                add     esp, 8
                iret

; ---------------------------------------------------------------------
; syscall_stub — INT 0x80.  Arguments in EAX (number), EBX, ECX, EDX;
;                the result is written back into the frame's EAX.
; ---------------------------------------------------------------------
syscall_stub:
                cli
                push    dword 0                 ; error code slot
                push    dword 0x80              ; int_no
                pusha
                mov     ax, ds
                push    eax
                mov     ax, es
                push    eax
                mov     ax, fs
                push    eax
                mov     ax, gs
                push    eax

                mov     ax, SEG_KDATA
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax

                mov     eax, esp
                push    eax
                call    syscall_dispatch
                add     esp, 4
                mov     [esp + FRAME_EAX], eax  ; return value

                pop     eax
                mov     gs, ax
                pop     eax
                mov     fs, ax
                pop     eax
                mov     es, ax
                pop     eax
                mov     ds, ax
                popa
                add     esp, 8
                iret

; ---------------------------------------------------------------------
                section .data
                align   4
isr_stub_table:
%assign i 0
%rep 32
                dd      isr_stub_ %+ i
%assign i i+1
%endrep

                align   4
irq_stub_table:
%assign i 0
%rep 16
                dd      irq_stub_ %+ i
%assign i i+1
%endrep
