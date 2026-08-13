; =====================================================================
;  Jino-OS  ::  printf.asm — formatted output
; ---------------------------------------------------------------------
;  Supported conversions:
;     %c  character          %s  string
;     %d / %i signed         %u  unsigned
;     %x / %X hexadecimal    %o  octal      %b  binary
;     %p  pointer (0x00000000)               %%  literal percent
;  Flags: '0' zero pad, '-' left align, width as a decimal number.
;  Output goes to the VGA console and, when present, to COM1.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  kprintf
                global  kputs
                global  kputc
                global  kvsprintf
                global  ksprintf
                global  kprint_hex32
                global  kprint_dec
                global  kprint_bytes
                global  printf_set_sink

                extern  vga_putc
                extern  vga_puts
                extern  serial_putc
                extern  utoa
                extern  strlen

SINK_VGA        equ     1
SINK_SERIAL     equ     2
SINK_BUFFER     equ     4

                section .text

; ---------------------------------------------------------------------
; printf_set_sink(mask) — pick where output should go.
; ---------------------------------------------------------------------
printf_set_sink:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                mov     [sink_mask], eax
                pop     ebp
                ret

; ---------------------------------------------------------------------
; emit(char) — internal: send one character to every active sink.
; ---------------------------------------------------------------------
emit:
                push    ebp
                mov     ebp, esp
                push    eax
                push    edx

                inc     dword [chars_written]

                mov     edx, [sink_mask]
                test    edx, SINK_BUFFER
                jz      .try_vga

                ; write into the sprintf destination if there is room
                mov     eax, [buf_pos]
                cmp     eax, [buf_limit]
                jae     .try_vga
                mov     edx, [buf_ptr]
                mov     ecx, [ebp + 8]
                mov     [edx + eax], cl
                inc     dword [buf_pos]
                mov     edx, [sink_mask]

.try_vga:
                test    edx, SINK_VGA
                jz      .try_serial
                push    dword [ebp + 8]
                call    vga_putc
                add     esp, 4
                mov     edx, [sink_mask]

.try_serial:
                test    edx, SINK_SERIAL
                jz      .done
                mov     eax, [ebp + 8]
                cmp     al, 10                  ; \n -> \r\n on the wire
                jne     .no_cr
                push    dword 13
                call    serial_putc
                add     esp, 4
.no_cr:
                push    dword [ebp + 8]
                call    serial_putc
                add     esp, 4
.done:
                pop     edx
                pop     eax
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kputc(char)
; ---------------------------------------------------------------------
kputc:
                push    ebp
                mov     ebp, esp
                push    dword [ebp + 8]
                call    emit
                add     esp, 4
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kputs(str) — string followed by a newline.
; ---------------------------------------------------------------------
kputs:
                push    ebp
                mov     ebp, esp
                push    esi
                mov     esi, [ebp + 8]
                test    esi, esi
                jz      .newline
.next:
                movzx   eax, byte [esi]
                test    al, al
                jz      .newline
                inc     esi
                push    eax
                call    emit
                add     esp, 4
                jmp     .next
.newline:
                push    dword 10
                call    emit
                add     esp, 4
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kprintf(fmt, ...) -> number of characters emitted
; ---------------------------------------------------------------------
kprintf:
                push    ebp
                mov     ebp, esp
                lea     eax, [ebp + 12]         ; first vararg
                push    eax
                push    dword [ebp + 8]
                call    kvsprintf
                add     esp, 8
                pop     ebp
                ret

; ---------------------------------------------------------------------
; ksprintf(buf, size, fmt, ...) -> length written (excluding the NUL)
; ---------------------------------------------------------------------
ksprintf:
                push    ebp
                mov     ebp, esp
                push    ebx

                mov     eax, [sink_mask]
                mov     [saved_sink], eax

                mov     eax, [ebp + 8]
                mov     [buf_ptr], eax
                mov     dword [buf_pos], 0
                mov     eax, [ebp + 12]
                test    eax, eax
                jz      .empty
                dec     eax                     ; room for the terminator
.empty:
                mov     [buf_limit], eax
                mov     dword [sink_mask], SINK_BUFFER

                lea     eax, [ebp + 20]
                push    eax
                push    dword [ebp + 16]
                call    kvsprintf
                add     esp, 8

                mov     ebx, [buf_pos]
                mov     eax, [buf_ptr]
                mov     byte [eax + ebx], 0

                mov     eax, [saved_sink]
                mov     [sink_mask], eax
                mov     eax, ebx

                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kvsprintf(fmt, args) -> characters emitted
;   args points at a flat array of 32-bit arguments.
; ---------------------------------------------------------------------
kvsprintf:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                push    ebx

                mov     dword [chars_written], 0
                mov     esi, [ebp + 8]          ; format string
                mov     edi, [ebp + 12]         ; argument pointer
                test    esi, esi
                jz      .finish

.next_char:
                movzx   eax, byte [esi]
                test    al, al
                jz      .finish
                inc     esi
                cmp     al, '%'
                je      .conversion

                push    eax
                call    emit
                add     esp, 4
                jmp     .next_char

; ---- a conversion specifier -----------------------------------------
.conversion:
                mov     dword [flag_zero], 0
                mov     dword [flag_left], 0
                mov     dword [field_width], 0

.flags:
                movzx   eax, byte [esi]
                cmp     al, '0'
                jne     .check_minus
                mov     dword [flag_zero], 1
                inc     esi
                jmp     .flags
.check_minus:
                cmp     al, '-'
                jne     .width
                mov     dword [flag_left], 1
                inc     esi
                jmp     .flags

.width:
                movzx   eax, byte [esi]
                cmp     al, '0'
                jb      .specifier
                cmp     al, '9'
                ja      .specifier
                sub     eax, '0'
                mov     ebx, [field_width]
                imul    ebx, ebx, 10
                add     ebx, eax
                mov     [field_width], ebx
                inc     esi
                jmp     .width

.specifier:
                movzx   eax, byte [esi]
                test    al, al
                jz      .finish
                inc     esi

                cmp     al, 'd'
                je      .fmt_signed
                cmp     al, 'i'
                je      .fmt_signed
                cmp     al, 'u'
                je      .fmt_unsigned
                cmp     al, 'x'
                je      .fmt_hex
                cmp     al, 'X'
                je      .fmt_hex_upper
                cmp     al, 'o'
                je      .fmt_octal
                cmp     al, 'b'
                je      .fmt_binary
                cmp     al, 'c'
                je      .fmt_char
                cmp     al, 's'
                je      .fmt_string
                cmp     al, 'p'
                je      .fmt_pointer
                cmp     al, '%'
                je      .fmt_percent

                ; unknown specifier: print it verbatim
                push    dword '%'
                call    emit
                add     esp, 4
                movzx   eax, byte [esi - 1]
                push    eax
                call    emit
                add     esp, 4
                jmp     .next_char

; ---------------------------------------------------------------------
.fmt_signed:
                mov     eax, [edi]
                add     edi, 4
                test    eax, eax
                jns     .signed_positive
                neg     eax
                push    dword 10
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], '-'
                jmp     .pad_and_emit_signed
.signed_positive:
                push    dword 10
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], 0
.pad_and_emit_signed:
                call    emit_number
                jmp     .next_char

.fmt_unsigned:
                mov     eax, [edi]
                add     edi, 4
                push    dword 10
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], 0
                call    emit_number
                jmp     .next_char

.fmt_hex:
                mov     eax, [edi]
                add     edi, 4
                push    dword 16
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], 0
                call    emit_number
                jmp     .next_char

.fmt_hex_upper:
                mov     eax, [edi]
                add     edi, 4
                push    dword 16
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], 0
                ; upper-case the digits in place
                mov     ebx, numbuf
.upper_loop:
                mov     al, [ebx]
                test    al, al
                jz      .upper_done
                cmp     al, 'a'
                jb      .upper_next
                cmp     al, 'f'
                ja      .upper_next
                sub     al, 32
                mov     [ebx], al
.upper_next:
                inc     ebx
                jmp     .upper_loop
.upper_done:
                call    emit_number
                jmp     .next_char

.fmt_octal:
                mov     eax, [edi]
                add     edi, 4
                push    dword 8
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], 0
                call    emit_number
                jmp     .next_char

.fmt_binary:
                mov     eax, [edi]
                add     edi, 4
                push    dword 2
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                mov     byte [sign_char], 0
                call    emit_number
                jmp     .next_char

.fmt_pointer:
                mov     eax, [edi]
                add     edi, 4
                push    dword 16
                push    dword numbuf
                push    eax
                call    utoa
                add     esp, 12
                push    dword '0'
                call    emit
                add     esp, 4
                push    dword 'x'
                call    emit
                add     esp, 4
                mov     dword [field_width], 8
                mov     dword [flag_zero], 1
                mov     dword [flag_left], 0
                mov     byte [sign_char], 0
                call    emit_number
                jmp     .next_char

.fmt_char:
                mov     eax, [edi]
                add     edi, 4
                and     eax, 0xFF
                mov     [numbuf], al
                mov     byte [numbuf + 1], 0
                mov     byte [sign_char], 0
                mov     dword [flag_zero], 0
                call    emit_number
                jmp     .next_char

.fmt_string:
                mov     eax, [edi]
                add     edi, 4
                test    eax, eax
                jnz     .string_ok
                mov     eax, str_null
.string_ok:
                mov     [str_ptr], eax
                call    emit_string
                jmp     .next_char

.fmt_percent:
                push    dword '%'
                call    emit
                add     esp, 4
                jmp     .next_char

.finish:
                mov     eax, [chars_written]
                pop     ebx
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; emit_number — writes numbuf honouring width, zero padding and sign.
; ---------------------------------------------------------------------
emit_number:
                push    esi
                push    ebx
                push    ecx

                ; measure the converted digits
                mov     esi, numbuf
                xor     ecx, ecx
.measure:
                cmp     byte [esi + ecx], 0
                je      .measured
                inc     ecx
                jmp     .measure
.measured:
                mov     ebx, ecx                ; digit count
                cmp     byte [sign_char], 0
                je      .no_sign_len
                inc     ebx
.no_sign_len:
                mov     eax, [field_width]
                sub     eax, ebx                ; eax = padding needed
                jns     .have_pad
                xor     eax, eax
.have_pad:
                mov     [pad_count], eax

                cmp     dword [flag_left], 0
                jne     .sign_first             ; left aligned: pad afterwards

                cmp     dword [flag_zero], 0
                jne     .zero_pad

                ; space padding comes before the sign
                mov     ecx, [pad_count]
.space_loop:
                test    ecx, ecx
                jz      .sign_first
                push    ecx
                push    dword ' '
                call    emit
                add     esp, 4
                pop     ecx
                dec     ecx
                jmp     .space_loop

.zero_pad:
                ; sign first, then zeros
                call    emit_sign
                mov     ecx, [pad_count]
.zero_loop:
                test    ecx, ecx
                jz      .digits
                push    ecx
                push    dword '0'
                call    emit
                add     esp, 4
                pop     ecx
                dec     ecx
                jmp     .zero_loop

.sign_first:
                call    emit_sign

.digits:
                mov     esi, numbuf
.digit_loop:
                movzx   eax, byte [esi]
                test    al, al
                jz      .trailing
                inc     esi
                push    eax
                call    emit
                add     esp, 4
                jmp     .digit_loop

.trailing:
                cmp     dword [flag_left], 0
                je      .done
                mov     ecx, [pad_count]
.trail_loop:
                test    ecx, ecx
                jz      .done
                push    ecx
                push    dword ' '
                call    emit
                add     esp, 4
                pop     ecx
                dec     ecx
                jmp     .trail_loop
.done:
                pop     ecx
                pop     ebx
                pop     esi
                ret

emit_sign:
                movzx   eax, byte [sign_char]
                test    al, al
                jz      .none
                push    eax
                call    emit
                add     esp, 4
                mov     byte [sign_char], 0     ; only once
.none:
                ret

; ---------------------------------------------------------------------
; emit_string — str_ptr with width handling
; ---------------------------------------------------------------------
emit_string:
                push    esi
                push    ecx
                push    ebx

                mov     esi, [str_ptr]
                xor     ebx, ebx
.measure:
                cmp     byte [esi + ebx], 0
                je      .measured
                inc     ebx
                jmp     .measure
.measured:
                mov     eax, [field_width]
                sub     eax, ebx
                jns     .have_pad
                xor     eax, eax
.have_pad:
                mov     ecx, eax

                cmp     dword [flag_left], 0
                jne     .body
.lead_pad:
                test    ecx, ecx
                jz      .body
                push    ecx
                push    dword ' '
                call    emit
                add     esp, 4
                pop     ecx
                dec     ecx
                jmp     .lead_pad

.body:
                push    ecx
                mov     esi, [str_ptr]
.body_loop:
                movzx   eax, byte [esi]
                test    al, al
                jz      .body_done
                inc     esi
                push    eax
                call    emit
                add     esp, 4
                jmp     .body_loop
.body_done:
                pop     ecx

                cmp     dword [flag_left], 0
                je      .done
.trail_pad:
                test    ecx, ecx
                jz      .done
                push    ecx
                push    dword ' '
                call    emit
                add     esp, 4
                pop     ecx
                dec     ecx
                jmp     .trail_pad
.done:
                pop     ebx
                pop     ecx
                pop     esi
                ret

; ---------------------------------------------------------------------
; kprint_hex32(value) — always eight digits with the 0x prefix
; ---------------------------------------------------------------------
kprint_hex32:
                push    ebp
                mov     ebp, esp
                push    dword [ebp + 8]
                push    dword fmt_hex32
                call    kprintf
                add     esp, 8
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kprint_dec(value)
; ---------------------------------------------------------------------
kprint_dec:
                push    ebp
                mov     ebp, esp
                push    dword [ebp + 8]
                push    dword fmt_dec
                call    kprintf
                add     esp, 8
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kprint_bytes(ptr, len) — a compact hex dump
; ---------------------------------------------------------------------
kprint_bytes:
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
                push    eax
                push    dword fmt_byte
                call    kprintf
                add     esp, 8
                inc     esi
                dec     ebx
                jmp     .next
.done:
                pop     ebx
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .data
sink_mask:      dd      SINK_VGA | SINK_SERIAL
buf_ptr:        dd      0
buf_pos:        dd      0
buf_limit:      dd      0
saved_sink:     dd      0

str_null:       db      "(null)", 0
fmt_hex32:      db      "0x%08x", 0
fmt_dec:        db      "%d", 0
fmt_byte:       db      "%02x ", 0

                section .bss
                alignb  4
chars_written:  resd    1
field_width:    resd    1
flag_zero:      resd    1
flag_left:      resd    1
pad_count:      resd    1
str_ptr:        resd    1
sign_char:      resb    1
                alignb  4
numbuf:         resb    40
