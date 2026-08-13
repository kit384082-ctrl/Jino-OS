; =====================================================================
;  Jino-OS  ::  string.asm — memory and string primitives
; =====================================================================

                bits    32
%include "kernel.inc"

                global  memset
                global  memcpy
                global  memmove
                global  memcmp
                global  strlen
                global  strcmp
                global  strncmp
                global  strcpy
                global  strncpy
                global  strchr
                global  strtok_r
                global  itoa
                global  utoa
                global  atoi
                global  toupper
                global  tolower
                global  isspace
                global  isdigit
                global  isalpha
                global  strcasecmp
                global  strtrim

                section .text

; ---------------------------------------------------------------------
; memset(dst, value, count) -> dst
; ---------------------------------------------------------------------
memset:
                push    ebp
                mov     ebp, esp
                push    edi
                push    ecx
                push    ebx

                mov     edi, [ebp + 8]
                mov     eax, [ebp + 12]
                mov     ecx, [ebp + 16]
                mov     ebx, edi                ; keep the return value

                and     eax, 0xFF
                cmp     ecx, 8
                jb      .bytes

                ; splat the byte across a dword and align the destination
                mov     ah, al
                mov     edx, eax
                shl     eax, 16
                or      eax, edx

.align_loop:
                test    edi, 3
                jz      .dwords
                mov     [edi], al
                inc     edi
                dec     ecx
                jmp     .align_loop

.dwords:
                push    ecx
                shr     ecx, 2
                rep     stosd
                pop     ecx
                and     ecx, 3

.bytes:
                test    ecx, ecx
                jz      .done
                rep     stosb
.done:
                mov     eax, ebx
                pop     ebx
                pop     ecx
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; memcpy(dst, src, count) -> dst
; ---------------------------------------------------------------------
memcpy:
                push    ebp
                mov     ebp, esp
                push    edi
                push    esi
                push    ecx

                mov     edi, [ebp + 8]
                mov     esi, [ebp + 12]
                mov     ecx, [ebp + 16]
                mov     eax, edi

                cmp     ecx, 16
                jb      .bytes
                mov     edx, ecx
                shr     ecx, 2
                rep     movsd
                mov     ecx, edx
                and     ecx, 3
.bytes:
                test    ecx, ecx
                jz      .done
                rep     movsb
.done:
                pop     ecx
                pop     esi
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; memmove(dst, src, count) -> dst   (handles overlap)
; ---------------------------------------------------------------------
memmove:
                push    ebp
                mov     ebp, esp
                push    edi
                push    esi
                push    ecx

                mov     edi, [ebp + 8]
                mov     esi, [ebp + 12]
                mov     ecx, [ebp + 16]
                mov     eax, edi

                cmp     edi, esi
                je      .done
                jb      .forward

                ; dst > src: copy backwards to avoid clobbering the tail
                add     esi, ecx
                add     edi, ecx
                dec     esi
                dec     edi
                std
                rep     movsb
                cld
                jmp     .done
.forward:
                rep     movsb
.done:
                pop     ecx
                pop     esi
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; memcmp(a, b, count) -> <0 / 0 / >0
; ---------------------------------------------------------------------
memcmp:
                push    ebp
                mov     ebp, esp
                push    edi
                push    esi
                push    ecx

                mov     esi, [ebp + 8]
                mov     edi, [ebp + 12]
                mov     ecx, [ebp + 16]
                xor     eax, eax
                test    ecx, ecx
                jz      .done
                repe    cmpsb
                je      .done
                movzx   eax, byte [esi - 1]
                movzx   edx, byte [edi - 1]
                sub     eax, edx
.done:
                pop     ecx
                pop     esi
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strlen(s) -> length
; ---------------------------------------------------------------------
strlen:
                push    ebp
                mov     ebp, esp
                push    esi
                mov     esi, [ebp + 8]
                xor     eax, eax
                test    esi, esi
                jz      .done
.next:
                cmp     byte [esi + eax], 0
                je      .done
                inc     eax
                jmp     .next
.done:
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strcmp(a, b)
; ---------------------------------------------------------------------
strcmp:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                mov     esi, [ebp + 8]
                mov     edi, [ebp + 12]
.next:
                movzx   eax, byte [esi]
                movzx   edx, byte [edi]
                cmp     al, dl
                jne     .diff
                test    al, al
                jz      .equal
                inc     esi
                inc     edi
                jmp     .next
.diff:
                sub     eax, edx
                jmp     .done
.equal:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strncmp(a, b, n)
; ---------------------------------------------------------------------
strncmp:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                push    ecx
                mov     esi, [ebp + 8]
                mov     edi, [ebp + 12]
                mov     ecx, [ebp + 16]
.next:
                test    ecx, ecx
                jz      .equal
                movzx   eax, byte [esi]
                movzx   edx, byte [edi]
                cmp     al, dl
                jne     .diff
                test    al, al
                jz      .equal
                inc     esi
                inc     edi
                dec     ecx
                jmp     .next
.diff:
                sub     eax, edx
                jmp     .done
.equal:
                xor     eax, eax
.done:
                pop     ecx
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strcasecmp(a, b) — ASCII only
; ---------------------------------------------------------------------
strcasecmp:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                mov     esi, [ebp + 8]
                mov     edi, [ebp + 12]
.next:
                movzx   eax, byte [esi]
                movzx   edx, byte [edi]
                cmp     al, 'A'
                jb      .a_ok
                cmp     al, 'Z'
                ja      .a_ok
                add     al, 32
.a_ok:
                cmp     dl, 'A'
                jb      .b_ok
                cmp     dl, 'Z'
                ja      .b_ok
                add     dl, 32
.b_ok:
                cmp     al, dl
                jne     .diff
                test    al, al
                jz      .equal
                inc     esi
                inc     edi
                jmp     .next
.diff:
                sub     eax, edx
                jmp     .done
.equal:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strcpy(dst, src) -> dst
; ---------------------------------------------------------------------
strcpy:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                mov     edi, [ebp + 8]
                mov     esi, [ebp + 12]
                mov     eax, edi
.next:
                mov     dl, [esi]
                mov     [edi], dl
                inc     esi
                inc     edi
                test    dl, dl
                jnz     .next
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strncpy(dst, src, n) -> dst   (always NUL terminates)
; ---------------------------------------------------------------------
strncpy:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                push    ecx
                mov     edi, [ebp + 8]
                mov     esi, [ebp + 12]
                mov     ecx, [ebp + 16]
                mov     eax, edi
                test    ecx, ecx
                jz      .done
                dec     ecx                     ; leave room for the NUL
.next:
                test    ecx, ecx
                jz      .terminate
                mov     dl, [esi]
                mov     [edi], dl
                test    dl, dl
                jz      .done
                inc     esi
                inc     edi
                dec     ecx
                jmp     .next
.terminate:
                mov     byte [edi], 0
.done:
                pop     ecx
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strchr(s, c) -> pointer or NULL
; ---------------------------------------------------------------------
strchr:
                push    ebp
                mov     ebp, esp
                push    esi
                mov     esi, [ebp + 8]
                mov     edx, [ebp + 12]
.next:
                mov     al, [esi]
                cmp     al, dl
                je      .found
                test    al, al
                jz      .missing
                inc     esi
                jmp     .next
.found:
                mov     eax, esi
                jmp     .done
.missing:
                xor     eax, eax
.done:
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strtok_r(str, delims, saveptr) -> token or NULL
; ---------------------------------------------------------------------
strtok_r:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                push    ebx

                mov     esi, [ebp + 8]
                test    esi, esi
                jnz     .have_str
                mov     ebx, [ebp + 16]
                mov     esi, [ebx]
                test    esi, esi
                jz      .none
.have_str:
                ; skip leading delimiters
.skip:
                movzx   eax, byte [esi]
                test    al, al
                jz      .none
                mov     edi, [ebp + 12]
                call    .in_set
                test    eax, eax
                jz      .token_start
                inc     esi
                jmp     .skip

.token_start:
                mov     edx, esi                ; remember the beginning
.scan:
                movzx   eax, byte [esi]
                test    al, al
                jz      .last_token
                mov     edi, [ebp + 12]
                call    .in_set
                test    eax, eax
                jnz     .cut
                inc     esi
                jmp     .scan

.cut:
                mov     byte [esi], 0
                inc     esi
                mov     ebx, [ebp + 16]
                mov     [ebx], esi
                mov     eax, edx
                jmp     .done

.last_token:
                mov     ebx, [ebp + 16]
                mov     [ebx], esi              ; points at the NUL
                mov     eax, edx
                jmp     .done

.none:
                mov     ebx, [ebp + 16]
                mov     dword [ebx], 0
                xor     eax, eax
.done:
                pop     ebx
                pop     edi
                pop     esi
                pop     ebp
                ret

; helper: AL = char, EDI = delimiter set -> EAX = 1 when present
.in_set:
                push    ecx
                mov     cl, al
.loop:
                mov     ch, [edi]
                test    ch, ch
                jz      .absent
                cmp     ch, cl
                je      .present
                inc     edi
                jmp     .loop
.present:
                mov     eax, 1
                pop     ecx
                ret
.absent:
                xor     eax, eax
                pop     ecx
                ret

; ---------------------------------------------------------------------
; utoa(value, buf, base) -> buf
; ---------------------------------------------------------------------
utoa:
                push    ebp
                mov     ebp, esp
                push    edi
                push    esi
                push    ebx

                mov     eax, [ebp + 8]
                mov     edi, [ebp + 12]
                mov     ebx, [ebp + 16]
                cmp     ebx, 2
                jb      .bad_base
                cmp     ebx, 16
                ja      .bad_base

                mov     esi, edi                ; save for reversing
                test    eax, eax
                jnz     .convert
                mov     byte [edi], '0'
                mov     byte [edi + 1], 0
                mov     eax, esi
                jmp     .done

.convert:
                xor     ecx, ecx                ; digit count
.digit_loop:
                xor     edx, edx
                div     ebx
                mov     dl, [digits + edx]
                mov     [edi], dl
                inc     edi
                inc     ecx
                test    eax, eax
                jnz     .digit_loop
                mov     byte [edi], 0

                ; reverse the digits in place
                dec     edi                     ; last digit
                mov     eax, esi                ; first digit
.reverse:
                cmp     eax, edi
                jae     .reversed
                mov     dl, [eax]
                mov     dh, [edi]
                mov     [eax], dh
                mov     [edi], dl
                inc     eax
                dec     edi
                jmp     .reverse
.reversed:
                mov     eax, esi
                jmp     .done

.bad_base:
                mov     byte [edi], 0
                mov     eax, edi
.done:
                pop     ebx
                pop     esi
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; itoa(value, buf, base) -> buf   (signed for base 10)
; ---------------------------------------------------------------------
itoa:
                push    ebp
                mov     ebp, esp
                push    edi

                mov     eax, [ebp + 8]
                mov     edi, [ebp + 12]
                mov     edx, [ebp + 16]
                cmp     edx, 10
                jne     .unsigned
                test    eax, eax
                jns     .unsigned

                mov     byte [edi], '-'
                inc     edi
                neg     eax
                push    dword [ebp + 16]
                push    edi
                push    eax
                call    utoa
                add     esp, 12
                mov     eax, [ebp + 12]
                jmp     .done

.unsigned:
                push    dword [ebp + 16]
                push    edi
                push    eax
                call    utoa
                add     esp, 12
                mov     eax, [ebp + 12]
.done:
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; atoi(str) -> value   (decimal, or 0x-prefixed hex)
; ---------------------------------------------------------------------
atoi:
                push    ebp
                mov     ebp, esp
                push    esi
                push    ebx

                mov     esi, [ebp + 8]
                xor     eax, eax
                xor     ecx, ecx                ; sign flag
                mov     ebx, 10

                test    esi, esi
                jz      .done
.skip_space:
                movzx   edx, byte [esi]
                cmp     dl, ' '
                je      .advance
                cmp     dl, 9
                je      .advance
                jmp     .check_sign
.advance:
                inc     esi
                jmp     .skip_space

.check_sign:
                cmp     dl, '-'
                jne     .check_plus
                mov     ecx, 1
                inc     esi
                jmp     .check_hex
.check_plus:
                cmp     dl, '+'
                jne     .check_hex
                inc     esi

.check_hex:
                cmp     byte [esi], '0'
                jne     .loop
                mov     dl, [esi + 1]
                cmp     dl, 'x'
                je      .hex
                cmp     dl, 'X'
                jne     .loop
.hex:
                mov     ebx, 16
                add     esi, 2

.loop:
                movzx   edx, byte [esi]
                test    dl, dl
                jz      .finish

                cmp     dl, '0'
                jb      .finish
                cmp     dl, '9'
                ja      .maybe_alpha
                sub     dl, '0'
                jmp     .accumulate
.maybe_alpha:
                cmp     ebx, 16
                jne     .finish
                or      dl, 0x20                ; lower case
                cmp     dl, 'a'
                jb      .finish
                cmp     dl, 'f'
                ja      .finish
                sub     dl, 'a' - 10
.accumulate:
                cmp     edx, ebx
                jae     .finish
                push    edx
                mul     ebx
                pop     edx
                add     eax, edx
                inc     esi
                jmp     .loop

.finish:
                test    ecx, ecx
                jz      .done
                neg     eax
.done:
                pop     ebx
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; strtrim(str) -> pointer to the first non-space, trailing spaces cut
; ---------------------------------------------------------------------
strtrim:
                push    ebp
                mov     ebp, esp
                push    esi
                push    edi
                mov     esi, [ebp + 8]
                test    esi, esi
                jz      .null
.lead:
                movzx   eax, byte [esi]
                cmp     al, ' '
                je      .lead_next
                cmp     al, 9
                je      .lead_next
                jmp     .find_end
.lead_next:
                inc     esi
                jmp     .lead

.find_end:
                mov     edi, esi
.scan:
                cmp     byte [edi], 0
                je      .trail
                inc     edi
                jmp     .scan
.trail:
                cmp     edi, esi
                jbe     .done
                movzx   eax, byte [edi - 1]
                cmp     al, ' '
                je      .cut
                cmp     al, 9
                je      .cut
                jmp     .done
.cut:
                dec     edi
                mov     byte [edi], 0
                jmp     .trail
.done:
                mov     eax, esi
                jmp     .out
.null:
                xor     eax, eax
.out:
                pop     edi
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------- ctype
toupper:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                cmp     al, 'a'
                jb      .done
                cmp     al, 'z'
                ja      .done
                sub     al, 32
.done:
                pop     ebp
                ret

tolower:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                cmp     al, 'A'
                jb      .done
                cmp     al, 'Z'
                ja      .done
                add     al, 32
.done:
                pop     ebp
                ret

isspace:
                push    ebp
                mov     ebp, esp
                mov     edx, [ebp + 8]
                xor     eax, eax
                cmp     dl, ' '
                je      .yes
                cmp     dl, 9
                jb      .done
                cmp     dl, 13
                ja      .done
.yes:
                mov     eax, 1
.done:
                pop     ebp
                ret

isdigit:
                push    ebp
                mov     ebp, esp
                mov     edx, [ebp + 8]
                xor     eax, eax
                cmp     dl, '0'
                jb      .done
                cmp     dl, '9'
                ja      .done
                mov     eax, 1
.done:
                pop     ebp
                ret

isalpha:
                push    ebp
                mov     ebp, esp
                mov     edx, [ebp + 8]
                xor     eax, eax
                or      dl, 0x20
                cmp     dl, 'a'
                jb      .done
                cmp     dl, 'z'
                ja      .done
                mov     eax, 1
.done:
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
digits:         db      "0123456789abcdef"
