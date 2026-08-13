; =====================================================================
;  Jino-OS  ::  stage1.asm  —  Master Boot Record (512 bytes)
; ---------------------------------------------------------------------
;  The BIOS loads this sector at 0000:7C00 in 16-bit real mode with
;  DL = BIOS boot drive number.  Our only job here is to be small and
;  reliable: set up a flat real-mode environment, pull stage2 off the
;  boot device and hand control over to it.
;
;  Reading is done with the INT 13h LBA extensions when the firmware
;  advertises them, and falls back to classic CHS geometry otherwise,
;  so the same MBR boots on floppies, USB sticks and IDE/SATA disks.
; =====================================================================

                bits    16
                org     0x7C00

%ifndef STAGE2_LBA
%define STAGE2_LBA      1
%endif
%ifndef STAGE2_SECTORS
%define STAGE2_SECTORS  8
%endif

STAGE2_SEG      equ     0x0000
STAGE2_OFF      equ     0x7E00          ; loaded straight after the MBR
STACK_TOP       equ     0x7C00          ; grows down, below our code

; ---------------------------------------------------------------------
start:
                cli
                xor     ax, ax
                mov     ds, ax
                mov     es, ax
                mov     ss, ax
                mov     sp, STACK_TOP
                cld
                sti

                mov     [boot_drive], dl        ; BIOS gives us the drive

                mov     si, msg_boot
                call    puts

                ; --- does the BIOS support the LBA extensions? --------
                mov     ah, 0x41
                mov     bx, 0x55AA
                mov     dl, [boot_drive]
                int     0x13
                jc      .use_chs
                cmp     bx, 0xAA55
                jne     .use_chs
                test    cl, 1                   ; bit0 = packet access
                jz      .use_chs

                call    read_lba
                jmp     .loaded

.use_chs:
                call    read_chs

.loaded:
                mov     si, msg_ok
                call    puts

                mov     dl, [boot_drive]        ; stage2 wants the drive too
                jmp     STAGE2_SEG:STAGE2_OFF

; ---------------------------------------------------------------------
; read_lba — INT 13h AH=42h, extended read using a disk address packet
; ---------------------------------------------------------------------
read_lba:
                mov     si, dap
                mov     ah, 0x42
                mov     dl, [boot_drive]
                int     0x13
                jc      disk_error
                ret

; ---------------------------------------------------------------------
; read_chs — classic cylinder/head/sector read.  We query the drive
;            geometry first so the translation is always correct.
; ---------------------------------------------------------------------
read_chs:
                push    es
                mov     ah, 0x08                ; get drive parameters
                mov     dl, [boot_drive]
                xor     di, di
                mov     es, di
                int     0x13
                pop     es
                jc      disk_error

                and     cl, 0x3F                ; CL[5:0] = sectors/track
                mov     [spt], cl
                mov     al, dh
                inc     al                      ; DH = max head index
                mov     [heads], al

                mov     ax, STAGE2_LBA
                xor     dx, dx
                div     word [spt]              ; ax = lba/spt, dx = sector-1
                mov     cl, dl
                inc     cl                      ; CL = sector (1-based)
                xor     dx, dx
                div     word [heads]            ; ax = cylinder, dx = head
                mov     ch, al                  ; CH = cylinder low 8 bits
                mov     dh, dl                  ; DH = head

                mov     bx, STAGE2_OFF
                mov     ax, 0x0200 | STAGE2_SECTORS
                mov     dl, [boot_drive]
                int     0x13
                jc      disk_error
                cmp     al, STAGE2_SECTORS
                jne     disk_error
                ret

; ---------------------------------------------------------------------
disk_error:
                mov     si, msg_err
                call    puts
                mov     si, msg_reboot
                call    puts
                xor     ax, ax
                int     0x16                    ; wait for a key
                int     0x19                    ; warm reboot
.hang:          hlt
                jmp     .hang

; ---------------------------------------------------------------------
; puts — write the NUL terminated string at DS:SI via BIOS teletype
; ---------------------------------------------------------------------
puts:
                pusha
                mov     ah, 0x0E
                xor     bx, bx
.next:          lodsb
                test    al, al
                jz      .done
                int     0x10
                jmp     .next
.done:          popa
                ret

; ------------------------------------------------------------ data ---
                align   4
dap:            db      0x10                    ; packet size
                db      0
                dw      STAGE2_SECTORS          ; sectors to transfer
                dw      STAGE2_OFF              ; offset
                dw      STAGE2_SEG              ; segment
                dq      STAGE2_LBA              ; 64-bit LBA

boot_drive:     db      0x80
spt:            dw      18
heads:          dw      2

msg_boot:       db      "Jino-OS", 13, 10, 0
msg_ok:         db      "stage2", 13, 10, 0
msg_err:        db      "disk error", 13, 10, 0
msg_reboot:     db      "press any key", 13, 10, 0

; --------------------------------------------------- MBR signature ---
                times   446 - ($ - $$) db 0     ; pad up to partition table

partition_table:
                ; A single "whole disk" entry so firmware that insists on
                ; a valid table still recognises the medium.
                db      0x80                    ; bootable
                db      0x00, 0x02, 0x00        ; CHS first  (0/0/2)
                db      0x7F                    ; type: unknown/other
                db      0x0F, 0xFF, 0xFF        ; CHS last
                dd      1                       ; first LBA
                dd      2879                    ; sector count
                times   16 * 3 db 0             ; three empty entries

                dw      0xAA55
