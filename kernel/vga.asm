; =====================================================================
;  Jino-OS  ::  vga.asm — 80x25 text mode console
; ---------------------------------------------------------------------
;  A scrolling terminal on top of the VGA text buffer with a hardware
;  cursor, colour attributes and the usual control characters.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  vga_init
                global  vga_clear
                global  vga_putc
                global  vga_puts
                global  vga_write
                global  vga_set_color
                global  vga_get_color
                global  vga_set_cursor
                global  vga_get_cursor
                global  vga_scroll
                global  vga_fill_row
                global  vga_hide_cursor
                global  vga_show_cursor
                global  vga_putc_at
                global  vga_use_framebuffer

                extern  fb_init
                extern  fb_putc_at
                extern  fb_scroll
                extern  fb_draw_cursor

                section .text

; ---------------------------------------------------------------------
; vga_use_framebuffer -> EAX = 1 when the console moved to the graphics
;                        display, 0 when it stayed in text mode.
;
;   Everything that has been printed so far is still sitting in the text
;   buffer, so once the framebuffer is up the buffer is replayed onto it
;   and the boot log appears in the window rather than being lost.
; ---------------------------------------------------------------------
vga_use_framebuffer:
                ENTER
                push    ebx
                push    esi
                push    edi

                call    fb_init
                test    eax, eax
                jz      .stay_in_text

                mov     dword [vga_graphics], 1

                ; ---- replay the text buffer -------------------------
                xor     ebx, ebx                ; row
.next_row:
                cmp     ebx, VGA_HEIGHT
                jae     .replayed
                xor     esi, esi                ; column
.next_col:
                cmp     esi, VGA_WIDTH
                jae     .row_done

                mov     eax, ebx
                mov     edx, VGA_WIDTH
                mul     edx
                add     eax, esi
                shl     eax, 1
                mov     dx, [VGA_MEMORY + eax]  ; character and attribute

                movzx   ecx, dh
                push    ecx                     ; attr
                push    esi                     ; col
                push    ebx                     ; row
                movzx   ecx, dl
                push    ecx                     ; char
                call    fb_putc_at
                add     esp, 16

                inc     esi
                jmp     .next_col
.row_done:
                inc     ebx
                jmp     .next_row

.replayed:
                call    update_hw_cursor
                mov     eax, 1
                jmp     .done

.stay_in_text:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; vga_init — clear the screen and park the cursor at the top left.
; ---------------------------------------------------------------------
vga_init:
                mov     byte [vga_color], VGA_ATTR(COLOR_LGREY, COLOR_BLACK)
                mov     dword [vga_row], 0
                mov     dword [vga_col], 0
                call    vga_clear
                call    vga_show_cursor
                ret

; ---------------------------------------------------------------------
; vga_clear — fill the whole buffer with spaces in the current colour.
; ---------------------------------------------------------------------
vga_clear:
                push    edi
                push    eax
                push    ecx
                mov     edi, VGA_MEMORY
                mov     ecx, VGA_WIDTH * VGA_HEIGHT
                mov     ah, [vga_color]
                mov     al, ' '
                rep     stosw
                mov     dword [vga_row], 0
                mov     dword [vga_col], 0
                cmp     dword [vga_graphics], 0
                je      .no_fb
                call    repaint_from_text
.no_fb:
                call    update_hw_cursor
                pop     ecx
                pop     eax
                pop     edi
                ret

; ---------------------------------------------------------------------
; vga_set_color(attr)
; ---------------------------------------------------------------------
vga_set_color:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                mov     [vga_color], al
                pop     ebp
                ret

; ---------------------------------------------------------------------
; vga_get_color -> EAX
; ---------------------------------------------------------------------
vga_get_color:
                movzx   eax, byte [vga_color]
                ret

; ---------------------------------------------------------------------
; vga_set_cursor(row, col)
; ---------------------------------------------------------------------
vga_set_cursor:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                cmp     eax, VGA_HEIGHT
                jb      .row_ok
                mov     eax, VGA_HEIGHT - 1
.row_ok:
                mov     [vga_row], eax
                mov     eax, [ebp + 12]
                cmp     eax, VGA_WIDTH
                jb      .col_ok
                mov     eax, VGA_WIDTH - 1
.col_ok:
                mov     [vga_col], eax
                call    update_hw_cursor
                pop     ebp
                ret

; ---------------------------------------------------------------------
; vga_get_cursor -> EAX = row, EDX = col
; ---------------------------------------------------------------------
vga_get_cursor:
                mov     eax, [vga_row]
                mov     edx, [vga_col]
                ret

; ---------------------------------------------------------------------
; vga_putc(char) — handles \n, \r, \t, \b and the printable range.
; ---------------------------------------------------------------------
vga_putc:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    edi

                mov     eax, [ebp + 8]
                and     eax, 0xFF

                cmp     al, 10                  ; \n
                je      .newline
                cmp     al, 13                  ; \r
                je      .carriage
                cmp     al, 9                   ; \t
                je      .tab
                cmp     al, 8                   ; \b
                je      .backspace
                cmp     al, 32
                jb      .done                   ; ignore other controls

                ; ---- ordinary character -----------------------------
                call    cursor_offset           ; -> EDI
                mov     ah, [vga_color]
                mov     [edi], ax
                call    mirror_cursor_cell
                inc     dword [vga_col]
                jmp     .wrap_check

.newline:
                mov     dword [vga_col], 0
                inc     dword [vga_row]
                jmp     .scroll_check

.carriage:
                mov     dword [vga_col], 0
                jmp     .update

.tab:
                mov     eax, [vga_col]
                add     eax, 8
                and     eax, ~7                 ; round up to a multiple of 8
                mov     [vga_col], eax
                jmp     .wrap_check

.backspace:
                mov     eax, [vga_col]
                test    eax, eax
                jnz     .back_same_row
                mov     eax, [vga_row]
                test    eax, eax
                jz      .done                   ; already at 0,0
                dec     dword [vga_row]
                mov     dword [vga_col], VGA_WIDTH - 1
                jmp     .back_erase
.back_same_row:
                dec     dword [vga_col]
.back_erase:
                call    cursor_offset
                mov     ah, [vga_color]
                mov     al, ' '
                mov     [edi], ax
                call    mirror_cursor_cell
                jmp     .update

.wrap_check:
                cmp     dword [vga_col], VGA_WIDTH
                jb      .update
                mov     dword [vga_col], 0
                inc     dword [vga_row]

.scroll_check:
                cmp     dword [vga_row], VGA_HEIGHT
                jb      .update
                call    vga_scroll
                mov     dword [vga_row], VGA_HEIGHT - 1

.update:
                call    update_hw_cursor
.done:
                pop     edi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; vga_putc_at(char, row, col) — draw without moving the cursor.
; ---------------------------------------------------------------------
vga_putc_at:
                push    ebp
                mov     ebp, esp
                push    edi
                mov     eax, [ebp + 12]         ; row
                mov     edx, VGA_WIDTH * 2
                mul     edx
                mov     edi, eax
                mov     eax, [ebp + 16]         ; col
                shl     eax, 1
                add     edi, eax
                add     edi, VGA_MEMORY
                mov     eax, [ebp + 8]
                mov     ah, [vga_color]
                mov     [edi], ax

                ; The text buffer stays the record of what is on screen
                ; even in graphics mode, so it is always written; the
                ; framebuffer is painted from it.
                cmp     dword [vga_graphics], 0
                je      .done
                movzx   eax, byte [vga_color]
                push    eax
                push    dword [ebp + 16]
                push    dword [ebp + 12]
                push    dword [ebp + 8]
                call    fb_putc_at
                add     esp, 16
.done:
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; vga_puts(char *) — NUL terminated string.
; ---------------------------------------------------------------------
vga_puts:
                push    ebp
                mov     ebp, esp
                push    esi
                mov     esi, [ebp + 8]
                test    esi, esi
                jz      .done
.next:
                mov     al, [esi]
                test    al, al
                jz      .done
                inc     esi
                movzx   eax, al
                push    eax
                call    vga_putc
                add     esp, 4
                jmp     .next
.done:
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; vga_write(buf, len) — explicit length, NULs are printed as-is.
; ---------------------------------------------------------------------
vga_write:
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
                call    vga_putc
                add     esp, 4
                jmp     .next
.done:
                pop     ebx
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; vga_scroll — move everything up one line, blank the bottom row.
; ---------------------------------------------------------------------
vga_scroll:
                push    esi
                push    edi
                push    ecx
                push    eax

                mov     edi, VGA_MEMORY
                mov     esi, VGA_MEMORY + VGA_WIDTH * 2
                mov     ecx, VGA_WIDTH * (VGA_HEIGHT - 1)
                rep     movsw

                mov     ecx, VGA_WIDTH
                mov     ah, [vga_color]
                mov     al, ' '
                rep     stosw

                cmp     dword [vga_graphics], 0
                je      .done
                call    fb_scroll

                ; The painted caret moved up with everything else, so
                ; the record of where it is has to move with it or the
                ; next erase will rub out the wrong cell.
                cmp     dword [caret_row], 0
                je      .done
                dec     dword [caret_row]
.done:
                pop     eax
                pop     ecx
                pop     edi
                pop     esi
                ret

; ---------------------------------------------------------------------
; vga_fill_row(row, char, attr)
; ---------------------------------------------------------------------
vga_fill_row:
                push    ebp
                mov     ebp, esp
                push    edi
                push    ecx
                mov     eax, [ebp + 8]
                mov     edx, VGA_WIDTH * 2
                mul     edx
                lea     edi, [VGA_MEMORY + eax]
                mov     eax, [ebp + 12]
                mov     edx, [ebp + 16]
                mov     ah, dl
                mov     ecx, VGA_WIDTH
                rep     stosw

                cmp     dword [vga_graphics], 0
                je      .done
                push    dword [ebp + 8]
                call    repaint_row
                add     esp, 4
.done:
                pop     ecx
                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; mirror_cursor_cell — paint the cell under the cursor onto the display.
; ---------------------------------------------------------------------
mirror_cursor_cell:
                cmp     dword [vga_graphics], 0
                je      .done
                pushad
                movzx   eax, byte [vga_color]
                push    eax
                push    dword [vga_col]
                push    dword [vga_row]
                call    cursor_offset
                movzx   eax, byte [edi]
                push    eax
                call    fb_putc_at
                add     esp, 16
                popad
.done:
                ret

; ---------------------------------------------------------------------
; repaint_cell(row, col) — redraw one character from the text buffer.
; ---------------------------------------------------------------------
repaint_cell:
                push    ebp
                mov     ebp, esp
                pushad

                mov     ebx, [ebp + 8]          ; row
                mov     esi, [ebp + 12]         ; col
                cmp     ebx, VGA_HEIGHT
                jae     .done
                cmp     esi, VGA_WIDTH
                jae     .done

                mov     eax, ebx
                mov     edx, VGA_WIDTH
                mul     edx
                add     eax, esi
                shl     eax, 1
                mov     dx, [VGA_MEMORY + eax]

                movzx   ecx, dh
                push    ecx                     ; attribute
                push    esi                     ; column
                push    ebx                     ; row
                movzx   ecx, dl
                push    ecx                     ; character
                call    fb_putc_at
                add     esp, 16
.done:
                popad
                pop     ebp
                ret

; ---------------------------------------------------------------------
; mirror_cursor_caret — move the drawn caret to the current position.
;
;   The hardware cursor is invisible in graphics mode, so the caret has
;   to be painted.  The cell it used to sit in is redrawn from the text
;   buffer, which erases the old one.
; ---------------------------------------------------------------------
mirror_cursor_caret:
                cmp     dword [vga_graphics], 0
                je      .done
                pushad

                push    dword [caret_col]
                push    dword [caret_row]
                call    repaint_cell
                add     esp, 8

                mov     eax, [vga_row]
                mov     [caret_row], eax
                mov     eax, [vga_col]
                mov     [caret_col], eax

                push    dword 1                 ; on
                push    dword [vga_col]
                push    dword [vga_row]
                call    fb_draw_cursor
                add     esp, 12

                popad
.done:
                ret

; ---------------------------------------------------------------------
; repaint_row(row) — redraw one text row onto the display.
; ---------------------------------------------------------------------
repaint_row:
                push    ebp
                mov     ebp, esp
                pushad

                mov     ebx, [ebp + 8]
                cmp     ebx, VGA_HEIGHT
                jae     .done
                xor     esi, esi
.next:
                cmp     esi, VGA_WIDTH
                jae     .done

                mov     eax, ebx
                mov     edx, VGA_WIDTH
                mul     edx
                add     eax, esi
                shl     eax, 1
                mov     dx, [VGA_MEMORY + eax]

                movzx   ecx, dh
                push    ecx
                push    esi
                push    ebx
                movzx   ecx, dl
                push    ecx
                call    fb_putc_at
                add     esp, 16

                inc     esi
                jmp     .next
.done:
                popad
                pop     ebp
                ret

; ---------------------------------------------------------------------
; repaint_from_text — redraw the whole console from the text buffer.
; ---------------------------------------------------------------------
repaint_from_text:
                pushad
                xor     ebx, ebx
.next_row:
                cmp     ebx, VGA_HEIGHT
                jae     .done
                push    ebx
                call    repaint_row
                add     esp, 4
                inc     ebx
                jmp     .next_row
.done:
                popad
                ret

; ---------------------------------------------------------------------
; cursor_offset -> EDI = VGA address of the current cursor cell
; ---------------------------------------------------------------------
cursor_offset:
                push    eax
                push    edx
                mov     eax, [vga_row]
                mov     edx, VGA_WIDTH
                mul     edx
                add     eax, [vga_col]
                shl     eax, 1
                lea     edi, [VGA_MEMORY + eax]
                pop     edx
                pop     eax
                ret

; ---------------------------------------------------------------------
; update_hw_cursor — program CRTC registers 0x0E / 0x0F.
; ---------------------------------------------------------------------
update_hw_cursor:
                push    eax
                push    ecx
                push    edx
                mov     eax, [vga_row]
                mov     edx, VGA_WIDTH
                mul     edx
                add     eax, [vga_col]
                mov     ecx, eax                ; ecx = linear position

                mov     dx, VGA_CRTC_INDEX
                mov     al, 0x0F
                out     dx, al
                mov     dx, VGA_CRTC_DATA
                mov     eax, ecx
                out     dx, al

                mov     dx, VGA_CRTC_INDEX
                mov     al, 0x0E
                out     dx, al
                mov     dx, VGA_CRTC_DATA
                mov     eax, ecx
                shr     eax, 8
                out     dx, al

                pop     edx
                pop     ecx
                pop     eax
                call    mirror_cursor_caret
                ret

; ---------------------------------------------------------------------
vga_hide_cursor:
                push    eax
                push    edx
                mov     dx, VGA_CRTC_INDEX
                mov     al, 0x0A
                out     dx, al
                mov     dx, VGA_CRTC_DATA
                mov     al, 0x20                ; bit 5 disables the cursor
                out     dx, al
                pop     edx
                pop     eax
                ret

vga_show_cursor:
                push    eax
                push    edx
                mov     dx, VGA_CRTC_INDEX
                mov     al, 0x0A
                out     dx, al
                mov     dx, VGA_CRTC_DATA
                mov     al, 13                  ; scanline start
                out     dx, al
                mov     dx, VGA_CRTC_INDEX
                mov     al, 0x0B
                out     dx, al
                mov     dx, VGA_CRTC_DATA
                mov     al, 15                  ; scanline end
                out     dx, al
                pop     edx
                pop     eax
                call    update_hw_cursor
                ret

; ---------------------------------------------------------------------
                section .data
vga_color:      db      VGA_ATTR(COLOR_LGREY, COLOR_BLACK)

                section .bss
                alignb  4
vga_row:        resd    1
vga_col:        resd    1

; Set once the framebuffer console has taken over.  Until then every
; drawing call is a plain text buffer write.
vga_graphics:   resd    1

; Where the painted caret currently sits, so it can be rubbed out
; again when it moves.
caret_row:      resd    1
caret_col:      resd    1
