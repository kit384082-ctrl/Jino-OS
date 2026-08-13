; =====================================================================
;  Jino-OS  ::  gdt.asm — Global Descriptor Table and TSS
; ---------------------------------------------------------------------
;  We run a flat memory model: kernel and user segments all cover the
;  whole 4 GiB address space and protection comes from paging instead.
;  A single TSS supplies the ring-0 stack used on privilege changes.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  gdt_init
                global  gdt_set_kernel_stack
                global  tss_entry
                global  gdt_descriptor

                extern  kprintf

GDT_ENTRIES     equ     6

                section .text

; ---------------------------------------------------------------------
; gdt_init — build the descriptors, load GDTR and reload the selectors.
; ---------------------------------------------------------------------
gdt_init:
                push    ebp
                mov     ebp, esp

                ; ---- 0x00 : the mandatory null descriptor ------------
                mov     dword [gdt + 0], 0
                mov     dword [gdt + 4], 0

                ; ---- 0x08 : ring 0 code, base 0, limit 4 GiB ---------
                ; access = present | ring0 | code | readable
                push    dword 0xCF
                push    dword 0x9A
                push    dword 0x000FFFFF
                push    dword 0
                push    dword SEG_KCODE
                call    gdt_set_entry
                add     esp, 20

                ; ---- 0x10 : ring 0 data ------------------------------
                push    dword 0xCF
                push    dword 0x92
                push    dword 0x000FFFFF
                push    dword 0
                push    dword SEG_KDATA
                call    gdt_set_entry
                add     esp, 20

                ; ---- 0x18 : ring 3 code ------------------------------
                push    dword 0xCF
                push    dword 0xFA
                push    dword 0x000FFFFF
                push    dword 0
                push    dword SEG_UCODE
                call    gdt_set_entry
                add     esp, 20

                ; ---- 0x20 : ring 3 data ------------------------------
                push    dword 0xCF
                push    dword 0xF2
                push    dword 0x000FFFFF
                push    dword 0
                push    dword SEG_UDATA
                call    gdt_set_entry
                add     esp, 20

                ; ---- 0x28 : the task state segment -------------------
                call    tss_setup

                ; ---- load it -----------------------------------------
                mov     word [gdt_descriptor], GDT_ENTRIES * 8 - 1
                mov     dword [gdt_descriptor + 2], gdt
                lgdt    [gdt_descriptor]

                ; far jump to reload CS, then the data selectors
                jmp     SEG_KCODE:.reload
.reload:
                mov     ax, SEG_KDATA
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax
                mov     ss, ax

                mov     ax, SEG_TSS | 3         ; RPL 3 as the CPU expects
                ltr     ax

                pop     ebp
                ret

; ---------------------------------------------------------------------
; gdt_set_entry(selector, base, limit, access, granularity)
; ---------------------------------------------------------------------
gdt_set_entry:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    edi

                mov     edi, [ebp + 8]          ; selector == byte offset
                and     edi, ~7
                add     edi, gdt

                mov     eax, [ebp + 12]         ; base
                mov     ebx, [ebp + 16]         ; limit
                mov     ecx, [ebp + 20]         ; access byte
                mov     edx, [ebp + 24]         ; granularity/flags nibble

                ; limit 15:0
                mov     [edi + 0], bx
                ; base 15:0
                mov     [edi + 2], ax
                ; base 23:16
                shr     eax, 16
                mov     [edi + 4], al
                ; access byte
                mov     [edi + 5], cl
                ; limit 19:16 together with the flags
                shr     ebx, 16
                and     bl, 0x0F
                and     dl, 0xF0
                or      bl, dl
                mov     [edi + 6], bl
                ; base 31:24
                mov     eax, [ebp + 12]
                shr     eax, 24
                mov     [edi + 7], al

                pop     edi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; tss_setup — a minimal 32-bit TSS: only SS0/ESP0 and the I/O map base
;             actually matter for a kernel that uses software task
;             switching.
; ---------------------------------------------------------------------
tss_setup:
                push    ebp
                mov     ebp, esp
                push    edi

                ; zero the structure first
                mov     edi, tss_entry
                mov     ecx, 104 / 4
                xor     eax, eax
                rep     stosd

                mov     dword [tss_entry + 4], 0        ; esp0, set later
                mov     dword [tss_entry + 8], SEG_KDATA ; ss0
                mov     word  [tss_entry + 102], 104     ; iomap base = end

                ; descriptor: type 0x89 (present, 32-bit available TSS)
                push    dword 0x00
                push    dword 0x89
                push    dword 103
                push    dword tss_entry
                push    dword SEG_TSS
                call    gdt_set_entry
                add     esp, 20

                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; gdt_set_kernel_stack(esp0) — where the CPU should switch to when an
;                              interrupt arrives while in ring 3.
; ---------------------------------------------------------------------
gdt_set_kernel_stack:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                mov     [tss_entry + 4], eax
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .bss
                alignb  8
gdt:            resb    GDT_ENTRIES * 8
gdt_descriptor: resb    6
                alignb  16
tss_entry:      resb    104
