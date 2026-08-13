; =====================================================================
;  Jino-OS  ::  userprog.asm — programs that run in ring 3
; ---------------------------------------------------------------------
;  These are ordinary routines, but they execute with CPL 3 and may not
;  touch anything the kernel has not explicitly handed them.  Every
;  service they need — printing, the clock, files — goes through
;  int 0x80.  There is no call into the kernel anywhere below.
;
;  Everything the programs use lives between user_area_start and
;  user_area_end so the kernel can hand exactly that span to ring 3 and
;  reject any pointer that falls outside it.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  user_demo
                global  user_faulter
                global  user_area_start
                global  user_area_end
                global  user_program_size

SYS_EXIT        equ     0
SYS_WRITE       equ     1
SYS_PUTC        equ     2
SYS_UPTIME      equ     3
SYS_VERSION     equ     4
SYS_TICKS       equ     5

; A three instruction call stub, the whole of the user side ABI.
%macro SYSCALL0 1
                mov     eax, %1
                int     0x80
%endmacro

%macro SYSCALL1 2
                mov     eax, %1
                mov     ebx, %2
                int     0x80
%endmacro

; ---------------------------------------------------------------------
;  The code and data below are what ring 3 is allowed to reach.  Keeping
;  them adjacent lets the kernel open one contiguous range.
; ---------------------------------------------------------------------
                section .text
                align   PAGE_SIZE
user_area_start_marker:

; ---------------------------------------------------------------------
; user_demo — the sample ring 3 program.
;
;   Prints through the kernel, asks it the time, and exits with a code.
;   It never touches kernel memory directly.
; ---------------------------------------------------------------------
user_demo:
                SYSCALL1 SYS_WRITE, msg_hello

                ; Ask the kernel who it is.  The answer lives in kernel
                ; memory, which ring 3 can neither read itself nor hand
                ; back to SYS_WRITE, so the kernel copies it out for us.
                mov     eax, SYS_VERSION
                mov     ebx, verbuf
                mov     ecx, VERBUF_SIZE
                int     0x80

                SYSCALL1 SYS_WRITE, verbuf

                SYSCALL1 SYS_WRITE, msg_nl

                ; and how long it has been up
                SYSCALL0 SYS_UPTIME
                call    print_number
                SYSCALL1 SYS_WRITE, msg_ms

                SYSCALL1 SYS_WRITE, msg_bye

                ; leave with a recognisable status
                SYSCALL1 SYS_EXIT, 42

                ; unreachable: sys_exit does not come back
.spin:          jmp     .spin

; ---------------------------------------------------------------------
; user_faulter — a deliberately badly behaved ring 3 program.
;
;   It asks the kernel to print a string that lives in kernel memory.
;   The pointer check has to refuse, and the program has to be told so
;   rather than the kernel obliging.
; ---------------------------------------------------------------------
user_faulter:
                SYSCALL1 SYS_WRITE, msg_probe

                ; 0x00100000 is the kernel's own base address
                mov     eax, SYS_WRITE
                mov     ebx, 0x00100000
                int     0x80

                cmp     eax, -1
                jne     .allowed

                SYSCALL1 SYS_WRITE, msg_refused
                SYSCALL1 SYS_EXIT, 0
.allowed:
                SYSCALL1 SYS_WRITE, msg_allowed
                SYSCALL1 SYS_EXIT, 1

; ---------------------------------------------------------------------
; print_number(EAX) — decimal, through SYS_PUTC one digit at a time.
; ---------------------------------------------------------------------
print_number:
                push    ebx
                push    ecx
                push    edx
                push    esi

                mov     esi, numbuf + 15
                mov     byte [esi], 0
                mov     ecx, 10

                test    eax, eax
                jnz     .convert
                dec     esi
                mov     byte [esi], '0'
                jmp     .emit
.convert:
                xor     edx, edx
                div     ecx
                add     dl, '0'
                dec     esi
                mov     [esi], dl
                test    eax, eax
                jnz     .convert
.emit:
                mov     eax, SYS_WRITE
                mov     ebx, esi
                int     0x80

                pop     esi
                pop     edx
                pop     ecx
                pop     ebx
                ret

; ---------------------------------------------------------------------
;  Data the programs read.  It sits in .text on purpose: the region is
;  handed to ring 3 as one span, and a user program has no business
;  writing to it.
; ---------------------------------------------------------------------
msg_hello:      db      "  [ring 3] hello from user mode", 10, 0
msg_nl:         db      10, 0
msg_ms:         db      " ms since boot", 10, 0
msg_bye:        db      "  [ring 3] exiting", 10, 0
msg_probe:      db      "  [ring 3] trying to read kernel memory...", 10, 0
msg_refused:    db      "  [ring 3] the kernel refused, as it should", 10, 0
msg_allowed:    db      "  [ring 3] the kernel allowed it, which is a bug", 10, 0

                align   4
numbuf:         times 16 db 0

; Where the kernel version is copied to, so that the pointer handed back
; to SYS_WRITE is one ring 3 actually owns.
VERBUF_SIZE     equ     64
verbuf:         times VERBUF_SIZE db 0

                align   PAGE_SIZE
user_area_end_marker:

; The span the kernel opens to ring 3, as addresses rather than labels
; so the C-style callers can read them.
                section .data
                align   4
user_area_start:    dd user_area_start_marker
user_area_end:      dd user_area_end_marker
user_program_size:  dd user_area_end_marker - user_area_start_marker
