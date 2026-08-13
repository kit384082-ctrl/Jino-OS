; =====================================================================
;  Jino-OS  ::  syscall.asm — the int 0x80 system call interface
; ---------------------------------------------------------------------
;  The only door from ring 3 into the kernel.  EAX picks the call and
;  EBX, ECX and EDX carry the arguments, which is enough for everything
;  here and keeps the user side to a three instruction stub.
;
;  Every pointer that arrives from ring 3 is suspect, so each one is
;  checked against the region the task was actually given before the
;  kernel dereferences it.  A user program that passes a kernel address
;  gets -1 back rather than a corrupted kernel.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  syscall_init
                global  syscall_dispatch
                global  syscall_count
                global  syscall_rejected

                extern  vga_puts
                extern  vga_putc
                extern  kprintf
                extern  pit_uptime_ms
                extern  pit_ticks
                extern  kernel_version
                extern  user_leave
                extern  user_syscall_count
                extern  strlen
                extern  fs_read
                extern  fs_create
                extern  keyboard_getchar
                extern  keyboard_available

; ---- the call numbers, shared with the user side --------------------
SYS_EXIT        equ     0
SYS_WRITE       equ     1
SYS_PUTC        equ     2
SYS_UPTIME      equ     3
SYS_VERSION     equ     4
SYS_TICKS       equ     5
SYS_GETCHAR     equ     6
SYS_READFILE    equ     7
SYS_WRITEFILE   equ     8
SYS_MAX         equ     9

; The window of memory a ring 3 task is allowed to point the kernel at.
; It is the span user_map_range() opens up, and nothing else.
                extern  user_area_start
                extern  user_area_end

                section .text

syscall_init:
                mov     dword [syscall_count], 0
                mov     dword [syscall_rejected], 0
                ret

; ---------------------------------------------------------------------
; syscall_dispatch(frame) -> EAX = the value ring 3 receives
; ---------------------------------------------------------------------
syscall_dispatch:
                ENTER
                push    ebx
                push    esi
                push    edi

                inc     dword [syscall_count]
                inc     dword [user_syscall_count]

                mov     esi, [ebp + 8]          ; the trap frame
                mov     eax, [esi + 44]         ; frame->eax, the call number
                mov     ebx, [esi + 32]         ; frame->ebx
                mov     ecx, [esi + 40]         ; frame->ecx
                mov     edx, [esi + 36]         ; frame->edx

                cmp     eax, SYS_MAX
                jae     .bad_call

                jmp     [table + eax * 4]

; ---- exit(code) — never returns -------------------------------------
.exit:
                push    ebx
                call    user_leave
                ; unreachable

; ---- write(text) -> bytes written -----------------------------------
.write:
                push    ecx
                push    edx
                CALL1   user_check_string, ebx
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .rejected

                push    ebx
                CALL1   vga_puts, ebx
                pop     ebx
                CALL1   strlen, ebx
                jmp     .done

; ---- putc(char) -----------------------------------------------------
.putc:
                CALL1   vga_putc, ebx
                xor     eax, eax
                jmp     .done

; ---- uptime() -> milliseconds ---------------------------------------
.uptime:
                mov     eax, [pit_uptime_ms]
                jmp     .done

; ---- version(buffer, size) -> length copied --------------------------
;   The string lives in kernel memory, so it is copied out into the
;   caller's buffer rather than handing ring 3 a kernel pointer.
.version:
                push    ecx
                push    edx
                CALL2   user_check_range, ebx, ecx
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .rejected

                test    ecx, ecx
                jz      .rejected

                mov     esi, kernel_version
                mov     edi, ebx
                dec     ecx                     ; leave room for the NUL
                xor     edx, edx
.version_copy:
                test    ecx, ecx
                jz      .version_end
                mov     al, [esi]
                test    al, al
                jz      .version_end
                mov     [edi], al
                inc     esi
                inc     edi
                inc     edx
                dec     ecx
                jmp     .version_copy
.version_end:
                mov     byte [edi], 0
                mov     eax, edx
                jmp     .done

; ---- ticks() --------------------------------------------------------
.ticks:
                mov     eax, [pit_ticks]
                jmp     .done

; ---- getchar() -> key, or 0 when nothing is waiting -----------------
.getchar:
                call    keyboard_available
                test    eax, eax
                jz      .no_key
                call    keyboard_getchar
                jmp     .done
.no_key:
                xor     eax, eax
                jmp     .done

; ---- readfile(name, buffer, length) -> bytes, or -1 -----------------
.readfile:
                push    ecx
                push    edx
                CALL1   user_check_string, ebx
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .rejected

                push    ecx
                push    edx
                CALL2   user_check_range, ecx, edx
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .rejected

                push    edx
                push    ecx
                push    ebx
                call    fs_read
                add     esp, 12
                jmp     .done

; ---- writefile(name, buffer, length) -> 1 on success ----------------
.writefile:
                push    ecx
                push    edx
                CALL1   user_check_string, ebx
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .rejected

                push    ecx
                push    edx
                CALL2   user_check_range, ecx, edx
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .rejected

                push    edx
                push    ecx
                push    ebx
                call    fs_create
                add     esp, 12
                jmp     .done

.rejected:
                inc     dword [syscall_rejected]
.bad_call:
                mov     eax, -1
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; user_check_range(address, length) -> EAX = 1 when ring 3 owns it all
; ---------------------------------------------------------------------
user_check_range:
                ENTER
                mov     eax, [ebp + 8]          ; start
                mov     ecx, [ebp + 12]         ; length

                cmp     eax, [user_area_start]
                jb      .no

                mov     edx, eax
                add     edx, ecx
                jc      .no                     ; the span wrapped around
                cmp     edx, [user_area_end]
                ja      .no

                mov     eax, 1
                LEAVE_RET
.no:
                xor     eax, eax
                LEAVE_RET

; ---------------------------------------------------------------------
; user_check_string(pointer) -> EAX = 1 when a NUL is found in range
;
;   Walking the string inside the permitted window is what makes the
;   later strlen safe: an unterminated string cannot run into kernel
;   memory because the scan stops at the boundary.
; ---------------------------------------------------------------------
user_check_string:
                ENTER
                push    esi

                mov     esi, [ebp + 8]
                cmp     esi, [user_area_start]
                jb      .no
                mov     edx, [user_area_end]
.scan:
                cmp     esi, edx
                jae     .no
                cmp     byte [esi], 0
                je      .yes
                inc     esi
                jmp     .scan
.yes:
                mov     eax, 1
                pop     esi
                LEAVE_RET
.no:
                xor     eax, eax
                pop     esi
                LEAVE_RET

; ---------------------------------------------------------------------
                section .rodata
                align   4
table:
                dd      syscall_dispatch.exit
                dd      syscall_dispatch.write
                dd      syscall_dispatch.putc
                dd      syscall_dispatch.uptime
                dd      syscall_dispatch.version
                dd      syscall_dispatch.ticks
                dd      syscall_dispatch.getchar
                dd      syscall_dispatch.readfile
                dd      syscall_dispatch.writefile

                section .bss
                alignb  4
syscall_count:      resd 1
syscall_rejected:   resd 1
