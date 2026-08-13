; =====================================================================
;  Jino-OS  ::  fb.asm — the linear framebuffer console
; ---------------------------------------------------------------------
;  stage2 asks VBE for 1024x768x32 and leaves the geometry in the boot
;  information block.  If it managed it, everything the kernel prints is
;  drawn here as glyphs instead of being poked into text memory.
;
;  The framebuffer is wherever the card put it, which is well above the
;  16 MiB the kernel identity maps, so it has to be mapped in before the
;  first pixel is written.
;
;  Text is composed against a character grid the same way the VGA
;  console works, so the two are interchangeable from the caller's side
;  and vga.asm can hand over to this without anyone else noticing.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  fb_init
                global  fb_available
                global  fb_clear
                global  fb_putc_at
                global  fb_fill_row
                global  fb_scroll
                global  fb_cols
                global  fb_rows
                global  fb_width
                global  fb_height
                global  fb_draw_cursor
                global  fb_present
                global  fb_fill_rect
                global  fb_draw_glyph
                global  fb_draw_desktop

                extern  paging_map
                extern  pmm_mark_used
                extern  font_glyphs

; A 32-bit pixel as the card wants it: 8 bits per channel, blue lowest.
%define RGB(r, g, b) (((r) << 16) | ((g) << 8) | (b))

FG_COLOUR       equ     RGB(0xC8, 0xCC, 0xD0)
BG_COLOUR       equ     RGB(0x0C, 0x10, 0x18)
DESKTOP_COLOUR  equ     RGB(0x1E, 0x3A, 0x5F)
FRAME_COLOUR    equ     RGB(0x50, 0x60, 0x78)
TITLE_COLOUR    equ     RGB(0x2C, 0x50, 0x84)
TITLE_TEXT_COLOUR equ   RGB(0xE8, 0xEC, 0xF0)

GLYPH_W         equ     8
GLYPH_H         equ     16
FONT_FIRST      equ     32
FONT_LAST       equ     126

; The console keeps the 80x25 shape the text console has, so the two
; stay interchangeable and everything that prints carries on working.
; The rest of the screen becomes the desktop it sits on.
CON_COLS        equ     80
CON_ROWS        equ     25
CON_W           equ     CON_COLS * GLYPH_W
CON_H           equ     CON_ROWS * GLYPH_H
BORDER          equ     2
TITLE_H         equ     20

                section .text

; ---------------------------------------------------------------------
; fb_init -> EAX = 1 when a framebuffer is up, 0 to stay on text mode
;
;   Reads the geometry stage2 negotiated, maps the framebuffer into the
;   address space and clears it.
; ---------------------------------------------------------------------
fb_init:
                ENTER
                push    ebx
                push    esi
                push    edi

                mov     eax, [BOOTINFO_ADDR + BI_FB_ADDR]
                test    eax, eax
                jz      .no_framebuffer

                ; Only the one layout is handled; anything else is
                ; better served by the text console than by drawing
                ; garbage.
                cmp     dword [BOOTINFO_ADDR + BI_FB_BPP], 32
                jne     .no_framebuffer

                mov     [fb_base], eax
                mov     eax, [BOOTINFO_ADDR + BI_FB_PITCH]
                mov     [fb_pitch], eax
                mov     eax, [BOOTINFO_ADDR + BI_FB_WIDTH]
                mov     [fb_width_px], eax
                mov     eax, [BOOTINFO_ADDR + BI_FB_HEIGHT]
                mov     [fb_height_px], eax

                ; The console is a fixed 80x25 window centred on the
                ; desktop rather than the whole surface.
                mov     dword [fb_cols_n], CON_COLS
                mov     dword [fb_rows_n], CON_ROWS

                mov     eax, [fb_width_px]
                sub     eax, CON_W
                shr     eax, 1
                mov     [con_x], eax

                mov     eax, [fb_height_px]
                sub     eax, CON_H
                shr     eax, 1
                mov     [con_y], eax

                ; ---- map it ------------------------------------------
                ; height * pitch, rounded up to whole pages.
                mov     eax, [fb_height_px]
                mul     dword [fb_pitch]
                add     eax, PAGE_SIZE - 1
                and     eax, ~(PAGE_SIZE - 1)
                mov     [fb_bytes], eax
                shr     eax, PAGE_SHIFT
                mov     ecx, eax                ; ecx = pages to map

                mov     esi, [fb_base]          ; physical == virtual
                xor     edi, edi                ; pages done
.map_next:
                cmp     edi, ecx
                jae     .mapped

                mov     eax, edi
                shl     eax, PAGE_SHIFT
                add     eax, esi                ; this page's address

                push    ecx
                push    edi
                push    eax                     ; keep the address

                push    dword PAGE_PRESENT | PAGE_WRITE
                push    eax                     ; physical
                push    eax                     ; virtual, identity
                call    paging_map
                add     esp, 12

                pop     edx                     ; the address again
                test    eax, eax
                jz      .map_failed_pop

                ; Take the frame out of the allocator's hands.  The card
                ; owns this memory: handing it out as a general purpose
                ; page would put someone else's data on the screen.
                shr     edx, PAGE_SHIFT
                push    edx
                call    pmm_mark_used
                add     esp, 4

                pop     edi
                pop     ecx

                inc     edi
                jmp     .map_next

.mapped:
                mov     dword [fb_ready], 1
                call    fb_clear
                call    fb_draw_desktop

                mov     eax, 1
                jmp     .done

.map_failed_pop:
                pop     edi
                pop     ecx
.map_failed:
                ; Leave fb_ready clear; the caller falls back to text.
                mov     dword [fb_base], 0
.no_framebuffer:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fb_available -> EAX = 1 when the framebuffer console is usable
; ---------------------------------------------------------------------
fb_available:
                mov     eax, [fb_ready]
                ret

fb_cols:
                mov     eax, [fb_cols_n]
                ret

fb_rows:
                mov     eax, [fb_rows_n]
                ret

fb_width:
                mov     eax, [fb_width_px]
                ret

fb_height:
                mov     eax, [fb_height_px]
                ret

; ---------------------------------------------------------------------
; fb_clear — paint the whole surface in the background colour.
; ---------------------------------------------------------------------
fb_clear:
                push    edi
                push    ecx
                push    eax

                cmp     dword [fb_ready], 0
                je      .done

                mov     edi, [fb_base]
                mov     ecx, [fb_bytes]
                shr     ecx, 2
                mov     eax, BG_COLOUR
                rep     stosd
.done:
                pop     eax
                pop     ecx
                pop     edi
                ret

; ---------------------------------------------------------------------
; row_address(row) -> EAX = address of the first pixel of that text row
; ---------------------------------------------------------------------
row_address:
                push    ebp
                mov     ebp, esp
                push    edx
                mov     eax, [ebp + 8]
                mov     edx, GLYPH_H
                mul     edx
                add     eax, [con_y]
                mul     dword [fb_pitch]
                add     eax, [fb_base]
                mov     edx, [con_x]
                shl     edx, 2
                add     eax, edx
                pop     edx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; fb_putc_at(char, row, col, attr) — draw one glyph on the grid.
;
;   The attribute is a VGA one so callers do not have to care which
;   console they are talking to; it is turned into pixels here.
; ---------------------------------------------------------------------
fb_putc_at:
                ENTER
                push    ebx
                push    esi
                push    edi

                cmp     dword [fb_ready], 0
                je      .done

                mov     eax, [ebp + 12]         ; row
                cmp     eax, [fb_rows_n]
                jae     .done
                mov     eax, [ebp + 16]         ; col
                cmp     eax, [fb_cols_n]
                jae     .done

                ; ---- where the glyph data starts ---------------------
                mov     eax, [ebp + 8]
                and     eax, 0xFF
                cmp     eax, FONT_FIRST
                jb      .blank
                cmp     eax, FONT_LAST
                ja      .blank
                sub     eax, FONT_FIRST
                mov     edx, GLYPH_H
                mul     edx
                add     eax, font_glyphs
                mov     esi, eax
                jmp     .have_glyph
.blank:
                mov     esi, blank_glyph
.have_glyph:

                ; ---- colours from the attribute ----------------------
                mov     eax, [ebp + 20]
                mov     ebx, eax
                and     eax, 0x0F
                mov     eax, [palette + eax * 4]
                mov     [this_fg], eax
                shr     ebx, 4
                and     ebx, 0x07
                mov     eax, [palette + ebx * 4]
                mov     [this_bg], eax

                ; ---- top-left pixel of the cell ----------------------
                push    dword [ebp + 12]
                call    row_address
                add     esp, 4
                mov     edi, eax
                mov     eax, [ebp + 16]
                shl     eax, 2                  ; 4 bytes per pixel
                mov     edx, GLYPH_W
                mul     edx
                add     edi, eax

                ; ---- one scanline at a time --------------------------
                xor     ecx, ecx                ; scanline
.next_line:
                cmp     ecx, GLYPH_H
                jae     .done

                movzx   ebx, byte [esi + ecx]   ; this line's bit pattern

                ; The glyph is exactly eight pixels wide, so the inner
                ; loop is written out in full: no counter, no compare,
                ; and the store offsets are constants.  This is the
                ; hottest code in the console by a wide margin.
%assign pixel 0
%rep GLYPH_W
                mov     eax, [this_bg]
                test    bl, 0x80
                cmovnz  eax, [this_fg]
                mov     [edi + pixel * 4], eax
                shl     ebx, 1
%assign pixel pixel + 1
%endrep

                add     edi, [fb_pitch]
                inc     ecx
                jmp     .next_line

.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fb_fill_row(row, char, attr) — used for the status bar.
; ---------------------------------------------------------------------
fb_fill_row:
                ENTER
                push    ebx
                push    esi

                cmp     dword [fb_ready], 0
                je      .done

                xor     esi, esi
.next:
                cmp     esi, [fb_cols_n]
                jae     .done

                push    dword [ebp + 16]        ; attr
                push    esi                     ; col
                push    dword [ebp + 8]         ; row
                push    dword [ebp + 12]        ; char
                call    fb_putc_at
                add     esp, 16

                inc     esi
                jmp     .next
.done:
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fb_scroll — shift the picture up one text row.
;
;   A straight copy of everything below the first row, then the last row
;   painted out.  At 1024x768 that is three megabytes a line, which is
;   slow on real hardware but perfectly honest.
; ---------------------------------------------------------------------
fb_scroll:
                push    esi
                push    edi
                push    ecx
                push    eax
                push    edx
                push    ebx

                cmp     dword [fb_ready], 0
                je      .done

                ; The console is a window on the desktop, so this walks
                ; it a scanline at a time rather than moving one big
                ; block: the pixels either side must not move.
                xor     ebx, ebx                ; destination scanline
                mov     edx, CON_H - GLYPH_H
.next_line:
                cmp     ebx, edx
                jae     .blank_last

                mov     eax, ebx
                call    scanline_address
                mov     edi, eax

                mov     eax, ebx
                add     eax, GLYPH_H
                call    scanline_address
                mov     esi, eax

                mov     ecx, CON_W
                rep     movsd

                inc     ebx
                jmp     .next_line

.blank_last:
                ; paint out the row that just came free
                mov     edx, CON_H
.next_blank:
                cmp     ebx, edx
                jae     .done

                mov     eax, ebx
                call    scanline_address
                mov     edi, eax
                mov     ecx, CON_W
                mov     eax, BG_COLOUR
                rep     stosd

                inc     ebx
                jmp     .next_blank
.done:
                pop     ebx
                pop     edx
                pop     eax
                pop     ecx
                pop     edi
                pop     esi
                ret

; ---------------------------------------------------------------------
; fb_fill_rect(x, y, w, h, colour) — the one primitive the chrome needs.
; ---------------------------------------------------------------------
fb_fill_rect:
                ENTER
                push    ebx
                push    esi
                push    edi

                cmp     dword [fb_ready], 0
                je      .done

                mov     ebx, [ebp + 12]         ; y
                mov     esi, [ebp + 20]         ; rows left
.next_row:
                test    esi, esi
                jz      .done
                cmp     ebx, [fb_height_px]
                jae     .done

                mov     eax, ebx
                mul     dword [fb_pitch]
                add     eax, [fb_base]
                mov     edi, eax
                mov     eax, [ebp + 8]          ; x
                shl     eax, 2
                add     edi, eax

                mov     ecx, [ebp + 16]         ; width
                mov     eax, [ebp + 24]         ; colour
                rep     stosd

                inc     ebx
                dec     esi
                jmp     .next_row
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fb_draw_desktop — the backdrop and the frame around the console.
;
;   Drawn once at start up.  The console window is deliberately the same
;   80x25 the text console is, so the picture is a window onto exactly
;   what the other console would have shown.
; ---------------------------------------------------------------------
fb_draw_desktop:
                ENTER
                push    ebx
                push    esi

                cmp     dword [fb_ready], 0
                je      .done

                ; ---- backdrop ---------------------------------------
                push    dword DESKTOP_COLOUR
                push    dword [fb_height_px]
                push    dword [fb_width_px]
                push    dword 0
                push    dword 0
                call    fb_fill_rect
                add     esp, 20

                ; ---- title bar above the console --------------------
                mov     eax, [con_y]
                sub     eax, TITLE_H + BORDER
                mov     ebx, eax                ; ebx = title bar y

                push    dword TITLE_COLOUR
                push    dword TITLE_H
                push    dword CON_W + BORDER * 2
                push    ebx
                mov     eax, [con_x]
                sub     eax, BORDER
                push    eax
                call    fb_fill_rect
                add     esp, 20

                ; ---- the frame itself -------------------------------
                ; top edge
                push    dword FRAME_COLOUR
                push    dword BORDER
                push    dword CON_W + BORDER * 2
                mov     eax, [con_y]
                sub     eax, BORDER
                push    eax
                mov     eax, [con_x]
                sub     eax, BORDER
                push    eax
                call    fb_fill_rect
                add     esp, 20

                ; bottom edge
                push    dword FRAME_COLOUR
                push    dword BORDER
                push    dword CON_W + BORDER * 2
                mov     eax, [con_y]
                add     eax, CON_H
                push    eax
                mov     eax, [con_x]
                sub     eax, BORDER
                push    eax
                call    fb_fill_rect
                add     esp, 20

                ; left edge
                push    dword FRAME_COLOUR
                push    dword CON_H
                push    dword BORDER
                push    dword [con_y]
                mov     eax, [con_x]
                sub     eax, BORDER
                push    eax
                call    fb_fill_rect
                add     esp, 20

                ; right edge
                push    dword FRAME_COLOUR
                push    dword CON_H
                push    dword BORDER
                push    dword [con_y]
                mov     eax, [con_x]
                add     eax, CON_W
                push    eax
                call    fb_fill_rect
                add     esp, 20

                ; ---- the console's own background -------------------
                push    dword BG_COLOUR
                push    dword CON_H
                push    dword CON_W
                push    dword [con_y]
                push    dword [con_x]
                call    fb_fill_rect
                add     esp, 20

                ; ---- the title ---------------------------------------
                ; Drawn straight into the bar, so it is not part of the
                ; character grid the console scrolls.
                mov     esi, title_text
                xor     ebx, ebx
.next_title:
                movzx   eax, byte [esi + ebx]
                test    eax, eax
                jz      .done

                push    ebx
                push    esi

                mov     ecx, ebx
                shl     ecx, 3                  ; * GLYPH_W
                add     ecx, [con_x]
                add     ecx, 6                  ; a little inset

                mov     edx, [con_y]
                sub     edx, TITLE_H + BORDER
                add     edx, 2

                push    dword TITLE_COLOUR
                push    dword TITLE_TEXT_COLOUR
                push    edx
                push    ecx
                push    eax
                call    fb_draw_glyph
                add     esp, 20

                pop     esi
                pop     ebx
                inc     ebx
                jmp     .next_title
.done:
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fb_draw_glyph(char, x, y, fg, bg) — one glyph at a pixel position.
;
;   The console draws on its character grid; this is for the chrome,
;   which is not on any grid.
; ---------------------------------------------------------------------
fb_draw_glyph:
                ENTER
                push    ebx
                push    esi
                push    edi

                cmp     dword [fb_ready], 0
                je      .done

                mov     eax, [ebp + 8]
                and     eax, 0xFF
                cmp     eax, FONT_FIRST
                jb      .done
                cmp     eax, FONT_LAST
                ja      .done
                sub     eax, FONT_FIRST
                mov     edx, GLYPH_H
                mul     edx
                add     eax, font_glyphs
                mov     esi, eax

                xor     ecx, ecx
.next_line:
                cmp     ecx, GLYPH_H
                jae     .done

                mov     eax, [ebp + 16]         ; y
                add     eax, ecx
                cmp     eax, [fb_height_px]
                jae     .done
                mul     dword [fb_pitch]
                add     eax, [fb_base]
                mov     edi, eax
                mov     eax, [ebp + 12]         ; x
                shl     eax, 2
                add     edi, eax

                movzx   ebx, byte [esi + ecx]
                push    ecx
                xor     edx, edx
.next_pixel:
                cmp     edx, GLYPH_W
                jae     .line_done
                test    bl, 0x80
                mov     eax, [ebp + 24]         ; bg
                jz      .plot
                mov     eax, [ebp + 20]         ; fg
.plot:
                mov     [edi], eax
                add     edi, 4
                shl     ebx, 1
                inc     edx
                jmp     .next_pixel
.line_done:
                pop     ecx
                inc     ecx
                jmp     .next_line
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; scanline_address(EAX = scanline within the console) -> EAX = address
; ---------------------------------------------------------------------
scanline_address:
                push    edx
                add     eax, [con_y]
                mul     dword [fb_pitch]
                add     eax, [fb_base]
                mov     edx, [con_x]
                shl     edx, 2
                add     eax, edx
                pop     edx
                ret

; ---------------------------------------------------------------------
; fb_draw_cursor(row, col, on) — a caret under the character cell.
; ---------------------------------------------------------------------
fb_draw_cursor:
                ENTER
                push    ebx
                push    edi

                cmp     dword [fb_ready], 0
                je      .done

                mov     eax, [ebp + 8]
                cmp     eax, [fb_rows_n]
                jae     .done
                mov     eax, [ebp + 12]
                cmp     eax, [fb_cols_n]
                jae     .done

                push    dword [ebp + 8]
                call    row_address
                add     esp, 4
                mov     edi, eax

                ; drop to the last two scanlines of the cell
                mov     eax, GLYPH_H - 2
                mul     dword [fb_pitch]
                add     edi, eax

                mov     eax, [ebp + 12]
                shl     eax, 2
                mov     edx, GLYPH_W
                mul     edx
                add     edi, eax

                mov     eax, BG_COLOUR
                cmp     dword [ebp + 16], 0
                je      .have_colour
                mov     eax, FG_COLOUR
.have_colour:
                mov     ebx, eax

                mov     ecx, 2                  ; two scanlines
.next_line:
                push    edi
                push    ecx
                mov     ecx, GLYPH_W
                mov     eax, ebx
                rep     stosd
                pop     ecx
                pop     edi
                add     edi, [fb_pitch]
                loop    .next_line
.done:
                pop     edi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fb_present — where a double buffer would be flushed.
;
;   Drawing goes straight to the card, so there is nothing to do; the
;   call exists so the console code reads the same either way.
; ---------------------------------------------------------------------
fb_present:
                ret

; ---------------------------------------------------------------------
                section .rodata
                align   4

; The sixteen VGA colours, as the framebuffer wants them.
palette:
                dd      RGB(0x0C, 0x10, 0x18)   ; black
                dd      RGB(0x20, 0x40, 0xA0)   ; blue
                dd      RGB(0x30, 0x90, 0x40)   ; green
                dd      RGB(0x20, 0x90, 0x98)   ; cyan
                dd      RGB(0xA8, 0x30, 0x38)   ; red
                dd      RGB(0x90, 0x38, 0x98)   ; magenta
                dd      RGB(0x98, 0x70, 0x28)   ; brown
                dd      RGB(0xC8, 0xCC, 0xD0)   ; light grey
                dd      RGB(0x58, 0x60, 0x68)   ; dark grey
                dd      RGB(0x60, 0x90, 0xF0)   ; light blue
                dd      RGB(0x70, 0xD0, 0x80)   ; light green
                dd      RGB(0x70, 0xD8, 0xE0)   ; light cyan
                dd      RGB(0xF0, 0x70, 0x78)   ; light red
                dd      RGB(0xE0, 0x80, 0xE0)   ; light magenta
                dd      RGB(0xF0, 0xD8, 0x60)   ; yellow
                dd      RGB(0xFF, 0xFF, 0xFF)   ; white

blank_glyph:
                times GLYPH_H db 0

title_text:     db      "Jino-OS console", 0

; ---------------------------------------------------------------------
                section .bss
                alignb  4
fb_base:        resd    1
fb_pitch:       resd    1
fb_width_px:    resd    1
fb_height_px:   resd    1
fb_bytes:       resd    1
fb_cols_n:      resd    1
fb_rows_n:      resd    1
fb_ready:       resd    1
this_fg:        resd    1
this_bg:        resd    1
con_x:          resd    1
con_y:          resd    1
