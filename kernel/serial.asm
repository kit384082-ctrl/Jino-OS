; =====================================================================
;  Jino-OS  ::  serial.asm — 16550 UART on COM1
; ---------------------------------------------------------------------
;  Used as a debug console: everything the kernel prints can also be
;  captured by the host through the serial line.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  serial_init
                global  serial_putc
                global  serial_puts
                global  serial_write
                global  serial_getc
                global  serial_poll
                global  serial_available

; Register offsets from the port base
UART_DATA       equ     0       ; DLAB=0: data
UART_IER        equ     1       ; DLAB=0: interrupt enable
UART_DLL        equ     0       ; DLAB=1: divisor low
UART_DLH        equ     1       ; DLAB=1: divisor high
UART_IIR        equ     2       ; read: interrupt id
UART_FCR        equ     2       ; write: FIFO control
UART_LCR        equ     3       ; line control
UART_MCR        equ     4       ; modem control
UART_LSR        equ     5       ; line status
UART_MSR        equ     6       ; modem status
UART_SCRATCH    equ     7

LSR_DATA_READY  equ     1 << 0
LSR_THR_EMPTY   equ     1 << 5

                section .text

; ---------------------------------------------------------------------
; serial_init — 38400 baud, 8N1, FIFOs on.  Returns EAX=1 when a UART
;               actually answered the loopback probe.
; ---------------------------------------------------------------------
serial_init:
                push    edx
                mov     dx, COM1_BASE + UART_IER
                xor     al, al
                out     dx, al                  ; interrupts off while we set up

                mov     dx, COM1_BASE + UART_LCR
                mov     al, 0x80                ; DLAB on
                out     dx, al

                mov     dx, COM1_BASE + UART_DLL
                mov     al, 3                   ; 115200 / 3 = 38400 baud
                out     dx, al
                mov     dx, COM1_BASE + UART_DLH
                xor     al, al
                out     dx, al

                mov     dx, COM1_BASE + UART_LCR
                mov     al, 0x03                ; 8 bits, no parity, 1 stop
                out     dx, al

                mov     dx, COM1_BASE + UART_FCR
                mov     al, 0xC7                ; enable + clear FIFOs, 14 byte
                out     dx, al

                mov     dx, COM1_BASE + UART_MCR
                mov     al, 0x1E                ; loopback for the self test
                out     dx, al

                mov     dx, COM1_BASE + UART_DATA
                mov     al, 0xAE
                out     dx, al
                mov     dx, COM1_BASE + UART_DATA
                in      al, dx
                cmp     al, 0xAE
                jne     .absent

                mov     dx, COM1_BASE + UART_MCR
                mov     al, 0x0F                ; DTR, RTS, OUT1, OUT2
                out     dx, al
                mov     byte [serial_ok], 1
                mov     eax, 1
                pop     edx
                ret
.absent:
                mov     byte [serial_ok], 0
                xor     eax, eax
                pop     edx
                ret

; ---------------------------------------------------------------------
; serial_putc(char)
; ---------------------------------------------------------------------
serial_putc:
                push    ebp
                mov     ebp, esp
                cmp     byte [serial_ok], 0
                je      .done
                push    edx
                push    ecx

                mov     ecx, 0x00100000         ; bounded spin
.wait:
                mov     dx, COM1_BASE + UART_LSR
                in      al, dx
                test    al, LSR_THR_EMPTY
                jnz     .ready
                dec     ecx
                jnz     .wait
                jmp     .out                    ; give up rather than hang
.ready:
                mov     eax, [ebp + 8]
                mov     dx, COM1_BASE + UART_DATA
                out     dx, al
.out:
                pop     ecx
                pop     edx
.done:
                pop     ebp
                ret

; ---------------------------------------------------------------------
; serial_puts(char *) — translates \n into \r\n for terminals.
; ---------------------------------------------------------------------
serial_puts:
                push    ebp
                mov     ebp, esp
                push    esi
                mov     esi, [ebp + 8]
                test    esi, esi
                jz      .done
.next:
                movzx   eax, byte [esi]
                test    al, al
                jz      .done
                inc     esi
                cmp     al, 10
                jne     .plain
                push    dword 13
                call    serial_putc
                add     esp, 4
                mov     eax, 10
.plain:
                push    eax
                call    serial_putc
                add     esp, 4
                jmp     .next
.done:
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; serial_write(buf, len)
; ---------------------------------------------------------------------
serial_write:
                push    ebp
                mov     ebp, esp
                push    esi
                push    ebx
                mov     esi, [ebp + 8]
                mov     ebx, [ebp + 12]
.next:
                test    ebx, ebx
                jz      .done
                movzx   eax, byte [esi]
                inc     esi
                dec     ebx
                push    eax
                call    serial_putc
                add     esp, 4
                jmp     .next
.done:
                pop     ebx
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; serial_available -> EAX = 1 when a byte is waiting
; ---------------------------------------------------------------------
serial_available:
                push    edx
                xor     eax, eax
                cmp     byte [serial_ok], 0
                je      .done
                mov     dx, COM1_BASE + UART_LSR
                in      al, dx
                and     eax, LSR_DATA_READY
.done:
                pop     edx
                ret

; ---------------------------------------------------------------------
; serial_poll -> EAX = byte, or -1 when nothing is pending
; ---------------------------------------------------------------------
serial_poll:
                push    edx
                call    serial_available
                test    eax, eax
                jz      .empty
                mov     dx, COM1_BASE + UART_DATA
                xor     eax, eax
                in      al, dx
                pop     edx
                ret
.empty:
                mov     eax, -1
                pop     edx
                ret

; ---------------------------------------------------------------------
; serial_getc -> EAX, blocking
; ---------------------------------------------------------------------
serial_getc:
.wait:
                call    serial_poll
                cmp     eax, -1
                je      .wait
                ret

; ---------------------------------------------------------------------
                section .bss
serial_ok:      resb    1
