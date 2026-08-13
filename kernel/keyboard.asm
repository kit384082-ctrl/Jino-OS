; =====================================================================
;  Jino-OS  ::  keyboard.asm — PS/2 keyboard driver
; ---------------------------------------------------------------------
;  Scan code set 1, with modifier tracking, extended (E0) prefixes and
;  a small circular buffer so readers never lose keystrokes.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  keyboard_init
                global  keyboard_handler
                global  keyboard_getchar
                global  keyboard_poll
                global  keyboard_available
                global  keyboard_readline
                global  keyboard_modifiers
                global  keyboard_last_scancode

                extern  idt_register_handler
                extern  pic_unmask_irq
                extern  vga_putc
                extern  serial_poll

BUFFER_SIZE     equ     256

; modifier bits reported by keyboard_modifiers
MOD_SHIFT       equ     1 << 0
MOD_CTRL        equ     1 << 1
MOD_ALT         equ     1 << 2
MOD_CAPS        equ     1 << 3
MOD_NUM         equ     1 << 4
MOD_SCROLL      equ     1 << 5

; keys we report above the ASCII range
KEY_UP          equ     0x100
KEY_DOWN        equ     0x101
KEY_LEFT        equ     0x102
KEY_RIGHT       equ     0x103
KEY_HOME        equ     0x104
KEY_END         equ     0x105
KEY_PGUP        equ     0x106
KEY_PGDN        equ     0x107
KEY_INSERT      equ     0x108
KEY_DELETE      equ     0x109
KEY_F1          equ     0x110

                section .text

; ---------------------------------------------------------------------
; keyboard_init
; ---------------------------------------------------------------------
keyboard_init:
                push    ebp
                mov     ebp, esp

                mov     dword [buf_head], 0
                mov     dword [buf_tail], 0
                mov     dword [keyboard_modifiers], 0
                mov     dword [extended], 0

                ; drain anything the BIOS left in the controller
                mov     ecx, 32
.drain:
                in      al, KBD_STATUS
                test    al, 1
                jz      .drained
                in      al, KBD_DATA
                dec     ecx
                jnz     .drain
.drained:

                push    dword keyboard_handler
                push    dword 33                ; vector for IRQ1
                call    idt_register_handler
                add     esp, 8

                push    dword 1
                call    pic_unmask_irq
                add     esp, 4

                pop     ebp
                ret

; ---------------------------------------------------------------------
; keyboard_handler(frame)
; ---------------------------------------------------------------------
keyboard_handler:
                push    ebp
                mov     ebp, esp
                pushad

                in      al, KBD_STATUS
                test    al, 1                   ; output buffer full?
                jz      .done

                in      al, KBD_DATA
                movzx   ebx, al
                mov     [keyboard_last_scancode], ebx

                cmp     al, 0xE0                ; extended prefix
                jne     .not_prefix
                mov     dword [extended], 1
                jmp     .done
.not_prefix:
                cmp     al, 0xE1                ; pause/break, ignore
                je      .clear_prefix

                test    al, 0x80                ; release?
                jnz     .key_release

; ---- key press ------------------------------------------------------
                cmp     dword [extended], 0
                jne     .extended_press

                ; modifiers
                cmp     bl, 0x2A                ; left shift
                je      .shift_down
                cmp     bl, 0x36                ; right shift
                je      .shift_down
                cmp     bl, 0x1D                ; left control
                je      .ctrl_down
                cmp     bl, 0x38                ; left alt
                je      .alt_down
                cmp     bl, 0x3A                ; caps lock
                je      .caps_toggle
                cmp     bl, 0x45                ; num lock
                je      .num_toggle
                cmp     bl, 0x46                ; scroll lock
                je      .scroll_toggle

                cmp     bl, 0x3B                ; F1..F10
                jb      .translate
                cmp     bl, 0x44
                ja      .translate
                movzx   eax, bl
                sub     eax, 0x3B
                add     eax, KEY_F1
                call    buffer_push
                jmp     .clear_prefix

.translate:
                cmp     bl, 0x58
                ja      .clear_prefix

                ; pick the layout table according to shift/caps
                mov     eax, [keyboard_modifiers]
                test    eax, MOD_SHIFT
                jnz     .shifted
                movzx   eax, byte [keymap_normal + ebx]
                jmp     .apply_caps
.shifted:
                movzx   eax, byte [keymap_shift + ebx]

.apply_caps:
                test    al, al
                jz      .clear_prefix

                ; caps lock only affects letters
                mov     edx, [keyboard_modifiers]
                test    edx, MOD_CAPS
                jz      .apply_ctrl
                cmp     al, 'a'
                jb      .apply_ctrl
                cmp     al, 'z'
                ja      .check_upper
                sub     al, 32
                jmp     .apply_ctrl
.check_upper:
                cmp     al, 'A'
                jb      .apply_ctrl
                cmp     al, 'Z'
                ja      .apply_ctrl
                add     al, 32

.apply_ctrl:
                test    edx, MOD_CTRL
                jz      .store
                ; control turns letters into 0x01..0x1A
                mov     ah, al
                or      ah, 0x20                ; lower case for the test
                cmp     ah, 'a'
                jb      .store
                cmp     ah, 'z'
                ja      .store
                and     al, 0x1F

.store:
                movzx   eax, al
                call    buffer_push
                jmp     .clear_prefix

.extended_press:
                movzx   eax, bl
                cmp     al, 0x48
                je      .k_up
                cmp     al, 0x50
                je      .k_down
                cmp     al, 0x4B
                je      .k_left
                cmp     al, 0x4D
                je      .k_right
                cmp     al, 0x47
                je      .k_home
                cmp     al, 0x4F
                je      .k_end
                cmp     al, 0x49
                je      .k_pgup
                cmp     al, 0x51
                je      .k_pgdn
                cmp     al, 0x52
                je      .k_insert
                cmp     al, 0x53
                je      .k_delete
                cmp     al, 0x1D                ; right control
                je      .ctrl_down
                cmp     al, 0x38                ; right alt
                je      .alt_down
                jmp     .clear_prefix

.k_up:          mov     eax, KEY_UP
                call    buffer_push
                jmp     .clear_prefix
.k_down:        mov     eax, KEY_DOWN
                call    buffer_push
                jmp     .clear_prefix
.k_left:        mov     eax, KEY_LEFT
                call    buffer_push
                jmp     .clear_prefix
.k_right:       mov     eax, KEY_RIGHT
                call    buffer_push
                jmp     .clear_prefix
.k_home:        mov     eax, KEY_HOME
                call    buffer_push
                jmp     .clear_prefix
.k_end:         mov     eax, KEY_END
                call    buffer_push
                jmp     .clear_prefix
.k_pgup:        mov     eax, KEY_PGUP
                call    buffer_push
                jmp     .clear_prefix
.k_pgdn:        mov     eax, KEY_PGDN
                call    buffer_push
                jmp     .clear_prefix
.k_insert:      mov     eax, KEY_INSERT
                call    buffer_push
                jmp     .clear_prefix
.k_delete:      mov     eax, KEY_DELETE
                call    buffer_push
                jmp     .clear_prefix

; ---- key release ----------------------------------------------------
.key_release:
                and     bl, 0x7F                ; strip the release bit
                cmp     bl, 0x2A
                je      .shift_up
                cmp     bl, 0x36
                je      .shift_up
                cmp     bl, 0x1D
                je      .ctrl_up
                cmp     bl, 0x38
                je      .alt_up
                jmp     .clear_prefix

; ---- modifier bookkeeping -------------------------------------------
.shift_down:    or      dword [keyboard_modifiers], MOD_SHIFT
                jmp     .clear_prefix
.shift_up:      and     dword [keyboard_modifiers], ~MOD_SHIFT
                jmp     .clear_prefix
.ctrl_down:     or      dword [keyboard_modifiers], MOD_CTRL
                jmp     .clear_prefix
.ctrl_up:       and     dword [keyboard_modifiers], ~MOD_CTRL
                jmp     .clear_prefix
.alt_down:      or      dword [keyboard_modifiers], MOD_ALT
                jmp     .clear_prefix
.alt_up:        and     dword [keyboard_modifiers], ~MOD_ALT
                jmp     .clear_prefix
.caps_toggle:   xor     dword [keyboard_modifiers], MOD_CAPS
                jmp     .clear_prefix
.num_toggle:    xor     dword [keyboard_modifiers], MOD_NUM
                jmp     .clear_prefix
.scroll_toggle: xor     dword [keyboard_modifiers], MOD_SCROLL

.clear_prefix:
                mov     dword [extended], 0
.done:
                popad
                pop     ebp
                ret

; ---------------------------------------------------------------------
; buffer_push — EAX = key code (clobbers EAX/EDX)
; ---------------------------------------------------------------------
buffer_push:
                push    ecx
                mov     ecx, [buf_head]
                mov     edx, ecx
                inc     edx
                and     edx, BUFFER_SIZE - 1
                cmp     edx, [buf_tail]
                je      .full                   ; drop rather than overwrite
                mov     [key_buffer + ecx * 4], eax
                mov     [buf_head], edx
.full:
                pop     ecx
                ret

; ---------------------------------------------------------------------
; keyboard_available -> EAX = number of queued keys
; ---------------------------------------------------------------------
keyboard_available:
                mov     eax, [buf_head]
                sub     eax, [buf_tail]
                and     eax, BUFFER_SIZE - 1
                ret

; ---------------------------------------------------------------------
; keyboard_poll -> EAX = key, or -1 when the queue is empty
; ---------------------------------------------------------------------
keyboard_poll:
                push    ecx
                pushfd
                cli
                mov     ecx, [buf_tail]
                cmp     ecx, [buf_head]
                je      .empty
                mov     eax, [key_buffer + ecx * 4]
                inc     ecx
                and     ecx, BUFFER_SIZE - 1
                mov     [buf_tail], ecx
                popfd
                pop     ecx
                ret
.empty:
                mov     eax, -1
                popfd
                pop     ecx
                ret

; ---------------------------------------------------------------------
; keyboard_getchar -> EAX, blocking.  Serial input counts too, which
;                     makes the shell usable over a headless console.
; ---------------------------------------------------------------------
keyboard_getchar:
.again:
                call    keyboard_poll
                cmp     eax, -1
                jne     .got

                call    serial_poll
                cmp     eax, -1
                jne     .serial

                sti
                hlt                             ; wait for the next interrupt
                jmp     .again

.serial:
                cmp     al, 13                  ; CR from a terminal
                jne     .got
                mov     eax, 10
.got:
                ret

; ---------------------------------------------------------------------
; keyboard_readline(buf, size) -> length
;   Line editing with backspace; echoes as it goes.
; ---------------------------------------------------------------------
keyboard_readline:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     esi, [ebp + 8]          ; buffer
                mov     edi, [ebp + 12]         ; size
                test    edi, edi
                jz      .empty_buffer
                dec     edi                     ; keep room for the NUL
                xor     ebx, ebx                ; current length

.loop:
                call    keyboard_getchar

                cmp     eax, 10                 ; enter
                je      .finish
                cmp     eax, 13
                je      .finish
                cmp     eax, 8                  ; backspace
                je      .backspace
                cmp     eax, 127
                je      .backspace

                cmp     eax, 32                 ; printable range only
                jb      .loop
                cmp     eax, 126
                ja      .loop

                cmp     ebx, edi
                jae     .loop                   ; buffer full

                mov     [esi + ebx], al
                inc     ebx
                push    eax
                call    vga_putc
                add     esp, 4
                jmp     .loop

.backspace:
                test    ebx, ebx
                jz      .loop
                dec     ebx
                push    dword 8
                call    vga_putc
                add     esp, 4
                jmp     .loop

.finish:
                mov     byte [esi + ebx], 0
                push    dword 10
                call    vga_putc
                add     esp, 4
                mov     eax, ebx
                jmp     .done

.empty_buffer:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
;  Scan code set 1 translation tables (US layout)
; ---------------------------------------------------------------------
                section .rodata
                align   16
keymap_normal:
                db      0,    27,  '1',  '2',  '3',  '4',  '5',  '6'   ; 00-07
                db      '7',  '8', '9',  '0',  '-',  '=',    8,    9   ; 08-0F
                db      'q',  'w', 'e',  'r',  't',  'y',  'u',  'i'   ; 10-17
                db      'o',  'p', '[',  ']',   10,    0,  'a',  's'   ; 18-1F
                db      'd',  'f', 'g',  'h',  'j',  'k',  'l',  ';'   ; 20-27
                db      39,   '`',   0, '\',  'z',  'x',  'c',  'v'    ; 28-2F
                db      'b',  'n', 'm',  ',',  '.',  '/',    0,  '*'   ; 30-37
                db      0,    ' ',   0,    0,    0,    0,    0,    0   ; 38-3F
                db      0,      0,   0,    0,    0,    0,    0,  '7'   ; 40-47
                db      '8',  '9', '-',  '4',  '5',  '6',  '+',  '1'   ; 48-4F
                db      '2',  '3', '0',  '.',    0,    0,    0,    0   ; 50-57
                db      0                                              ; 58

                align   16
keymap_shift:
                db      0,    27,  '!',  '@',  '#',  '$',  '%',  '^'   ; 00-07
                db      '&',  '*', '(',  ')',  '_',  '+',    8,    9   ; 08-0F
                db      'Q',  'W', 'E',  'R',  'T',  'Y',  'U',  'I'   ; 10-17
                db      'O',  'P', '{',  '}',   10,    0,  'A',  'S'   ; 18-1F
                db      'D',  'F', 'G',  'H',  'J',  'K',  'L',  ':'   ; 20-27
                db      '"',  '~',   0,  '|',  'Z',  'X',  'C',  'V'   ; 28-2F
                db      'B',  'N', 'M',  '<',  '>',  '?',    0,  '*'   ; 30-37
                db      0,    ' ',   0,    0,    0,    0,    0,    0   ; 38-3F
                db      0,      0,   0,    0,    0,    0,    0,  '7'   ; 40-47
                db      '8',  '9', '-',  '4',  '5',  '6',  '+',  '1'   ; 48-4F
                db      '2',  '3', '0',  '.',    0,    0,    0,    0   ; 50-57
                db      0                                              ; 58

; ---------------------------------------------------------------------
                section .bss
                alignb  4
key_buffer:             resd    BUFFER_SIZE
buf_head:               resd    1
buf_tail:               resd    1
extended:               resd    1
keyboard_modifiers:     resd    1
keyboard_last_scancode: resd    1
