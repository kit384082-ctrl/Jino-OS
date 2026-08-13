; =====================================================================
;  Jino-OS  ::  paging.asm — 32-bit two level paging
; ---------------------------------------------------------------------
;  The kernel identity maps the first 16 MiB so that physical pointers
;  keep working after CR0.PG goes high, then enables paging.  Page
;  faults are reported through the exception handler installed here.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  paging_init
                global  paging_map
                global  paging_unmap
                global  paging_get_physical
                global  paging_enable
                global  paging_disable
                global  paging_flush_tlb
                global  paging_invalidate
                global  paging_is_enabled
                global  page_directory
                global  paging_fault_count

                extern  pmm_alloc_page
                extern  pmm_free_page
                extern  memset
                extern  kprintf
                extern  idt_register_handler
                extern  panic

IDENTITY_MB     equ     16
IDENTITY_TABLES equ     IDENTITY_MB / 4         ; each table covers 4 MiB

                section .text

; ---------------------------------------------------------------------
; paging_init — build the identity map and turn paging on.
; ---------------------------------------------------------------------
paging_init:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                ; ---- a blank page directory --------------------------
                push    dword PAGE_SIZE
                push    dword 0
                push    dword page_directory
                call    memset
                add     esp, 12

                ; ---- identity map the low memory ---------------------
                xor     esi, esi                ; table index
.table_loop:
                cmp     esi, IDENTITY_TABLES
                jae     .tables_done

                ; page_tables[esi] is a statically reserved table
                mov     eax, esi
                shl     eax, PAGE_SHIFT
                add     eax, page_tables
                mov     edi, eax                ; edi = table address

                ; fill 1024 entries, each mapping one 4 KiB frame
                xor     ebx, ebx
.entry_loop:
                mov     eax, esi
                shl     eax, 10                 ; table * 1024
                add     eax, ebx                ; + entry
                shl     eax, PAGE_SHIFT         ; physical address
                or      eax, PAGE_PRESENT | PAGE_WRITE
                mov     [edi + ebx * 4], eax
                inc     ebx
                cmp     ebx, 1024
                jb      .entry_loop

                ; link the table into the directory
                mov     eax, edi
                or      eax, PAGE_PRESENT | PAGE_WRITE
                mov     [page_directory + esi * 4], eax

                inc     esi
                jmp     .table_loop
.tables_done:

                ; ---- the page fault handler --------------------------
                push    dword page_fault_handler
                push    dword 14
                call    idt_register_handler
                add     esp, 8

                ; ---- switch it on ------------------------------------
                push    dword page_directory
                call    paging_enable
                add     esp, 4

                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; paging_enable(directory_physical)
; ---------------------------------------------------------------------
paging_enable:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                mov     [current_directory], eax
                mov     cr3, eax
                mov     eax, cr0
                or      eax, 0x80000000         ; PG
                mov     cr0, eax
                mov     dword [paging_active], 1
                pop     ebp
                ret

; ---------------------------------------------------------------------
; paging_disable
; ---------------------------------------------------------------------
paging_disable:
                mov     eax, cr0
                and     eax, 0x7FFFFFFF
                mov     cr0, eax
                mov     dword [paging_active], 0
                ret

paging_is_enabled:
                mov     eax, [paging_active]
                ret

; ---------------------------------------------------------------------
; paging_map(virtual, physical, flags) -> EAX = 1 on success
; ---------------------------------------------------------------------
paging_map:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     esi, [ebp + 8]          ; virtual address
                mov     edi, [ebp + 12]         ; physical address
                mov     ebx, [ebp + 16]         ; flags

                and     esi, ~(PAGE_SIZE - 1)
                and     edi, ~(PAGE_SIZE - 1)

                ; directory index = virt >> 22
                mov     eax, esi
                shr     eax, 22
                mov     ecx, eax                ; ecx = pd index

                mov     eax, [current_directory]
                mov     edx, [eax + ecx * 4]
                test    edx, PAGE_PRESENT
                jnz     .have_table

                ; allocate a fresh page table
                push    ecx
                call    pmm_alloc_page
                pop     ecx
                test    eax, eax
                jz      .fail

                push    eax
                push    ecx
                push    dword PAGE_SIZE
                push    dword 0
                push    eax
                call    memset
                add     esp, 12
                pop     ecx
                pop     eax

                mov     edx, eax
                or      edx, PAGE_PRESENT | PAGE_WRITE | PAGE_USER
                mov     eax, [current_directory]
                mov     [eax + ecx * 4], edx

.have_table:
                and     edx, ~0xFFF             ; table physical address

                ; table index = (virt >> 12) & 0x3FF
                mov     eax, esi
                shr     eax, PAGE_SHIFT
                and     eax, 0x3FF

                mov     ecx, edi
                or      ecx, ebx
                or      ecx, PAGE_PRESENT
                mov     [edx + eax * 4], ecx

                ; drop the stale translation
                push    esi
                call    paging_invalidate
                add     esp, 4

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
; paging_unmap(virtual)
; ---------------------------------------------------------------------
paging_unmap:
                push    ebp
                mov     ebp, esp
                push    esi

                mov     esi, [ebp + 8]
                and     esi, ~(PAGE_SIZE - 1)

                mov     eax, esi
                shr     eax, 22
                mov     ecx, [current_directory]
                mov     edx, [ecx + eax * 4]
                test    edx, PAGE_PRESENT
                jz      .done

                and     edx, ~0xFFF
                mov     eax, esi
                shr     eax, PAGE_SHIFT
                and     eax, 0x3FF
                mov     dword [edx + eax * 4], 0

                push    esi
                call    paging_invalidate
                add     esp, 4
.done:
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; paging_get_physical(virtual) -> EAX = physical address or 0
; ---------------------------------------------------------------------
paging_get_physical:
                push    ebp
                mov     ebp, esp
                push    esi

                mov     esi, [ebp + 8]
                mov     eax, esi
                shr     eax, 22
                mov     ecx, [current_directory]
                mov     edx, [ecx + eax * 4]
                test    edx, PAGE_PRESENT
                jz      .unmapped

                and     edx, ~0xFFF
                mov     eax, esi
                shr     eax, PAGE_SHIFT
                and     eax, 0x3FF
                mov     eax, [edx + eax * 4]
                test    eax, PAGE_PRESENT
                jz      .unmapped

                and     eax, ~0xFFF
                mov     edx, esi
                and     edx, PAGE_SIZE - 1      ; keep the offset
                add     eax, edx
                jmp     .done
.unmapped:
                xor     eax, eax
.done:
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; paging_invalidate(virtual) — a single TLB entry
; ---------------------------------------------------------------------
paging_invalidate:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                invlpg  [eax]
                pop     ebp
                ret

; ---------------------------------------------------------------------
; paging_flush_tlb — reload CR3
; ---------------------------------------------------------------------
paging_flush_tlb:
                mov     eax, cr3
                mov     cr3, eax
                ret

; ---------------------------------------------------------------------
; page_fault_handler(frame)
; ---------------------------------------------------------------------
page_fault_handler:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi

                inc     dword [paging_fault_count]

                mov     esi, [ebp + 8]          ; trap frame
                mov     eax, cr2                ; the offending address
                mov     ebx, [esi + 52]         ; error code

                push    dword [esi + 56]        ; eip
                push    ebx
                push    eax
                push    dword fmt_fault
                call    kprintf
                add     esp, 16

                ; decode the error code bits for the reader
                test    ebx, 1
                jnz     .protection
                push    dword msg_not_present
                call    kprintf
                add     esp, 4
                jmp     .rw
.protection:
                push    dword msg_protection
                call    kprintf
                add     esp, 4
.rw:
                test    ebx, 2
                jz      .read
                push    dword msg_write
                call    kprintf
                add     esp, 4
                jmp     .ring
.read:
                push    dword msg_read
                call    kprintf
                add     esp, 4
.ring:
                test    ebx, 4
                jz      .kernel_mode
                push    dword msg_user
                call    kprintf
                add     esp, 4
                jmp     .finish
.kernel_mode:
                push    dword msg_kernel
                call    kprintf
                add     esp, 4
.finish:
                push    dword msg_nl
                call    kprintf
                add     esp, 4

                push    dword msg_pf_panic
                call    panic
                add     esp, 4

                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
fmt_fault:      db      10, "page fault at 0x%08x (error 0x%x, eip 0x%08x): ", 0
msg_not_present: db     "page not present, ", 0
msg_protection: db      "protection violation, ", 0
msg_read:       db      "read, ", 0
msg_write:      db      "write, ", 0
msg_kernel:     db      "kernel mode", 0
msg_user:       db      "user mode", 0
msg_nl:         db      10, 0
msg_pf_panic:   db      "unhandled page fault", 0

; ---------------------------------------------------------------------
                section .data
current_directory:  dd  page_directory
paging_active:      dd  0

                section .bss
                alignb  4096
page_directory:     resb PAGE_SIZE
page_tables:        resb PAGE_SIZE * IDENTITY_TABLES
                alignb  4
paging_fault_count: resd 1
