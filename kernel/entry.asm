; =====================================================================
;  Jino-OS  ::  entry.asm — the very first kernel code to execute
; ---------------------------------------------------------------------
;  stage2 jumps here in 32-bit protected mode with:
;      EAX = BOOTINFO_MAGIC
;      EBX = pointer to the boot information block
;      flat 4 GiB code/data selectors already loaded
;  Interrupts are off and paging is disabled.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  _start
                global  boot_magic
                global  boot_info_ptr
                global  kernel_stack_top

                extern  kmain
                extern  __bss_start
                extern  __bss_end

                section .text.entry
; ---------------------------------------------------------------------
_start:
                cli
                cld

                ; A stack of our own before we touch anything else.
                mov     esp, kernel_stack_top

                ; Preserve what the loader handed us.
                mov     [boot_magic], eax
                mov     [boot_info_ptr], ebx

                ; A frame pointer of zero terminates stack traces.
                xor     ebp, ebp
                push    ebp
                push    ebp

                call    clear_bss
                call    check_cpu

                ; kmain(magic, bootinfo)
                push    dword [boot_info_ptr]
                push    dword [boot_magic]
                call    kmain
                add     esp, 8

                ; kmain is not supposed to come back.
halt_forever:
                cli
.loop:          hlt
                jmp     .loop

; ---------------------------------------------------------------------
; clear_bss — the loader copies only the on-disk image, so .bss has to
;             be zeroed by hand before any C-style globals are touched.
; ---------------------------------------------------------------------
clear_bss:
                mov     edi, __bss_start
                mov     ecx, __bss_end
                sub     ecx, edi
                jbe     .done
                add     ecx, 3
                shr     ecx, 2
                xor     eax, eax
                rep     stosd
.done:
                ret

; ---------------------------------------------------------------------
; check_cpu — make sure we are on something at least 486-class with
;             CPUID available; store the result for cpu.asm to report.
; ---------------------------------------------------------------------
                global  cpu_has_cpuid
check_cpu:
                ; The AC bit in EFLAGS only sticks on a 486 and above.
                pushfd
                pop     eax
                mov     ecx, eax
                xor     eax, 1 << 18            ; AC
                push    eax
                popfd
                pushfd
                pop     eax
                push    ecx
                popfd                           ; restore
                xor     eax, ecx
                test    eax, 1 << 18
                jz      .too_old

                ; The ID bit tells us whether CPUID exists.
                pushfd
                pop     eax
                mov     ecx, eax
                xor     eax, 1 << 21            ; ID
                push    eax
                popfd
                pushfd
                pop     eax
                push    ecx
                popfd
                xor     eax, ecx
                test    eax, 1 << 21
                jz      .no_cpuid

                mov     byte [cpu_has_cpuid], 1
                ret

.no_cpuid:
                mov     byte [cpu_has_cpuid], 0
                ret

.too_old:
                ; Nothing to print with yet — say so straight to VGA.
                mov     edi, VGA_MEMORY
                mov     esi, msg_too_old
                mov     ah, VGA_ATTR(COLOR_WHITE, COLOR_RED)
.next:
                lodsb
                test    al, al
                jz      .stop
                mov     [edi], ax
                add     edi, 2
                jmp     .next
.stop:
                jmp     halt_forever

                section .rodata
msg_too_old:    db      "Jino-OS requires an i486 or newer CPU", 0

; ---------------------------------------------------------------------
; These are written before clear_bss runs, so they cannot live in .bss.
                section .data
                align   4
boot_magic:     dd      0
boot_info_ptr:  dd      0
cpu_has_cpuid:  db      0

; The stack deliberately lives outside .bss: clear_bss runs *on* this
; stack, so zeroing it would destroy its own return address.
                section .stack nobits alloc noexec write align=16
kernel_stack:   resb    KERNEL_STACK_SIZE
kernel_stack_top:
