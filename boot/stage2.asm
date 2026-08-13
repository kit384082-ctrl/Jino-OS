; =====================================================================
;  Jino-OS  ::  stage2.asm  —  second stage loader
; ---------------------------------------------------------------------
;  Loaded by stage1 at 0000:7E00, still in 16-bit real mode.
;
;  Responsibilities:
;    1.  Collect a memory map from the BIOS (INT 15h, EAX=E820, with
;        E801/88 fallbacks) and stash it for the kernel.
;    2.  Enable the A20 gate so we can address memory above 1 MiB.
;    3.  Read the kernel image off the boot device and copy it to
;        physical 0x00100000 through "unreal mode".
;    4.  Install a flat GDT, switch the CPU into 32-bit protected mode
;        and jump into the kernel with a boot-information block.
; =====================================================================

                bits    16
                org     0x7E00

%ifndef KERNEL_LBA
%define KERNEL_LBA      9
%endif
%ifndef KERNEL_SECTORS
%define KERNEL_SECTORS  128
%endif

%include "bootinfo.inc"

KERNEL_PHYS     equ     0x00100000      ; where the kernel is assembled for
DISK_BUF        equ     0x00010000      ; 64 KiB scratch below 1 MiB
DISK_BUF_SEG    equ     0x1000
CHUNK_SECTORS   equ     32              ; 16 KiB per BIOS call

; ---------------------------------------------------------------------
stage2_entry:
                cli
                xor     ax, ax
                mov     ds, ax
                mov     es, ax
                mov     ss, ax
                mov     sp, 0x7C00
                cld
                sti

                mov     [bi_drive], dl

                mov     si, msg_hello
                call    puts

                call    init_bootinfo
                call    detect_memory
                call    enable_a20
                call    load_kernel

                mov     si, msg_pmode
                call    puts

                call    enter_protected_mode    ; never returns

; ---------------------------------------------------------------------
; init_bootinfo — zero the boot information block and fill the parts we
;                 already know about.
; ---------------------------------------------------------------------
init_bootinfo:
                push    es
                mov     ax, 0
                mov     es, ax
                mov     di, BOOTINFO_ADDR
                mov     cx, BOOTINFO_SIZE / 2
                xor     ax, ax
                rep     stosw
                pop     es

                mov     dword [BOOTINFO_ADDR + BI_MAGIC], BOOTINFO_MAGIC
                xor     eax, eax
                mov     al, [bi_drive]
                mov     dword [BOOTINFO_ADDR + BI_DRIVE], eax
                mov     dword [BOOTINFO_ADDR + BI_E820_ADDR], E820_ADDR
                mov     dword [BOOTINFO_ADDR + BI_KERNEL_LBA], KERNEL_LBA
                mov     dword [BOOTINFO_ADDR + BI_KERNEL_SECT], KERNEL_SECTORS
                mov     dword [BOOTINFO_ADDR + BI_KERNEL_PHYS], KERNEL_PHYS
                ret

; ---------------------------------------------------------------------
; detect_memory — INT 15h EAX=E820 walk, plus the legacy fallbacks.
; ---------------------------------------------------------------------
detect_memory:
                ; ---- conventional memory (INT 12h returns KiB) -------
                int     0x12
                movzx   eax, ax
                mov     [BOOTINFO_ADDR + BI_LOWMEM_KB], eax

                ; ---- extended memory (INT 15h AX=E801) ---------------
                xor     cx, cx
                xor     dx, dx
                mov     ax, 0xE801
                int     0x15
                jc      .no_e801
                test    cx, cx
                jnz     .use_cx
                mov     cx, ax
                mov     dx, bx
.use_cx:
                movzx   eax, dx                 ; DX = 64 KiB blocks > 16 MiB
                shl     eax, 6                  ; -> KiB
                movzx   ebx, cx                 ; CX = KiB between 1 and 16 MiB
                add     eax, ebx
                mov     [BOOTINFO_ADDR + BI_HIGHMEM_KB], eax
.no_e801:

                ; ---- the real map ------------------------------------
                mov     di, E820_ADDR
                xor     ebx, ebx
                xor     bp, bp                  ; entry counter
                mov     edx, 0x534D4150         ; 'SMAP'
.next:
                mov     eax, 0xE820
                mov     ecx, 24
                mov     dword [es:di + 20], 1   ; force a valid ACPI 3 field
                int     0x15
                jc      .done                   ; carry on first call = no E820
                cmp     eax, 0x534D4150
                jne     .done
                jcxz    .skip                   ; zero length entry
                cmp     cl, 20
                jbe     .keep
                test    byte [es:di + 20], 1    ; "ignore this entry" bit
                jz      .skip
.keep:
                mov     ecx, [es:di + 8]        ; length low
                or      ecx, [es:di + 12]       ; length high
                jz      .skip
                inc     bp
                add     di, 24
                cmp     bp, E820_MAX
                jae     .done
.skip:
                test    ebx, ebx
                jnz     .next
.done:
                movzx   eax, bp
                mov     [BOOTINFO_ADDR + BI_E820_COUNT], eax
                ret

; ---------------------------------------------------------------------
; enable_a20 — try the cheap methods first, verify after each one.
; ---------------------------------------------------------------------
enable_a20:
                call    a20_check
                jc      .done                   ; CF=1 -> already enabled

                mov     ax, 0x2401              ; BIOS interface
                int     0x15
                call    a20_check
                jc      .done

                in      al, 0x92                ; fast A20
                test    al, 2
                jnz     .skip_fast
                or      al, 2
                and     al, 0xFE                ; never touch the reset bit
                out     0x92, al
.skip_fast:
                call    a20_check
                jc      .done

                call    a20_keyboard            ; 8042 controller
                call    a20_check
                jc      .done

                mov     si, msg_a20err
                call    puts
.done:
                ret

; a20_keyboard — the classic keyboard controller dance
a20_keyboard:
                cli
                call    .wait_in
                mov     al, 0xAD                ; disable keyboard
                out     0x64, al
                call    .wait_in
                mov     al, 0xD0                ; read output port
                out     0x64, al
                call    .wait_out
                in      al, 0x60
                push    ax
                call    .wait_in
                mov     al, 0xD1                ; write output port
                out     0x64, al
                call    .wait_in
                pop     ax
                or      al, 2                   ; set the A20 bit
                out     0x60, al
                call    .wait_in
                mov     al, 0xAE                ; re-enable keyboard
                out     0x64, al
                call    .wait_in
                sti
                ret
.wait_in:
                in      al, 0x64
                test    al, 2
                jnz     .wait_in
                ret
.wait_out:
                in      al, 0x64
                test    al, 1
                jz      .wait_out
                ret

; a20_check — CF=1 when the gate is open (0000:0500 != FFFF:0510)
a20_check:
                push    ds
                push    es
                pusha
                xor     ax, ax
                mov     es, ax
                mov     ax, 0xFFFF
                mov     ds, ax
                mov     di, 0x0500
                mov     si, 0x0510
                mov     al, [es:di]
                push    ax
                mov     al, [ds:si]
                push    ax
                mov     byte [es:di], 0x00
                mov     byte [ds:si], 0xFF
                mov     al, [es:di]
                cmp     al, 0xFF                ; wrapped -> A20 still closed
                pop     bx
                mov     [ds:si], bl
                pop     bx
                mov     [es:di], bl
                popa
                pop     es
                pop     ds
                je      .closed
                stc
                ret
.closed:
                clc
                ret

; ---------------------------------------------------------------------
; load_kernel — read KERNEL_SECTORS sectors starting at KERNEL_LBA and
;               move them to KERNEL_PHYS one chunk at a time.
; ---------------------------------------------------------------------
load_kernel:
                mov     si, msg_load
                call    puts

                call    unreal_mode

                mov     dword [cur_lba], KERNEL_LBA
                mov     dword [cur_dest], KERNEL_PHYS
                mov     word  [left], KERNEL_SECTORS

.loop:
                mov     cx, [left]
                test    cx, cx
                jz      .finished
                cmp     cx, CHUNK_SECTORS
                jbe     .have_count
                mov     cx, CHUNK_SECTORS
.have_count:
                mov     [this_count], cx

                mov     eax, [cur_lba]
                mov     bx, DISK_BUF_SEG
                call    disk_read               ; CX sectors -> BX:0000

                ; copy the chunk up beyond 1 MiB
                movzx   ecx, word [this_count]
                shl     ecx, 9                  ; sectors -> bytes
                shr     ecx, 2                  ; -> dwords
                mov     esi, DISK_BUF
                mov     edi, [cur_dest]
                call    copy_up

                movzx   eax, word [this_count]
                mov     ebx, eax
                shl     ebx, 9
                add     [cur_dest], ebx
                add     [cur_lba], eax
                sub     [left], ax

                mov     al, '.'
                call    putc
                jmp     .loop

.finished:
                mov     si, msg_crlf
                call    puts
                ret

; ---------------------------------------------------------------------
; copy_up — ECX dwords from linear ESI to linear EDI (unreal mode).
; ---------------------------------------------------------------------
copy_up:
                push    ds
                push    es
.next:
                mov     eax, [fs:esi]
                mov     [gs:edi], eax
                add     esi, 4
                add     edi, 4
                dec     ecx
                jnz     .next
                pop     es
                pop     ds
                ret

; ---------------------------------------------------------------------
; disk_read — EAX = LBA, CX = sector count, BX = destination segment.
;             Uses INT 13h extensions when available, CHS otherwise.
; ---------------------------------------------------------------------
disk_read:
                pusha
                mov     [rd_lba], eax
                mov     [rd_count], cx
                mov     [rd_seg], bx

                mov     ah, 0x41
                mov     bx, 0x55AA
                mov     dl, [bi_drive]
                int     0x13
                jc      .chs
                cmp     bx, 0xAA55
                jne     .chs
                test    cl, 1
                jz      .chs

                mov     eax, [rd_lba]
                mov     [dap_lba], eax
                mov     dword [dap_lba + 4], 0
                mov     ax, [rd_count]
                mov     [dap_count], ax
                mov     word [dap_off], 0
                mov     ax, [rd_seg]
                mov     [dap_seg], ax

                mov     si, dap
                mov     ah, 0x42
                mov     dl, [bi_drive]
                int     0x13
                jc      .fail
                popa
                ret

.chs:
                push    es
                mov     ah, 0x08
                mov     dl, [bi_drive]
                xor     di, di
                mov     es, di
                int     0x13
                pop     es
                jc      .fail
                and     cl, 0x3F
                movzx   ax, cl
                mov     [spt], ax
                movzx   ax, dh
                inc     ax
                mov     [heads], ax

                mov     eax, [rd_lba]
                xor     edx, edx
                movzx   ebx, word [spt]
                div     ebx                     ; eax = lba/spt, edx = sec-1
                mov     cl, dl
                inc     cl
                xor     edx, edx
                movzx   ebx, word [heads]
                div     ebx                     ; eax = cyl, edx = head
                mov     ch, al
                shl     ah, 6                   ; cylinder bits 8-9
                or      cl, ah
                mov     dh, dl

                mov     ax, [rd_seg]
                mov     es, ax
                xor     bx, bx
                mov     ax, [rd_count]
                mov     ah, 0x02
                mov     dl, [bi_drive]
                int     0x13
                jc      .fail
                popa
                ret

.fail:
                mov     si, msg_diskerr
                call    puts
.halt:          cli
                hlt
                jmp     .halt

; ---------------------------------------------------------------------
; unreal_mode — briefly enter protected mode to load FS/GS with 4 GiB
;               segment limits, then drop back to real mode.
; ---------------------------------------------------------------------
unreal_mode:
                cli
                push    ds
                push    es
                lgdt    [gdt_ptr]
                mov     eax, cr0
                or      al, 1
                mov     cr0, eax
                jmp     $ + 2
                mov     bx, GDT_DATA32
                mov     fs, bx
                mov     gs, bx
                mov     eax, cr0
                and     al, 0xFE
                mov     cr0, eax
                jmp     $ + 2
                pop     es
                pop     ds
                sti
                ret

; ---------------------------------------------------------------------
; enter_protected_mode — the point of no return.
; ---------------------------------------------------------------------
enter_protected_mode:
                cli
                lgdt    [gdt_ptr]
                mov     eax, cr0
                or      eax, 1
                mov     cr0, eax
                jmp     GDT_CODE32:.pm32

                bits    32
.pm32:
                mov     ax, GDT_DATA32
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax
                mov     ss, ax
                mov     esp, 0x00090000         ; temporary stack

                mov     eax, BOOTINFO_MAGIC
                mov     ebx, BOOTINFO_ADDR
                jmp     GDT_CODE32:KERNEL_PHYS

                bits    16

; ---------------------------------------------------------------- I/O
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

putc:
                pusha
                mov     ah, 0x0E
                xor     bx, bx
                int     0x10
                popa
                ret

; --------------------------------------------------------------- data
                align   8
gdt:
                dq      0x0000000000000000      ; 0x00 null
                dq      0x00CF9A000000FFFF      ; 0x08 code32, base 0, 4 GiB
                dq      0x00CF92000000FFFF      ; 0x10 data32, base 0, 4 GiB
                dq      0x000F9A000000FFFF      ; 0x18 code16
                dq      0x000F92000000FFFF      ; 0x20 data16
gdt_end:

GDT_CODE32      equ     0x08
GDT_DATA32      equ     0x10

gdt_ptr:
                dw      gdt_end - gdt - 1
                dd      gdt

                align   4
dap:            db      0x10
                db      0
dap_count:      dw      0
dap_off:        dw      0
dap_seg:        dw      0
dap_lba:        dq      0

bi_drive:       db      0x80
spt:            dw      18
heads:          dw      2

rd_lba:         dd      0
rd_count:       dw      0
rd_seg:         dw      0

cur_lba:        dd      0
cur_dest:       dd      0
left:           dw      0
this_count:     dw      0

msg_hello:      db      "Jino-OS loader", 13, 10, 0
msg_load:       db      "loading kernel ", 0
msg_pmode:      db      "entering protected mode", 13, 10, 0
msg_diskerr:    db      13, 10, "stage2: disk read failed", 13, 10, 0
msg_a20err:     db      "A20 failed", 13, 10, 0
msg_crlf:       db      13, 10, 0
