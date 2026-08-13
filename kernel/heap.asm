; =====================================================================
;  Jino-OS  ::  heap.asm — kernel heap allocator
; ---------------------------------------------------------------------
;  A first-fit free list with boundary tags.  Blocks carry a header
;  holding their size, a used flag and links to their neighbours, which
;  makes coalescing on free straightforward.
;
;      struct block {
;          u32 magic;      // guards against corruption
;          u32 size;       // payload bytes
;          u32 used;       // 0 = free, 1 = allocated
;          block *next;    // address ordered
;          block *prev;
;      };
; =====================================================================

                bits    32
%include "kernel.inc"

                global  heap_init
                global  kmalloc
                global  kfree
                global  krealloc
                global  kcalloc
                global  heap_used
                global  heap_total
                global  heap_free_bytes
                global  heap_block_count
                global  heap_validate
                global  heap_dump

                extern  memset
                extern  memcpy
                extern  kprintf
                extern  panic

BLOCK_MAGIC     equ     0x4A484E4B              ; 'JHNK'
HEADER_SIZE     equ     20
MIN_PAYLOAD     equ     16
HEAP_SIZE       equ     1024 * 1024             ; 1 MiB of kernel heap

; header field offsets
H_MAGIC         equ     0
H_SIZE          equ     4
H_USED          equ     8
H_NEXT          equ     12
H_PREV          equ     16

                section .text

; ---------------------------------------------------------------------
; heap_init — one big free block covering the whole arena.
; ---------------------------------------------------------------------
heap_init:
                push    ebp
                mov     ebp, esp

                mov     eax, heap_area
                mov     [heap_start], eax
                mov     [free_list], eax

                mov     dword [eax + H_MAGIC], BLOCK_MAGIC
                mov     dword [eax + H_SIZE], HEAP_SIZE - HEADER_SIZE
                mov     dword [eax + H_USED], 0
                mov     dword [eax + H_NEXT], 0
                mov     dword [eax + H_PREV], 0

                mov     dword [heap_total], HEAP_SIZE
                mov     dword [heap_used], 0
                mov     dword [heap_block_count], 1

                pop     ebp
                ret

; ---------------------------------------------------------------------
; kmalloc(size) -> EAX = pointer, or 0 when the heap is exhausted
; ---------------------------------------------------------------------
kmalloc:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     ecx, [ebp + 8]
                test    ecx, ecx
                jz      .fail

                ; round the request up to an 8 byte boundary
                add     ecx, 7
                and     ecx, ~7
                cmp     ecx, MIN_PAYLOAD
                jae     .size_ok
                mov     ecx, MIN_PAYLOAD
.size_ok:
                mov     [req_size], ecx

                ; ---- first fit ---------------------------------------
                mov     esi, [free_list]
.search:
                test    esi, esi
                jz      .fail

                cmp     dword [esi + H_MAGIC], BLOCK_MAGIC
                jne     .corrupt

                cmp     dword [esi + H_USED], 0
                jne     .next
                mov     eax, [esi + H_SIZE]
                cmp     eax, ecx
                jae     .found
.next:
                mov     esi, [esi + H_NEXT]
                jmp     .search

.found:
                ; big enough to split off a new free block?
                mov     eax, [esi + H_SIZE]
                sub     eax, ecx                ; leftover bytes
                cmp     eax, HEADER_SIZE + MIN_PAYLOAD
                jb      .no_split

                ; ---- split -------------------------------------------
                lea     edi, [esi + HEADER_SIZE]
                add     edi, ecx                ; the new header sits here

                sub     eax, HEADER_SIZE        ; payload of the remainder
                mov     dword [edi + H_MAGIC], BLOCK_MAGIC
                mov     [edi + H_SIZE], eax
                mov     dword [edi + H_USED], 0

                mov     edx, [esi + H_NEXT]
                mov     [edi + H_NEXT], edx
                mov     [edi + H_PREV], esi
                test    edx, edx
                jz      .no_successor
                mov     [edx + H_PREV], edi
.no_successor:
                mov     [esi + H_NEXT], edi
                mov     [esi + H_SIZE], ecx
                inc     dword [heap_block_count]

.no_split:
                mov     dword [esi + H_USED], 1
                mov     eax, [esi + H_SIZE]
                add     [heap_used], eax

                lea     eax, [esi + HEADER_SIZE]
                jmp     .done

.corrupt:
                push    dword msg_corrupt
                call    panic
                add     esp, 4
.fail:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kcalloc(count, size) -> zeroed memory
; ---------------------------------------------------------------------
kcalloc:
                push    ebp
                mov     ebp, esp
                push    ebx

                mov     eax, [ebp + 8]
                mov     ecx, [ebp + 12]
                mul     ecx
                test    edx, edx                ; overflow?
                jnz     .fail
                mov     ebx, eax

                push    eax
                call    kmalloc
                add     esp, 4
                test    eax, eax
                jz      .done

                push    eax
                push    ebx
                push    dword 0
                push    eax
                call    memset
                add     esp, 12
                pop     eax
                jmp     .done
.fail:
                xor     eax, eax
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; kfree(pointer) — releases and merges with any free neighbour.
; ---------------------------------------------------------------------
kfree:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi

                mov     esi, [ebp + 8]
                test    esi, esi
                jz      .done

                sub     esi, HEADER_SIZE        ; back to the header

                cmp     dword [esi + H_MAGIC], BLOCK_MAGIC
                jne     .bad_pointer
                cmp     dword [esi + H_USED], 0
                je      .double_free

                mov     eax, [esi + H_SIZE]
                sub     [heap_used], eax
                mov     dword [esi + H_USED], 0

                ; ---- merge with the following block ------------------
                mov     ebx, [esi + H_NEXT]
                test    ebx, ebx
                jz      .try_prev
                cmp     dword [ebx + H_USED], 0
                jne     .try_prev

                mov     eax, [ebx + H_SIZE]
                add     eax, HEADER_SIZE
                add     [esi + H_SIZE], eax

                mov     edx, [ebx + H_NEXT]
                mov     [esi + H_NEXT], edx
                test    edx, edx
                jz      .no_next2
                mov     [edx + H_PREV], esi
.no_next2:
                mov     dword [ebx + H_MAGIC], 0
                dec     dword [heap_block_count]

.try_prev:
                ; ---- merge with the preceding block ------------------
                mov     ebx, [esi + H_PREV]
                test    ebx, ebx
                jz      .done
                cmp     dword [ebx + H_USED], 0
                jne     .done

                mov     eax, [esi + H_SIZE]
                add     eax, HEADER_SIZE
                add     [ebx + H_SIZE], eax

                mov     edx, [esi + H_NEXT]
                mov     [ebx + H_NEXT], edx
                test    edx, edx
                jz      .no_next3
                mov     [edx + H_PREV], ebx
.no_next3:
                mov     dword [esi + H_MAGIC], 0
                dec     dword [heap_block_count]
                jmp     .done

.bad_pointer:
                push    dword msg_badfree
                call    panic
                add     esp, 4
                jmp     .done
.double_free:
                push    dword msg_double
                call    panic
                add     esp, 4
.done:
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; krealloc(pointer, new_size) -> EAX
; ---------------------------------------------------------------------
krealloc:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     esi, [ebp + 8]
                mov     edi, [ebp + 12]

                test    esi, esi
                jnz     .have_ptr
                push    edi
                call    kmalloc
                add     esp, 4
                jmp     .done
.have_ptr:
                test    edi, edi
                jnz     .have_size
                push    esi
                call    kfree
                add     esp, 4
                xor     eax, eax
                jmp     .done
.have_size:
                mov     ebx, esi
                sub     ebx, HEADER_SIZE
                cmp     dword [ebx + H_MAGIC], BLOCK_MAGIC
                jne     .bad

                mov     eax, [ebx + H_SIZE]
                cmp     edi, eax
                jbe     .keep                   ; shrinking: reuse in place

                push    edi
                call    kmalloc
                add     esp, 4
                test    eax, eax
                jz      .done

                ; copy the old payload across
                push    eax
                mov     ecx, [ebx + H_SIZE]
                push    ecx
                push    esi
                push    eax
                call    memcpy
                add     esp, 12
                pop     eax

                push    eax
                push    esi
                call    kfree
                add     esp, 4
                pop     eax
                jmp     .done
.keep:
                mov     eax, esi
                jmp     .done
.bad:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; heap_free_bytes -> EAX
; ---------------------------------------------------------------------
heap_free_bytes:
                mov     eax, [heap_total]
                sub     eax, [heap_used]
                ret

; ---------------------------------------------------------------------
; heap_validate -> EAX = 1 when every block looks sane
; ---------------------------------------------------------------------
heap_validate:
                push    esi
                push    ebx
                mov     esi, [heap_start]
                xor     ebx, ebx                ; block counter
.loop:
                test    esi, esi
                jz      .ok
                cmp     dword [esi + H_MAGIC], BLOCK_MAGIC
                jne     .bad
                inc     ebx
                cmp     ebx, 100000             ; loop guard
                ja      .bad
                mov     esi, [esi + H_NEXT]
                jmp     .loop
.ok:
                mov     eax, 1
                jmp     .done
.bad:
                xor     eax, eax
.done:
                pop     ebx
                pop     esi
                ret

; ---------------------------------------------------------------------
; heap_dump — list every block
; ---------------------------------------------------------------------
heap_dump:
                push    ebp
                mov     ebp, esp
                push    esi
                push    ebx

                push    dword hdr_heap
                call    kprintf
                add     esp, 4

                mov     esi, [heap_start]
                xor     ebx, ebx
.loop:
                test    esi, esi
                jz      .done
                cmp     ebx, 32                 ; keep the output readable
                jae     .truncated

                mov     eax, [esi + H_USED]
                test    eax, eax
                jz      .free_block
                mov     edx, str_used
                jmp     .print
.free_block:
                mov     edx, str_free
.print:
                push    edx
                push    dword [esi + H_SIZE]
                lea     eax, [esi + HEADER_SIZE]
                push    eax
                push    ebx
                push    dword fmt_block
                call    kprintf
                add     esp, 20

                inc     ebx
                mov     esi, [esi + H_NEXT]
                jmp     .loop
.truncated:
                push    dword msg_more
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
msg_corrupt:    db      "heap: block header corrupted", 0
msg_badfree:    db      "heap: kfree() on an invalid pointer", 0
msg_double:     db      "heap: double free detected", 0
hdr_heap:       db      "  #   address     size      state", 10, 0
fmt_block:      db      "  %-3u 0x%08x  %8u  %s", 10, 0
msg_more:       db      "  ...", 10, 0
str_used:       db      "used", 0
str_free:       db      "free", 0

                section .bss
                alignb  4
heap_start:         resd 1
free_list:          resd 1
heap_used:          resd 1
heap_total:         resd 1
heap_block_count:   resd 1
req_size:           resd 1

                alignb  4096
heap_area:          resb HEAP_SIZE
