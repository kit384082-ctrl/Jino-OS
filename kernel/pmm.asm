; =====================================================================
;  Jino-OS  ::  pmm.asm — physical memory manager
; ---------------------------------------------------------------------
;  A bitmap allocator over 4 KiB page frames.  The map is built from the
;  E820 list the bootloader collected: everything starts out reserved
;  and usable regions are then released, after which the kernel image,
;  the low 1 MiB and the bitmap itself are taken back.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  pmm_init
                global  pmm_alloc_page
                global  pmm_alloc_pages
                global  pmm_free_page
                global  pmm_free_pages
                global  pmm_mark_used
                global  pmm_mark_free
                global  pmm_is_free
                global  pmm_total_pages
                global  pmm_used_pages
                global  pmm_free_pages_count
                global  pmm_bitmap_base
                global  pmm_highest_addr
                global  pmm_dump_map

                extern  kprintf
                extern  memset
                extern  __kernel_end

MAX_PAGES       equ     1024 * 1024             ; covers 4 GiB
BITMAP_BYTES    equ     MAX_PAGES / 8           ; 128 KiB

                section .text

; ---------------------------------------------------------------------
; pmm_init(bootinfo) — returns EAX = number of usable pages.
; ---------------------------------------------------------------------
pmm_init:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     esi, [ebp + 8]          ; boot info block

                ; ---- everything reserved to begin with ---------------
                push    dword BITMAP_BYTES
                push    dword 0xFF
                push    dword bitmap
                call    memset
                add     esp, 12

                mov     dword [pmm_total_pages], 0
                mov     dword [pmm_used_pages], 0
                mov     dword [pmm_highest_addr], 0

                ; ---- walk the E820 map -------------------------------
                mov     ecx, [esi + BI_E820_COUNT]
                test    ecx, ecx
                jz      .no_map
                mov     edi, [esi + BI_E820_ADDR]

.entry_loop:
                push    ecx

                mov     eax, [edi + E820_TYPE]
                cmp     eax, E820_USABLE
                jne     .next_entry

                ; ignore anything that starts above 4 GiB
                mov     eax, [edi + E820_BASE + 4]
                test    eax, eax
                jnz     .next_entry

                mov     ebx, [edi + E820_BASE]          ; base
                mov     edx, [edi + E820_LENGTH]        ; length low
                mov     eax, [edi + E820_LENGTH + 4]    ; length high
                test    eax, eax
                jz      .length_ok
                mov     edx, 0xFFFFFFFF                 ; clamp to 4 GiB
                sub     edx, ebx
.length_ok:
                test    edx, edx
                jz      .next_entry

                ; track the top of physical memory
                mov     eax, ebx
                add     eax, edx
                jc      .skip_high
                cmp     eax, [pmm_highest_addr]
                jbe     .skip_high
                mov     [pmm_highest_addr], eax
.skip_high:

                ; round the base up and the end down to whole pages
                mov     eax, ebx
                add     eax, PAGE_SIZE - 1
                and     eax, ~(PAGE_SIZE - 1)
                mov     ebx, eax                ; aligned start

                mov     eax, [edi + E820_BASE]
                add     eax, edx
                and     eax, ~(PAGE_SIZE - 1)   ; aligned end
                cmp     eax, ebx
                jbe     .next_entry

                sub     eax, ebx
                shr     eax, PAGE_SHIFT         ; page count
                mov     ecx, eax
                mov     eax, ebx
                shr     eax, PAGE_SHIFT         ; first frame index

.release_loop:
                test    ecx, ecx
                jz      .next_entry
                cmp     eax, MAX_PAGES
                jae     .next_entry
                push    eax
                push    ecx
                push    eax
                call    pmm_mark_free
                add     esp, 4
                pop     ecx
                pop     eax
                inc     eax
                dec     ecx
                jmp     .release_loop

.next_entry:
                add     edi, E820_ENTRY_SIZE
                pop     ecx
                dec     ecx
                jnz     .entry_loop
                jmp     .have_regions

; ---- no E820: fall back to the numbers INT 12h/15h gave us ----------
.no_map:
                mov     eax, [esi + BI_HIGHMEM_KB]
                test    eax, eax
                jnz     .have_high
                mov     eax, 15 * 1024          ; assume a modest 16 MiB
.have_high:
                shr     eax, 2                  ; KiB -> pages
                mov     ecx, eax
                mov     eax, 0x00100000 >> PAGE_SHIFT
.fallback_loop:
                test    ecx, ecx
                jz      .have_regions
                cmp     eax, MAX_PAGES
                jae     .have_regions
                push    eax
                push    ecx
                push    eax
                call    pmm_mark_free
                add     esp, 4
                pop     ecx
                pop     eax
                inc     eax
                dec     ecx
                jmp     .fallback_loop

; ---------------------------------------------------------------------
.have_regions:
                ; ---- reserve the first megabyte ----------------------
                xor     ebx, ebx
.low_loop:
                push    ebx
                call    pmm_mark_used
                add     esp, 4
                inc     ebx
                cmp     ebx, 0x00100000 >> PAGE_SHIFT
                jb      .low_loop

                ; ---- reserve the kernel image ------------------------
                mov     ebx, KERNEL_PHYS_BASE >> PAGE_SHIFT
                mov     eax, __kernel_end
                add     eax, PAGE_SIZE - 1
                shr     eax, PAGE_SHIFT
                mov     ecx, eax
.kernel_loop:
                cmp     ebx, ecx
                jae     .kernel_done
                push    ecx
                push    ebx
                push    ebx
                call    pmm_mark_used
                add     esp, 4
                pop     ebx
                pop     ecx
                inc     ebx
                jmp     .kernel_loop
.kernel_done:

                ; ---- reserve the bitmap itself -----------------------
                mov     ebx, bitmap
                shr     ebx, PAGE_SHIFT
                mov     ecx, bitmap + BITMAP_BYTES + PAGE_SIZE - 1
                shr     ecx, PAGE_SHIFT
.bitmap_loop:
                cmp     ebx, ecx
                jae     .bitmap_done
                push    ecx
                push    ebx
                push    ebx
                call    pmm_mark_used
                add     esp, 4
                pop     ebx
                pop     ecx
                inc     ebx
                jmp     .bitmap_loop
.bitmap_done:

                mov     eax, [pmm_total_pages]
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pmm_mark_free(frame) — release one frame into the pool.
; ---------------------------------------------------------------------
pmm_mark_free:
                push    ebp
                mov     ebp, esp
                push    ebx
                mov     eax, [ebp + 8]
                cmp     eax, MAX_PAGES
                jae     .done

                mov     ebx, eax
                shr     ebx, 3                  ; byte index
                mov     ecx, eax
                and     ecx, 7                  ; bit within the byte
                mov     dl, 1
                shl     dl, cl

                test    byte [bitmap + ebx], dl
                jz      .done                   ; already free
                not     dl
                and     byte [bitmap + ebx], dl
                inc     dword [pmm_total_pages]
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pmm_mark_used(frame)
; ---------------------------------------------------------------------
pmm_mark_used:
                push    ebp
                mov     ebp, esp
                push    ebx
                mov     eax, [ebp + 8]
                cmp     eax, MAX_PAGES
                jae     .done

                mov     ebx, eax
                shr     ebx, 3
                mov     ecx, eax
                and     ecx, 7
                mov     dl, 1
                shl     dl, cl

                test    byte [bitmap + ebx], dl
                jnz     .done                   ; already taken
                or      byte [bitmap + ebx], dl
                inc     dword [pmm_used_pages]
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pmm_is_free(frame) -> EAX = 1 when the frame is available
; ---------------------------------------------------------------------
pmm_is_free:
                push    ebp
                mov     ebp, esp
                push    ebx
                mov     eax, [ebp + 8]
                cmp     eax, MAX_PAGES
                jae     .no
                mov     ebx, eax
                shr     ebx, 3
                mov     ecx, eax
                and     ecx, 7
                mov     dl, 1
                shl     dl, cl
                test    byte [bitmap + ebx], dl
                jnz     .no
                mov     eax, 1
                jmp     .done
.no:
                xor     eax, eax
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pmm_alloc_page -> EAX = physical address, or 0 when out of memory
; ---------------------------------------------------------------------
pmm_alloc_page:
                push    ebx
                push    esi

                mov     esi, [alloc_hint]
                xor     ecx, ecx                ; how many bytes scanned
.scan:
                movzx   edx, byte [bitmap + esi]
                cmp     edx, 0xFF
                je      .next_byte

                ; invert so that free frames show up as set bits, then
                ; bsf gives us the lowest one directly
                not     edx
                and     edx, 0xFF
                bsf     ebx, edx                ; ebx = bit index

                mov     eax, 1
                push    ecx
                mov     ecx, ebx
                shl     eax, cl
                pop     ecx

                or      [bitmap + esi], al
                inc     dword [pmm_used_pages]
                mov     [alloc_hint], esi

                mov     eax, esi
                shl     eax, 3
                add     eax, ebx                ; frame number
                shl     eax, PAGE_SHIFT         ; -> physical address

                pop     esi
                pop     ebx
                ret

.next_byte:
                inc     esi
                cmp     esi, BITMAP_BYTES
                jb      .keep_going
                xor     esi, esi                ; wrap around
.keep_going:
                inc     ecx
                cmp     ecx, BITMAP_BYTES
                jb      .scan

                xor     eax, eax                ; nothing available
                pop     esi
                pop     ebx
                ret

; ---------------------------------------------------------------------
; pmm_alloc_pages(count) -> EAX = base address of a contiguous run
; ---------------------------------------------------------------------
pmm_alloc_pages:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     edi, [ebp + 8]
                cmp     edi, 1
                jbe     .single

                xor     esi, esi                ; candidate start frame
.search:
                mov     eax, esi
                add     eax, edi
                cmp     eax, MAX_PAGES
                ja      .fail

                xor     ecx, ecx                ; matched so far
.check:
                cmp     ecx, edi
                jae     .found

                mov     eax, esi
                add     eax, ecx
                push    ecx
                push    eax
                call    pmm_is_free
                add     esp, 4
                pop     ecx
                test    eax, eax
                jz      .advance

                inc     ecx
                jmp     .check

.advance:
                add     esi, ecx
                inc     esi
                jmp     .search

.found:
                xor     ecx, ecx
.claim:
                cmp     ecx, edi
                jae     .claimed
                mov     eax, esi
                add     eax, ecx
                push    ecx
                push    eax
                call    pmm_mark_used
                add     esp, 4
                pop     ecx
                inc     ecx
                jmp     .claim
.claimed:
                mov     eax, esi
                shl     eax, PAGE_SHIFT
                jmp     .done

.single:
                call    pmm_alloc_page
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
; pmm_free_page(physical_address)
; ---------------------------------------------------------------------
pmm_free_page:
                push    ebp
                mov     ebp, esp
                push    ebx
                mov     eax, [ebp + 8]
                shr     eax, PAGE_SHIFT
                cmp     eax, MAX_PAGES
                jae     .done

                mov     ebx, eax
                shr     ebx, 3
                mov     ecx, eax
                and     ecx, 7
                mov     dl, 1
                shl     dl, cl

                test    byte [bitmap + ebx], dl
                jz      .done                   ; double free, ignore
                not     dl
                and     byte [bitmap + ebx], dl
                dec     dword [pmm_used_pages]

                ; restart future searches near the freed frame
                mov     [alloc_hint], ebx
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pmm_free_pages(address, count)
; ---------------------------------------------------------------------
pmm_free_pages:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                mov     esi, [ebp + 8]
                mov     ebx, [ebp + 12]
.loop:
                test    ebx, ebx
                jz      .done
                push    esi
                call    pmm_free_page
                add     esp, 4
                add     esi, PAGE_SIZE
                dec     ebx
                jmp     .loop
.done:
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pmm_free_pages_count -> EAX
; ---------------------------------------------------------------------
pmm_free_pages_count:
                mov     eax, [pmm_total_pages]
                sub     eax, [pmm_used_pages]
                ret

; ---------------------------------------------------------------------
; pmm_dump_map(bootinfo) — print the memory map for the user.
; ---------------------------------------------------------------------
pmm_dump_map:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     esi, [ebp + 8]
                mov     ecx, [esi + BI_E820_COUNT]
                test    ecx, ecx
                jz      .none
                mov     edi, [esi + BI_E820_ADDR]

                push    dword hdr_map
                call    kprintf
                add     esp, 4

.loop:
                push    ecx

                mov     eax, [edi + E820_TYPE]
                cmp     eax, 5
                jbe     .type_ok
                mov     eax, 0
.type_ok:
                mov     ebx, [type_names + eax * 4]

                ; length in KiB, taking the high dword into account
                mov     eax, [edi + E820_LENGTH]
                mov     edx, [edi + E820_LENGTH + 4]
                shrd    eax, edx, 10            ; (edx:eax) >> 10

                push    ebx                     ; type name
                push    eax                     ; length in KiB
                push    dword [edi + E820_BASE] ; base low
                push    dword [edi + E820_BASE + 4] ; base high
                push    dword fmt_entry
                call    kprintf
                add     esp, 20

                add     edi, E820_ENTRY_SIZE
                pop     ecx
                dec     ecx
                jnz     .loop
                jmp     .done

.none:
                push    dword msg_nomap
                call    kprintf
                add     esp, 4
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
hdr_map:        db      "  base               length         type", 10, 0
fmt_entry:      db      "  %08x%08x  %10u KiB  %s", 10, 0
msg_nomap:      db      "  (no E820 map available)", 10, 0

t_unknown:      db      "unknown", 0
t_usable:       db      "usable", 0
t_reserved:     db      "reserved", 0
t_acpi_rec:     db      "ACPI reclaim", 0
t_acpi_nvs:     db      "ACPI NVS", 0
t_bad:          db      "bad", 0

                align   4
type_names:     dd      t_unknown, t_usable, t_reserved
                dd      t_acpi_rec, t_acpi_nvs, t_bad

                section .data
alloc_hint:     dd      0

                section .bss
                alignb  4
pmm_total_pages:    resd 1
pmm_used_pages:     resd 1
pmm_highest_addr:   resd 1

                alignb  4096
bitmap:             resb BITMAP_BYTES
pmm_bitmap_base:    resd 1
