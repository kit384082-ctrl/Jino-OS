; =====================================================================
;  Jino-OS  ::  ata.asm — PIO mode ATA (IDE) disk driver
; ---------------------------------------------------------------------
;  28-bit LBA reads and writes against the primary channel.  Polling
;  only: simple, and plenty fast enough for loading data off the boot
;  medium.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  ata_init
                global  ata_read_sectors
                global  ata_write_sectors
                global  ata_identify
                global  ata_present
                global  ata_model
                global  ata_sectors
                global  ata_print_info

                extern  kprintf
                extern  memset

; primary channel I/O ports
ATA_DATA        equ     0x1F0
ATA_ERROR       equ     0x1F1
ATA_FEATURES    equ     0x1F1
ATA_SECCOUNT    equ     0x1F2
ATA_LBA_LO      equ     0x1F3
ATA_LBA_MID     equ     0x1F4
ATA_LBA_HI      equ     0x1F5
ATA_DRIVE       equ     0x1F6
ATA_STATUS      equ     0x1F7
ATA_COMMAND     equ     0x1F7
ATA_CONTROL     equ     0x3F6

; status register bits
SR_ERR          equ     1 << 0
SR_DRQ          equ     1 << 3
SR_SRV          equ     1 << 4
SR_DF           equ     1 << 5
SR_RDY          equ     1 << 6
SR_BSY          equ     1 << 7

CMD_READ_PIO    equ     0x20
CMD_WRITE_PIO   equ     0x30
CMD_FLUSH       equ     0xE7
CMD_IDENTIFY    equ     0xEC

                section .text

; ---------------------------------------------------------------------
; ata_init -> EAX = 1 when a drive answered
; ---------------------------------------------------------------------
ata_init:
                push    ebp
                mov     ebp, esp

                mov     dword [ata_present], 0
                mov     dword [ata_sectors], 0
                mov     byte [ata_model], 0

                ; disable interrupts from the controller: we poll
                mov     dx, ATA_CONTROL
                mov     al, 0x02                ; nIEN
                out     dx, al

                call    ata_identify
                pop     ebp
                ret

; ---------------------------------------------------------------------
; ata_identify -> EAX = 1 on success, filling ata_model / ata_sectors
; ---------------------------------------------------------------------
ata_identify:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                ; select the master drive
                mov     dx, ATA_DRIVE
                mov     al, 0xA0
                out     dx, al
                call    ata_delay

                ; zero the addressing registers
                xor     al, al
                mov     dx, ATA_SECCOUNT
                out     dx, al
                mov     dx, ATA_LBA_LO
                out     dx, al
                mov     dx, ATA_LBA_MID
                out     dx, al
                mov     dx, ATA_LBA_HI
                out     dx, al

                mov     dx, ATA_COMMAND
                mov     al, CMD_IDENTIFY
                out     dx, al
                call    ata_delay

                ; status 0 means nothing is attached
                mov     dx, ATA_STATUS
                in      al, dx
                test    al, al
                jz      .absent

                ; wait for BSY to clear
                mov     ecx, 0x100000
.wait_bsy:
                mov     dx, ATA_STATUS
                in      al, dx
                test    al, SR_BSY
                jz      .bsy_clear
                dec     ecx
                jnz     .wait_bsy
                jmp     .absent
.bsy_clear:
                ; a non-zero LBA mid/high means this is ATAPI, not ATA
                mov     dx, ATA_LBA_MID
                in      al, dx
                test    al, al
                jnz     .absent
                mov     dx, ATA_LBA_HI
                in      al, dx
                test    al, al
                jnz     .absent

                ; now wait for DRQ or an error
                mov     ecx, 0x100000
.wait_drq:
                mov     dx, ATA_STATUS
                in      al, dx
                test    al, SR_ERR
                jnz     .absent
                test    al, SR_DRQ
                jnz     .have_data
                dec     ecx
                jnz     .wait_drq
                jmp     .absent

.have_data:
                ; read the 256 word identify block
                mov     edi, identify_buffer
                mov     ecx, 256
                mov     dx, ATA_DATA
                rep     insw

                ; ---- model string: words 27..46, byte swapped --------
                mov     esi, identify_buffer + 27 * 2
                mov     edi, ata_model
                mov     ecx, 20
.model_loop:
                mov     ax, [esi]
                xchg    al, ah                  ; the ATA spec stores it big endian
                mov     [edi], ax
                add     esi, 2
                add     edi, 2
                dec     ecx
                jnz     .model_loop
                mov     byte [ata_model + 40], 0

                ; trim the padding spaces
                mov     edi, ata_model + 39
.trim:
                cmp     edi, ata_model
                jb      .trimmed
                cmp     byte [edi], ' '
                jne     .trimmed
                mov     byte [edi], 0
                dec     edi
                jmp     .trim
.trimmed:

                ; ---- capacity: words 60..61 hold the 28-bit LBA count -
                mov     eax, [identify_buffer + 60 * 2]
                mov     [ata_sectors], eax

                mov     dword [ata_present], 1
                mov     eax, 1
                jmp     .done

.absent:
                mov     dword [ata_present], 0
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; ata_read_sectors(lba, count, buffer) -> EAX = 1 on success
; ---------------------------------------------------------------------
ata_read_sectors:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                cmp     dword [ata_present], 0
                je      .fail

                mov     ebx, [ebp + 8]          ; lba
                mov     esi, [ebp + 12]         ; sector count
                mov     edi, [ebp + 16]         ; destination

                test    esi, esi
                jz      .fail
                cmp     esi, 256
                ja      .fail

                call    ata_wait_ready
                test    eax, eax
                jz      .fail

                ; drive/head: master, LBA mode, bits 27:24 of the address
                mov     eax, ebx
                shr     eax, 24
                and     al, 0x0F
                or      al, 0xE0
                mov     dx, ATA_DRIVE
                out     dx, al

                mov     dx, ATA_FEATURES
                xor     al, al
                out     dx, al

                mov     eax, esi
                mov     dx, ATA_SECCOUNT
                out     dx, al

                mov     eax, ebx
                mov     dx, ATA_LBA_LO
                out     dx, al
                mov     eax, ebx
                shr     eax, 8
                mov     dx, ATA_LBA_MID
                out     dx, al
                mov     eax, ebx
                shr     eax, 16
                mov     dx, ATA_LBA_HI
                out     dx, al

                mov     dx, ATA_COMMAND
                mov     al, CMD_READ_PIO
                out     dx, al

                ; one 512 byte transfer per sector
.sector_loop:
                test    esi, esi
                jz      .success

                call    ata_poll
                test    eax, eax
                jz      .fail

                mov     ecx, 256
                mov     dx, ATA_DATA
                rep     insw

                dec     esi
                jmp     .sector_loop

.success:
                mov     eax, 1
                jmp     .done
.fail:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; ata_write_sectors(lba, count, buffer) -> EAX = 1 on success
; ---------------------------------------------------------------------
ata_write_sectors:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                cmp     dword [ata_present], 0
                je      .fail

                mov     ebx, [ebp + 8]
                mov     esi, [ebp + 12]
                mov     edi, [ebp + 16]

                test    esi, esi
                jz      .fail
                cmp     esi, 256
                ja      .fail

                call    ata_wait_ready
                test    eax, eax
                jz      .fail

                mov     eax, ebx
                shr     eax, 24
                and     al, 0x0F
                or      al, 0xE0
                mov     dx, ATA_DRIVE
                out     dx, al

                mov     dx, ATA_FEATURES
                xor     al, al
                out     dx, al

                mov     eax, esi
                mov     dx, ATA_SECCOUNT
                out     dx, al

                mov     eax, ebx
                mov     dx, ATA_LBA_LO
                out     dx, al
                mov     eax, ebx
                shr     eax, 8
                mov     dx, ATA_LBA_MID
                out     dx, al
                mov     eax, ebx
                shr     eax, 16
                mov     dx, ATA_LBA_HI
                out     dx, al

                mov     dx, ATA_COMMAND
                mov     al, CMD_WRITE_PIO
                out     dx, al

.sector_loop:
                test    esi, esi
                jz      .flush

                call    ata_poll
                test    eax, eax
                jz      .fail

                ; outsw does not exist as a rep-prefixed pair with esi
                ; already in use, so push the data word by word
                mov     ecx, 256
                mov     dx, ATA_DATA
.word_loop:
                mov     ax, [edi]
                out     dx, ax
                add     edi, 2
                dec     ecx
                jnz     .word_loop

                dec     esi
                jmp     .sector_loop

.flush:
                ; A cache flush returns no data, so waiting on DRQ here
                ; would spin until the timeout; wait for the drive to go
                ; ready again instead.
                mov     dx, ATA_COMMAND
                mov     al, CMD_FLUSH
                out     dx, al
                call    ata_wait_ready

                mov     eax, 1
                jmp     .done
.fail:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; ata_poll -> EAX = 1 when DRQ is up without an error
; ---------------------------------------------------------------------
ata_poll:
                push    ecx
                push    edx
                call    ata_delay

                mov     ecx, 0x400000
.wait:
                mov     dx, ATA_STATUS
                in      al, dx
                test    al, SR_BSY
                jnz     .again
                test    al, SR_ERR
                jnz     .error
                test    al, SR_DF
                jnz     .error
                test    al, SR_DRQ
                jnz     .ready
.again:
                dec     ecx
                jnz     .wait
.error:
                xor     eax, eax
                pop     edx
                pop     ecx
                ret
.ready:
                mov     eax, 1
                pop     edx
                pop     ecx
                ret

; ---------------------------------------------------------------------
; ata_wait_ready -> EAX = 1 when the drive is idle and ready
; ---------------------------------------------------------------------
ata_wait_ready:
                push    ecx
                push    edx
                mov     ecx, 0x400000
.wait:
                mov     dx, ATA_STATUS
                in      al, dx
                test    al, SR_BSY
                jnz     .again
                test    al, SR_RDY
                jnz     .ready
.again:
                dec     ecx
                jnz     .wait
                xor     eax, eax
                pop     edx
                pop     ecx
                ret
.ready:
                mov     eax, 1
                pop     edx
                pop     ecx
                ret

; ---------------------------------------------------------------------
; ata_delay — read the alternate status register a few times, which is
;             the canonical 400 ns wait.
; ---------------------------------------------------------------------
ata_delay:
                push    eax
                push    ecx
                push    edx
                mov     ecx, 4
                mov     dx, ATA_CONTROL
.loop:
                in      al, dx
                dec     ecx
                jnz     .loop
                pop     edx
                pop     ecx
                pop     eax
                ret

; ---------------------------------------------------------------------
; ata_print_info
; ---------------------------------------------------------------------
ata_print_info:
                push    ebp
                mov     ebp, esp

                cmp     dword [ata_present], 0
                je      .none

                ; capacity in MiB = sectors / 2048
                mov     eax, [ata_sectors]
                shr     eax, 11
                push    eax
                push    dword [ata_sectors]
                push    dword ata_model
                push    dword fmt_disk
                call    kprintf
                add     esp, 16
                jmp     .done
.none:
                push    dword msg_nodisk
                call    kprintf
                add     esp, 4
.done:
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
fmt_disk:       db      "ata0: %s, %u sectors (%u MiB)", 10, 0
msg_nodisk:     db      "ata0: no drive detected", 10, 0

                section .bss
                alignb  4
ata_present:        resd 1
ata_sectors:        resd 1
ata_model:          resb 48
                alignb  4
identify_buffer:    resb 512
