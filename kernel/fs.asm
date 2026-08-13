; =====================================================================
;  Jino-OS  ::  fs.asm — JinoFS, a small on-disk filesystem
; ---------------------------------------------------------------------
;  The layout is deliberately flat: one superblock, one fixed size
;  directory, and a data area handed out in whole sectors.  Files are
;  stored contiguously, which keeps reads to a single ATA request and
;  removes any need for an allocation map on disk — the directory is
;  the allocation map.
;
;      LBA 256       superblock
;      LBA 257..260  directory, 64 entries of 32 bytes
;      LBA 261..     data area
;
;  The volume starts at LBA 256 to stay clear of the boot sectors and
;  the kernel image, which grow from the front of the disk.  mkimage.py
;  enforces that gap, so a kernel that grows into the filesystem fails
;  the build rather than corrupting itself at run time.
;
;      struct entry {              // 32 bytes
;          char name[16];          // NUL padded
;          u32  size;              // payload bytes
;          u32  start;             // absolute LBA of the first sector
;          u32  sectors;           // sectors reserved for it
;          u32  flags;             // 1 = in use
;      };
;
;  The whole directory is cached in memory while mounted and written
;  back after any change, so a command never leaves the on-disk copy
;  half updated.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  fs_init
                global  fs_format
                global  fs_mounted
                global  fs_create
                global  fs_read
                global  fs_delete
                global  fs_find
                global  fs_list
                global  fs_file_count
                global  fs_used_sectors
                global  fs_free_sectors
                global  fs_print_info
                global  fs_max_file_size

                extern  ata_present
                extern  ata_read_sectors
                extern  ata_write_sectors
                extern  memset
                extern  memcpy
                extern  strlen
                extern  strcmp
                extern  strncpy
                extern  kprintf

FS_MAGIC        equ     0x3153464A              ; 'JFS1'
FS_VERSION      equ     1

FS_SUPER_LBA    equ     256
FS_DIR_LBA      equ     257
FS_DIR_SECTORS  equ     4
FS_DATA_LBA     equ     261
FS_DATA_SECTORS equ     512                     ; 256 KiB of file data

FS_MAX_FILES    equ     64
FS_ENTRY_SIZE   equ     32
FS_NAME_MAX     equ     16
FS_MAX_FILE     equ     8192                    ; 16 sectors per file

; entry field offsets
E_NAME          equ     0
E_SIZE          equ     16
E_START         equ     20
E_SECTORS       equ     24
E_FLAGS         equ     28

; superblock field offsets
S_MAGIC         equ     0
S_VERSION       equ     4
S_DIR_LBA       equ     8
S_DIR_SECTORS   equ     12
S_DATA_LBA      equ     16
S_DATA_SECTORS  equ     20
S_MAX_FILES     equ     24

                section .text

; ---------------------------------------------------------------------
; fs_init -> EAX = 1 when a formatted volume was mounted
;
;   A missing or unformatted disk is not an error; the shell simply
;   reports that there is nothing mounted and offers "format".
; ---------------------------------------------------------------------
fs_init:
                ENTER

                mov     dword [fs_mounted], 0

                cmp     dword [ata_present], 0
                je      .no

                CALL3   ata_read_sectors, FS_SUPER_LBA, 1, fs_super
                test    eax, eax
                jz      .no

                cmp     dword [fs_super + S_MAGIC], FS_MAGIC
                jne     .no
                cmp     dword [fs_super + S_VERSION], FS_VERSION
                jne     .no

                CALL3   ata_read_sectors, FS_DIR_LBA, FS_DIR_SECTORS, fs_dir
                test    eax, eax
                jz      .no

                mov     dword [fs_mounted], 1
                mov     eax, 1
                LEAVE_RET
.no:
                xor     eax, eax
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_format -> EAX = 1 on success
;
;   Lays down a fresh superblock and an empty directory.  Any previous
;   contents become unreachable, which is all this filesystem needs a
;   format to mean.
; ---------------------------------------------------------------------
fs_format:
                ENTER

                cmp     dword [ata_present], 0
                je      .fail

                CALL3   memset, fs_super, 0, 512
                mov     dword [fs_super + S_MAGIC], FS_MAGIC
                mov     dword [fs_super + S_VERSION], FS_VERSION
                mov     dword [fs_super + S_DIR_LBA], FS_DIR_LBA
                mov     dword [fs_super + S_DIR_SECTORS], FS_DIR_SECTORS
                mov     dword [fs_super + S_DATA_LBA], FS_DATA_LBA
                mov     dword [fs_super + S_DATA_SECTORS], FS_DATA_SECTORS
                mov     dword [fs_super + S_MAX_FILES], FS_MAX_FILES

                CALL3   ata_write_sectors, FS_SUPER_LBA, 1, fs_super
                test    eax, eax
                jz      .fail

                CALL3   memset, fs_dir, 0, FS_MAX_FILES * FS_ENTRY_SIZE
                call    fs_flush_dir
                test    eax, eax
                jz      .fail

                mov     dword [fs_mounted], 1
                mov     eax, 1
                LEAVE_RET
.fail:
                xor     eax, eax
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_flush_dir -> EAX = 1 on success   (internal)
; ---------------------------------------------------------------------
fs_flush_dir:
                ENTER
                CALL3   ata_write_sectors, FS_DIR_LBA, FS_DIR_SECTORS, fs_dir
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_find(name) -> EAX = entry pointer, or 0 when there is no such file
; ---------------------------------------------------------------------
fs_find:
                ENTER
                push    ebx
                push    esi

                cmp     dword [fs_mounted], 0
                je      .miss

                mov     esi, [ebp + 8]          ; the wanted name
                mov     ebx, fs_dir
                xor     ecx, ecx
.next:
                cmp     ecx, FS_MAX_FILES
                jae     .miss

                cmp     dword [ebx + E_FLAGS], 0
                je      .skip

                push    ecx
                CALL2   strcmp, ebx, esi
                pop     ecx
                test    eax, eax
                jz      .hit
.skip:
                add     ebx, FS_ENTRY_SIZE
                inc     ecx
                jmp     .next
.hit:
                mov     eax, ebx
                jmp     .done
.miss:
                xor     eax, eax
.done:
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_alloc_run(sectors) -> EAX = starting LBA, or 0 when there is no
;                          contiguous space left                (internal)
;
;   The in-use map is rebuilt from the directory on every call.  With 64
;   entries that is far cheaper than keeping a bitmap coherent on disk.
; ---------------------------------------------------------------------
fs_alloc_run:
                ENTER
                push    ebx
                push    esi
                push    edi

                mov     edi, [ebp + 8]          ; sectors wanted
                test    edi, edi
                jz      .fail
                cmp     edi, FS_DATA_SECTORS
                ja      .fail

                CALL3   memset, fs_usage, 0, FS_DATA_SECTORS

                ; mark every sector already claimed by a file
                mov     ebx, fs_dir
                xor     ecx, ecx
.mark:
                cmp     ecx, FS_MAX_FILES
                jae     .scan

                cmp     dword [ebx + E_FLAGS], 0
                je      .mark_next

                mov     esi, [ebx + E_START]
                sub     esi, FS_DATA_LBA        ; index into the data area
                mov     edx, [ebx + E_SECTORS]
.mark_one:
                test    edx, edx
                jz      .mark_next
                cmp     esi, FS_DATA_SECTORS
                jae     .mark_next
                mov     byte [fs_usage + esi], 1
                inc     esi
                dec     edx
                jmp     .mark_one
.mark_next:
                add     ebx, FS_ENTRY_SIZE
                inc     ecx
                jmp     .mark

                ; first fit: walk the map looking for a long enough gap
.scan:
                xor     esi, esi                ; candidate start
.try:
                mov     eax, esi
                add     eax, edi
                cmp     eax, FS_DATA_SECTORS
                ja      .fail

                xor     ecx, ecx
.probe:
                cmp     ecx, edi
                jae     .found
                mov     eax, esi
                add     eax, ecx
                cmp     byte [fs_usage + eax], 0
                jne     .busy
                inc     ecx
                jmp     .probe
.busy:
                ; skip past the sector that blocked us
                add     esi, ecx
                inc     esi
                jmp     .try
.found:
                mov     eax, esi
                add     eax, FS_DATA_LBA
                jmp     .done
.fail:
                xor     eax, eax
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_create(name, data, size) -> EAX = 1 on success
;
;   Writing over an existing name replaces it, so the space of the old
;   copy is released before the new one is placed.
; ---------------------------------------------------------------------
fs_create:
                ENTER
                push    ebx
                push    esi
                push    edi
                sub     esp, 8                  ; [ebp-20] start, [ebp-16] sectors

                cmp     dword [fs_mounted], 0
                je      .fail

                mov     eax, [ebp + 16]         ; size
                cmp     eax, FS_MAX_FILE
                ja      .fail

                ; a name has to fit the field, with room for the NUL
                CALL1   strlen, dword [ebp + 8]
                test    eax, eax
                jz      .fail
                cmp     eax, FS_NAME_MAX - 1
                ja      .fail

                ; replacing? drop the previous copy first
                CALL1   fs_find, dword [ebp + 8]
                test    eax, eax
                jz      .fresh
                mov     dword [eax + E_FLAGS], 0
.fresh:
                ; sectors = ceil(size / 512), at least one
                mov     eax, [ebp + 16]
                add     eax, 511
                shr     eax, 9
                test    eax, eax
                jnz     .have_count
                mov     eax, 1
.have_count:
                mov     [ebp - 16], eax

                CALL1   fs_alloc_run, eax
                test    eax, eax
                jz      .fail
                mov     [ebp - 20], eax

                ; find a free directory slot
                mov     ebx, fs_dir
                xor     ecx, ecx
.slot:
                cmp     ecx, FS_MAX_FILES
                jae     .fail
                cmp     dword [ebx + E_FLAGS], 0
                je      .got_slot
                add     ebx, FS_ENTRY_SIZE
                inc     ecx
                jmp     .slot
.got_slot:
                ; push the payload out one sector at a time, zero padding
                ; the tail so the last sector never leaks old contents
                mov     esi, [ebp + 12]         ; source
                mov     edi, [ebp + 16]         ; bytes left
                mov     edx, [ebp - 20]         ; target LBA
.write:
                test    edi, edi
                jz      .stored

                push    edx
                CALL3   memset, fs_io, 0, 512
                pop     edx

                mov     ecx, edi
                cmp     ecx, 512
                jbe     .chunk
                mov     ecx, 512
.chunk:
                push    edx
                push    ecx
                CALL3   memcpy, fs_io, esi, ecx
                pop     ecx
                pop     edx

                push    edx
                push    ecx
                CALL3   ata_write_sectors, edx, 1, fs_io
                pop     ecx
                pop     edx
                test    eax, eax
                jz      .fail

                add     esi, ecx
                sub     edi, ecx
                inc     edx
                jmp     .write
.stored:
                ; the directory entry goes in last, so a failed write
                ; never leaves a file that cannot be read back
                CALL3   strncpy, ebx, dword [ebp + 8], FS_NAME_MAX
                mov     eax, [ebp + 16]
                mov     [ebx + E_SIZE], eax
                mov     eax, [ebp - 20]
                mov     [ebx + E_START], eax
                mov     eax, [ebp - 16]
                mov     [ebx + E_SECTORS], eax
                mov     dword [ebx + E_FLAGS], 1

                call    fs_flush_dir
                test    eax, eax
                jz      .fail

                mov     eax, 1
                jmp     .done
.fail:
                xor     eax, eax
.done:
                add     esp, 8
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_read(name, buffer, maxlen) -> EAX = bytes delivered, or -1 when
;                                  there is no such file
; ---------------------------------------------------------------------
fs_read:
                ENTER
                push    ebx
                push    esi
                push    edi

                CALL1   fs_find, dword [ebp + 8]
                test    eax, eax
                jz      .missing
                mov     ebx, eax

                mov     edi, [ebx + E_SIZE]
                cmp     edi, [ebp + 16]
                jbe     .fits
                mov     edi, [ebp + 16]         ; clamp to the buffer
.fits:
                test    edi, edi
                jz      .empty

                mov     esi, [ebp + 12]         ; destination
                mov     edx, [ebx + E_START]
                xor     ecx, ecx                ; bytes copied so far
.loop:
                cmp     ecx, edi
                jae     .done_ok

                push    ecx
                push    edx
                CALL3   ata_read_sectors, edx, 1, fs_io
                pop     edx
                pop     ecx
                test    eax, eax
                jz      .failed

                mov     eax, edi
                sub     eax, ecx                ; bytes still wanted
                cmp     eax, 512
                jbe     .last
                mov     eax, 512
.last:
                push    ecx
                push    edx
                push    eax
                mov     ebx, esi
                add     ebx, ecx                ; destination cursor
                CALL3   memcpy, ebx, fs_io, eax
                pop     eax
                pop     edx
                pop     ecx

                add     ecx, eax
                inc     edx
                jmp     .loop
.done_ok:
                mov     eax, edi
                jmp     .done
.empty:
                xor     eax, eax
                jmp     .done
.failed:
                mov     eax, -1
                jmp     .done
.missing:
                mov     eax, -1
.done:
                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_delete(name) -> EAX = 1 when a file was removed
; ---------------------------------------------------------------------
fs_delete:
                ENTER

                CALL1   fs_find, dword [ebp + 8]
                test    eax, eax
                jz      .miss

                mov     dword [eax + E_FLAGS], 0
                call    fs_flush_dir
                test    eax, eax
                jz      .miss

                mov     eax, 1
                LEAVE_RET
.miss:
                xor     eax, eax
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_file_count -> EAX = number of files currently stored
; ---------------------------------------------------------------------
fs_file_count:
                push    ebx
                xor     eax, eax
                mov     ebx, fs_dir
                xor     ecx, ecx
.next:
                cmp     ecx, FS_MAX_FILES
                jae     .done
                cmp     dword [ebx + E_FLAGS], 0
                je      .skip
                inc     eax
.skip:
                add     ebx, FS_ENTRY_SIZE
                inc     ecx
                jmp     .next
.done:
                pop     ebx
                ret

; ---------------------------------------------------------------------
; fs_used_sectors -> EAX = sectors held by files
; ---------------------------------------------------------------------
fs_used_sectors:
                push    ebx
                xor     eax, eax
                mov     ebx, fs_dir
                xor     ecx, ecx
.next:
                cmp     ecx, FS_MAX_FILES
                jae     .done
                cmp     dword [ebx + E_FLAGS], 0
                je      .skip
                add     eax, [ebx + E_SECTORS]
.skip:
                add     ebx, FS_ENTRY_SIZE
                inc     ecx
                jmp     .next
.done:
                pop     ebx
                ret

; ---------------------------------------------------------------------
; fs_free_sectors -> EAX = sectors still available
; ---------------------------------------------------------------------
fs_free_sectors:
                call    fs_used_sectors
                mov     edx, FS_DATA_SECTORS
                sub     edx, eax
                mov     eax, edx
                ret

; ---------------------------------------------------------------------
; fs_max_file_size -> EAX = the largest file this volume accepts
; ---------------------------------------------------------------------
fs_max_file_size:
                mov     eax, FS_MAX_FILE
                ret

; ---------------------------------------------------------------------
; fs_list — print the directory
; ---------------------------------------------------------------------
fs_list:
                ENTER
                push    ebx
                push    esi

                cmp     dword [fs_mounted], 0
                je      .unmounted

                call    fs_file_count
                test    eax, eax
                jz      .empty

                CALL1   kprintf, hdr_list

                mov     ebx, fs_dir
                xor     esi, esi
.next:
                cmp     esi, FS_MAX_FILES
                jae     .total

                cmp     dword [ebx + E_FLAGS], 0
                je      .skip

                push    dword [ebx + E_START]
                push    dword [ebx + E_SIZE]
                push    ebx                     ; the name is at offset 0
                push    dword fmt_list
                call    kprintf
                add     esp, 16
.skip:
                add     ebx, FS_ENTRY_SIZE
                inc     esi
                jmp     .next
.total:
                call    fs_file_count
                CALL2   kprintf, fmt_total, eax
                jmp     .done
.empty:
                CALL1   kprintf, msg_empty
                jmp     .done
.unmounted:
                CALL1   kprintf, msg_unmounted
.done:
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; fs_print_info — a one line summary for the boot banner and "df"
; ---------------------------------------------------------------------
fs_print_info:
                ENTER
                push    ebx
                push    esi

                cmp     dword [fs_mounted], 0
                je      .unmounted

                call    fs_file_count
                mov     ebx, eax
                call    fs_used_sectors
                shl     eax, 9
                mov     esi, eax
                call    fs_free_sectors
                shl     eax, 9

                push    eax                     ; free bytes
                push    esi                     ; used bytes
                push    ebx                     ; files
                push    dword fmt_info
                call    kprintf
                add     esp, 16
                jmp     .done
.unmounted:
                CALL1   kprintf, msg_unmounted
.done:
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
                section .rodata
hdr_list:       db      "  name              size   lba", 10, 0
fmt_list:       db      "  %-16s%6u   %u", 10, 0
fmt_total:      db      "%u file(s)", 10, 0
fmt_info:       db      "jinofs: %u file(s), %u bytes used, %u bytes free", 10, 0
msg_empty:      db      "no files", 10, 0
msg_unmounted:  db      "no filesystem mounted (try: format)", 10, 0

                section .bss
                alignb  4
fs_mounted:     resd    1
fs_super:       resb    512
fs_dir:         resb    FS_MAX_FILES * FS_ENTRY_SIZE
fs_usage:       resb    FS_DATA_SECTORS
                alignb  4
fs_io:          resb    512
