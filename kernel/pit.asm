; =====================================================================
;  Jino-OS  ::  pit.asm — 8254 programmable interval timer
; ---------------------------------------------------------------------
;  Channel 0 drives IRQ0 and gives the kernel its tick, uptime counter
;  and a busy-wait sleep with millisecond resolution.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  pit_init
                global  pit_handler
                global  pit_ticks
                global  pit_uptime_ms
                global  pit_uptime_seconds
                global  pit_sleep_ms
                global  pit_frequency
                global  pit_set_callback

                extern  idt_register_handler
                extern  pic_unmask_irq

                section .text

; ---------------------------------------------------------------------
; pit_init(frequency_hz)
; ---------------------------------------------------------------------
pit_init:
                push    ebp
                mov     ebp, esp
                push    ebx

                mov     ebx, [ebp + 8]
                test    ebx, ebx
                jnz     .have_freq
                mov     ebx, 100                ; a sane default
.have_freq:
                cmp     ebx, 19                 ; below this the divisor
                jae     .not_too_slow           ; would not fit in 16 bits
                mov     ebx, 19
.not_too_slow:
                cmp     ebx, PIT_FREQ
                jbe     .in_range
                mov     ebx, PIT_FREQ
.in_range:
                mov     [pit_frequency], ebx

                ; divisor = 1193182 / frequency
                mov     eax, PIT_FREQ
                xor     edx, edx
                div     ebx
                mov     [pit_divisor], eax

                ; channel 0, lobyte/hibyte, mode 3 (square wave), binary
                push    eax
                mov     al, 0x36
                out     PIT_CMD, al
                IO_WAIT
                pop     eax

                out     PIT_CH0, al             ; low byte
                IO_WAIT
                shr     eax, 8
                out     PIT_CH0, al             ; high byte
                IO_WAIT

                ; how many milliseconds one tick is worth (fixed point 16.16)
                mov     eax, 1000
                shl     eax, 16
                xor     edx, edx
                div     ebx
                mov     [ms_per_tick_fx], eax

                mov     dword [pit_ticks], 0
                mov     dword [pit_ms_accum], 0

                push    dword pit_handler
                push    dword 32                ; vector for IRQ0
                call    idt_register_handler
                add     esp, 8

                push    dword 0
                call    pic_unmask_irq
                add     esp, 4

                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pit_handler(frame) — called from the IRQ dispatcher.
; ---------------------------------------------------------------------
pit_handler:
                push    ebp
                mov     ebp, esp
                push    eax
                push    edx

                inc     dword [pit_ticks]

                ; accumulate fractional milliseconds
                mov     eax, [pit_ms_accum]
                add     eax, [ms_per_tick_fx]
                mov     [pit_ms_accum], eax
                shr     eax, 16
                test    eax, eax
                jz      .no_ms
                add     [pit_uptime_ms], eax
                shl     eax, 16
                sub     [pit_ms_accum], eax
.no_ms:
                ; a user supplied callback, if any
                mov     eax, [pit_callback]
                test    eax, eax
                jz      .done
                push    dword [ebp + 8]
                call    eax
                add     esp, 4
.done:
                pop     edx
                pop     eax
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pit_set_callback(fn) — invoked on every tick, NULL to remove.
; ---------------------------------------------------------------------
pit_set_callback:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                mov     [pit_callback], eax
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pit_uptime_seconds -> EAX
; ---------------------------------------------------------------------
pit_uptime_seconds:
                mov     eax, [pit_uptime_ms]
                xor     edx, edx
                mov     ecx, 1000
                div     ecx
                ret

; ---------------------------------------------------------------------
; pit_sleep_ms(milliseconds) — spins with interrupts enabled.
; ---------------------------------------------------------------------
pit_sleep_ms:
                push    ebp
                mov     ebp, esp
                push    ebx

                mov     ebx, [pit_uptime_ms]
                add     ebx, [ebp + 8]          ; deadline

                ; If interrupts are disabled the tick will never advance,
                ; so fall back to a calibrated delay loop instead.
                pushfd
                pop     eax
                test    eax, 1 << 9             ; IF
                jz      .busy_loop

.wait:
                hlt
                mov     eax, [pit_uptime_ms]
                cmp     eax, ebx
                jb      .wait
                jmp     .done

.busy_loop:
                mov     eax, [ebp + 8]
                test    eax, eax
                jz      .done
                mov     ecx, 20000              ; rough per-millisecond count
                mul     ecx
.spin:
                dec     eax
                jnz     .spin
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .data
pit_frequency:  dd      100
pit_divisor:    dd      11932
ms_per_tick_fx: dd      0
pit_callback:   dd      0

                section .bss
                alignb  4
pit_ticks:      resd    1
pit_uptime_ms:  resd    1
pit_ms_accum:   resd    1
