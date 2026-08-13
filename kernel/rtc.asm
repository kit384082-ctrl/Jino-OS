; =====================================================================
;  Jino-OS  ::  rtc.asm — MC146818 real time clock / CMOS
; =====================================================================

                bits    32
%include "kernel.inc"

                global  rtc_init
                global  rtc_read_time
                global  rtc_seconds
                global  rtc_minutes
                global  rtc_hours
                global  rtc_day
                global  rtc_month
                global  rtc_year
                global  rtc_format
                global  cmos_read
                global  cmos_write

                extern  ksprintf

REG_SECONDS     equ     0x00
REG_MINUTES     equ     0x02
REG_HOURS       equ     0x04
REG_WEEKDAY     equ     0x06
REG_DAY         equ     0x07
REG_MONTH       equ     0x08
REG_YEAR        equ     0x09
REG_CENTURY     equ     0x32
REG_STATUS_A    equ     0x0A
REG_STATUS_B    equ     0x0B

                section .text

; ---------------------------------------------------------------------
; cmos_read(reg) -> EAX
; ---------------------------------------------------------------------
cmos_read:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                and     al, 0x7F                ; keep NMI enabled
                out     CMOS_ADDR, al
                IO_WAIT
                xor     eax, eax
                in      al, CMOS_DATA
                pop     ebp
                ret

; ---------------------------------------------------------------------
; cmos_write(reg, value)
; ---------------------------------------------------------------------
cmos_write:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                and     al, 0x7F
                out     CMOS_ADDR, al
                IO_WAIT
                mov     eax, [ebp + 12]
                out     CMOS_DATA, al
                pop     ebp
                ret

; ---------------------------------------------------------------------
; rtc_init — note whether the chip reports BCD and 12-hour time.
; ---------------------------------------------------------------------
rtc_init:
                push    ebp
                mov     ebp, esp

                push    dword REG_STATUS_B
                call    cmos_read
                add     esp, 4
                mov     [status_b], eax

                test    eax, 0x04               ; bit2 set -> binary mode
                jnz     .binary
                mov     dword [is_bcd], 1
                jmp     .check_hours
.binary:
                mov     dword [is_bcd], 0
.check_hours:
                mov     eax, [status_b]
                test    eax, 0x02               ; bit1 set -> 24 hour clock
                jnz     .h24
                mov     dword [is_12h], 1
                jmp     .done
.h24:
                mov     dword [is_12h], 0
.done:
                call    rtc_read_time
                pop     ebp
                ret

; ---------------------------------------------------------------------
; rtc_read_time — refresh the exported fields.  Reads twice and retries
;                 when the values disagree, which avoids catching the
;                 clock mid-update.
; ---------------------------------------------------------------------
rtc_read_time:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi

                mov     esi, 64                 ; retry budget
.retry:
                ; wait until no update is in progress
                mov     ecx, 0x10000
.wait_update:
                push    ecx
                push    dword REG_STATUS_A
                call    cmos_read
                add     esp, 4
                pop     ecx
                test    eax, 0x80
                jz      .ready
                dec     ecx
                jnz     .wait_update
.ready:
                call    read_raw
                ; keep a copy to compare against
                mov     eax, [rtc_seconds]
                mov     [prev_sec], eax
                mov     eax, [rtc_minutes]
                mov     [prev_min], eax
                mov     eax, [rtc_hours]
                mov     [prev_hour], eax
                mov     eax, [rtc_day]
                mov     [prev_day], eax

                call    read_raw

                mov     eax, [rtc_seconds]
                cmp     eax, [prev_sec]
                jne     .differs
                mov     eax, [rtc_minutes]
                cmp     eax, [prev_min]
                jne     .differs
                mov     eax, [rtc_hours]
                cmp     eax, [prev_hour]
                jne     .differs
                mov     eax, [rtc_day]
                cmp     eax, [prev_day]
                je      .stable
.differs:
                dec     esi
                jnz     .retry

.stable:
                ; ---- convert from BCD when necessary -----------------
                cmp     dword [is_bcd], 0
                je      .no_bcd

                mov     eax, [rtc_seconds]
                call    bcd_to_bin
                mov     [rtc_seconds], eax
                mov     eax, [rtc_minutes]
                call    bcd_to_bin
                mov     [rtc_minutes], eax
                mov     eax, [rtc_day]
                call    bcd_to_bin
                mov     [rtc_day], eax
                mov     eax, [rtc_month]
                call    bcd_to_bin
                mov     [rtc_month], eax
                mov     eax, [rtc_year]
                call    bcd_to_bin
                mov     [rtc_year], eax

                ; hours need care: bit 7 is the PM flag in 12-hour mode
                mov     eax, [rtc_hours]
                mov     ebx, eax
                and     eax, 0x7F
                call    bcd_to_bin
                and     ebx, 0x80
                or      eax, ebx
                mov     [rtc_hours], eax
.no_bcd:
                ; ---- 12 hour to 24 hour ------------------------------
                cmp     dword [is_12h], 0
                je      .hours_done
                mov     eax, [rtc_hours]
                test    eax, 0x80
                jz      .hours_done
                and     eax, 0x7F
                cmp     eax, 12
                je      .noon
                add     eax, 12
                jmp     .store_hours
.noon:
                mov     eax, 12
.store_hours:
                mov     [rtc_hours], eax
.hours_done:
                ; ---- turn a two digit year into a full one -----------
                mov     eax, [rtc_year]
                cmp     eax, 100
                jae     .year_done
                add     eax, 2000
                mov     [rtc_year], eax
.year_done:

                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; read_raw — pull the registers straight out of CMOS
; ---------------------------------------------------------------------
read_raw:
                push    dword REG_SECONDS
                call    cmos_read
                add     esp, 4
                mov     [rtc_seconds], eax

                push    dword REG_MINUTES
                call    cmos_read
                add     esp, 4
                mov     [rtc_minutes], eax

                push    dword REG_HOURS
                call    cmos_read
                add     esp, 4
                mov     [rtc_hours], eax

                push    dword REG_DAY
                call    cmos_read
                add     esp, 4
                mov     [rtc_day], eax

                push    dword REG_MONTH
                call    cmos_read
                add     esp, 4
                mov     [rtc_month], eax

                push    dword REG_YEAR
                call    cmos_read
                add     esp, 4
                mov     [rtc_year], eax
                ret

; ---------------------------------------------------------------------
; bcd_to_bin — EAX in, EAX out
; ---------------------------------------------------------------------
bcd_to_bin:
                push    edx
                mov     edx, eax
                and     eax, 0x0F               ; low nibble
                shr     edx, 4
                and     edx, 0x0F
                imul    edx, edx, 10
                add     eax, edx
                pop     edx
                ret

; ---------------------------------------------------------------------
; rtc_format(buf, size) -> "YYYY-MM-DD HH:MM:SS"
; ---------------------------------------------------------------------
rtc_format:
                push    ebp
                mov     ebp, esp

                call    rtc_read_time

                push    dword [rtc_seconds]
                push    dword [rtc_minutes]
                push    dword [rtc_hours]
                push    dword [rtc_day]
                push    dword [rtc_month]
                push    dword [rtc_year]
                push    dword fmt_time
                push    dword [ebp + 12]
                push    dword [ebp + 8]
                call    ksprintf
                add     esp, 36

                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
fmt_time:       db      "%04u-%02u-%02u %02u:%02u:%02u", 0

                section .bss
                alignb  4
rtc_seconds:    resd    1
rtc_minutes:    resd    1
rtc_hours:      resd    1
rtc_day:        resd    1
rtc_month:      resd    1
rtc_year:       resd    1
status_b:       resd    1
is_bcd:         resd    1
is_12h:         resd    1
prev_sec:       resd    1
prev_min:       resd    1
prev_hour:      resd    1
prev_day:       resd    1
