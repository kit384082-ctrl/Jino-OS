; =====================================================================
;  Jino-OS  ::  shell.asm — the interactive command interpreter
; =====================================================================

                bits    32
%include "kernel.inc"

                global  shell_run
                global  shell_execute

                extern  kprintf
                extern  kputs
                extern  vga_clear
                extern  vga_set_color
                extern  vga_get_color
                extern  keyboard_readline
                extern  strcmp
                extern  strncmp
                extern  strlen
                extern  strtok_r
                extern  atoi
                extern  memset
                extern  memcpy

                extern  pmm_total_pages
                extern  pmm_used_pages
                extern  pmm_free_pages_count
                extern  pmm_alloc_page
                extern  pmm_free_page
                extern  pmm_dump_map
                extern  heap_used
                extern  heap_total
                extern  heap_dump
                extern  heap_validate
                extern  kmalloc
                extern  kfree
                extern  pit_ticks
                extern  pit_uptime_ms
                extern  pit_uptime_seconds
                extern  pit_sleep_ms
                extern  rtc_format
                extern  cpu_print_info
                extern  cpu_vendor
                extern  ata_print_info
                extern  ata_present
                extern  ata_read_sectors
                extern  task_print
                extern  task_create
                extern  task_yield
                extern  task_reap
                extern  task_set_preemption
                extern  fs_init
                extern  fs_format
                extern  fs_mounted
                extern  fs_create
                extern  fs_read
                extern  fs_delete
                extern  fs_list
                extern  fs_print_info
                extern  fs_max_file_size
                extern  user_enter
                extern  user_demo
                extern  user_faulter
                extern  user_syscall_count
                extern  syscall_count
                extern  syscall_rejected
                extern  paging_get_physical
                extern  paging_fault_count
                extern  paging_is_enabled
                extern  boot_info_ptr
                extern  panic

CMDLINE_MAX     equ     256
MAX_ARGS        equ     16
FILEBUF_MAX     equ     1024

                section .text

; ---------------------------------------------------------------------
; shell_run — the read/eval/print loop.  Does not return.
; ---------------------------------------------------------------------
shell_run:
                push    ebp
                mov     ebp, esp

                push    dword msg_welcome
                call    kprintf
                add     esp, 4

.loop:
                ; ---- prompt ------------------------------------------
                push    dword VGA_ATTR(COLOR_LGREEN, COLOR_BLACK)
                call    vga_set_color
                add     esp, 4

                push    dword prompt
                call    kprintf
                add     esp, 4

                push    dword VGA_ATTR(COLOR_LGREY, COLOR_BLACK)
                call    vga_set_color
                add     esp, 4

                ; ---- read --------------------------------------------
                push    dword CMDLINE_MAX
                push    dword cmdline
                call    keyboard_readline
                add     esp, 8

                test    eax, eax
                jz      .loop                   ; empty line

                ; ---- evaluate ----------------------------------------
                push    dword cmdline
                call    shell_execute
                add     esp, 4

                jmp     .loop

; ---------------------------------------------------------------------
; shell_execute(line) — split into argv and dispatch.
; ---------------------------------------------------------------------
shell_execute:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                ; ---- tokenise ----------------------------------------
                mov     dword [argc], 0
                mov     dword [saveptr], 0

                push    dword saveptr
                push    dword delims
                push    dword [ebp + 8]
                call    strtok_r
                add     esp, 12

.token_loop:
                test    eax, eax
                jz      .parsed
                mov     ecx, [argc]
                cmp     ecx, MAX_ARGS
                jae     .parsed
                mov     [argv + ecx * 4], eax
                inc     dword [argc]

                push    dword saveptr
                push    dword delims
                push    dword 0
                call    strtok_r
                add     esp, 12
                jmp     .token_loop

.parsed:
                cmp     dword [argc], 0
                je      .done

                ; ---- look the command up -----------------------------
                mov     esi, command_table
.search:
                mov     eax, [esi]              ; name pointer
                test    eax, eax
                jz      .unknown

                push    esi
                push    dword [argv]
                push    eax
                call    strcmp
                add     esp, 8
                pop     esi
                test    eax, eax
                jz      .found

                add     esi, 12                 ; name, handler, help
                jmp     .search

.found:
                mov     eax, [esi + 4]          ; handler
                call    eax
                jmp     .done

.unknown:
                push    dword [argv]
                push    dword fmt_unknown
                call    kprintf
                add     esp, 8
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; =====================================================================
;  Commands
; =====================================================================

; ---------------------------------------------------------------- help
;  With no argument the commands are listed by group, which fits the
;  25 line screen; "help <name>" describes a single command.
cmd_help:
                push    ebx
                push    esi

                cmp     dword [argc], 2
                jae     .one

                CALL1   kprintf, msg_help_header

                mov     esi, help_groups
.group:
                mov     eax, [esi]              ; group title
                test    eax, eax
                jz      .footer

                CALL2   kprintf, fmt_group, eax
                mov     ebx, [esi + 4]          ; NULL terminated name list
.name:
                mov     eax, [ebx]
                test    eax, eax
                jz      .group_done
                CALL2   kprintf, fmt_group_item, eax
                add     ebx, 4
                jmp     .name
.group_done:
                CALL1   kprintf, fmt_nl
                add     esi, 8
                jmp     .group
.footer:
                CALL1   kprintf, msg_help_footer
                jmp     .done

                ; help <name>
.one:
                mov     esi, command_table
.search:
                mov     eax, [esi]
                test    eax, eax
                jz      .unknown

                push    esi
                CALL2   strcmp, eax, dword [argv + 4]
                pop     esi
                test    eax, eax
                jz      .found

                add     esi, 12
                jmp     .search
.found:
                push    dword [esi + 8]         ; help text
                push    dword [esi]             ; name
                push    dword fmt_help
                call    kprintf
                add     esp, 12
                jmp     .done
.unknown:
                CALL2   kprintf, fmt_help_unknown, dword [argv + 4]
.done:
                pop     esi
                pop     ebx
                ret

; --------------------------------------------------------------- clear
cmd_clear:
                call    vga_clear
                ret

; ---------------------------------------------------------------- echo
cmd_echo:
                push    ebx
                mov     ebx, 1                  ; skip argv[0]
.loop:
                cmp     ebx, [argc]
                jae     .done
                push    dword [argv + ebx * 4]
                push    dword fmt_word
                call    kprintf
                add     esp, 8
                inc     ebx
                jmp     .loop
.done:
                push    dword fmt_nl
                call    kprintf
                add     esp, 4
                pop     ebx
                ret

; --------------------------------------------------------------- uname
cmd_uname:
                push    dword msg_uname
                call    kprintf
                add     esp, 4
                ret

; ---------------------------------------------------------------- mem
cmd_mem:
                push    ebx

                ; physical
                mov     eax, [pmm_total_pages]
                shl     eax, 2                  ; pages -> KiB
                mov     ebx, eax

                call    pmm_free_pages_count
                shl     eax, 2

                push    eax
                push    dword [pmm_used_pages]
                push    dword [pmm_total_pages]
                push    ebx
                push    dword fmt_mem_phys
                call    kprintf
                add     esp, 20

                ; heap
                mov     eax, [heap_total]
                sub     eax, [heap_used]
                push    eax
                push    dword [heap_used]
                push    dword [heap_total]
                push    dword fmt_mem_heap
                call    kprintf
                add     esp, 16

                ; paging
                call    paging_is_enabled
                test    eax, eax
                jz      .no_paging
                push    dword [paging_fault_count]
                push    dword msg_paging_on
                call    kprintf
                add     esp, 8
                jmp     .done
.no_paging:
                push    dword msg_paging_off
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                ret

; ------------------------------------------------------------ memmap
cmd_memmap:
                push    dword [boot_info_ptr]
                call    pmm_dump_map
                add     esp, 4
                ret

; -------------------------------------------------------------- heap
cmd_heap:
                call    heap_dump

                call    heap_validate
                test    eax, eax
                jz      .broken
                push    dword msg_heap_ok
                call    kprintf
                add     esp, 4
                ret
.broken:
                push    dword msg_heap_bad
                call    kprintf
                add     esp, 4
                ret

; --------------------------------------------------------------- cpu
cmd_cpu:
                call    cpu_print_info
                ret

; ------------------------------------------------------------ uptime
cmd_uptime:
                push    ebx
                call    pit_uptime_seconds
                mov     ebx, eax

                ; break it down into minutes and seconds
                xor     edx, edx
                mov     ecx, 60
                div     ecx                     ; eax = minutes, edx = secs

                push    dword [pit_ticks]
                push    edx
                push    eax
                push    ebx
                push    dword fmt_uptime
                call    kprintf
                add     esp, 20
                pop     ebx
                ret

; --------------------------------------------------------------- date
cmd_date:
                push    dword 64
                push    dword timebuf
                call    rtc_format
                add     esp, 8

                push    dword timebuf
                push    dword fmt_date
                call    kprintf
                add     esp, 8
                ret

; --------------------------------------------------------------- disk
cmd_disk:
                call    ata_print_info
                ret

; ------------------------------------------------------------ sectors
cmd_read:
                push    ebx
                push    esi

                cmp     dword [ata_present], 0
                je      .no_disk

                cmp     dword [argc], 2
                jb      .usage

                push    dword [argv + 4]
                call    atoi
                add     esp, 4
                mov     ebx, eax                ; the LBA

                push    dword sector_buffer
                push    dword 1
                push    ebx
                call    ata_read_sectors
                add     esp, 12
                test    eax, eax
                jz      .failed

                push    ebx
                push    dword fmt_sector
                call    kprintf
                add     esp, 8

                ; a 16 bytes per line hex dump
                xor     esi, esi
.line:
                cmp     esi, 512
                jae     .done

                push    esi
                push    dword fmt_offset
                call    kprintf
                add     esp, 8

                xor     ecx, ecx
.byte_loop:
                cmp     ecx, 16
                jae     .line_end
                push    ecx
                movzx   eax, byte [sector_buffer + esi + ecx]
                push    eax
                push    dword fmt_hexbyte
                call    kprintf
                add     esp, 8
                pop     ecx
                inc     ecx
                jmp     .byte_loop
.line_end:
                push    dword fmt_nl
                call    kprintf
                add     esp, 4

                add     esi, 16
                cmp     esi, 128                ; only show the first 128
                jb      .line
                push    dword msg_truncated
                call    kprintf
                add     esp, 4
                jmp     .done

.no_disk:
                push    dword msg_no_disk
                call    kprintf
                add     esp, 4
                jmp     .done
.usage:
                push    dword msg_read_usage
                call    kprintf
                add     esp, 4
                jmp     .done
.failed:
                push    dword msg_read_failed
                call    kprintf
                add     esp, 4
.done:
                pop     esi
                pop     ebx
                ret

; ---------------------------------------------------------------- ps
cmd_ps:
                call    task_print
                ret

; ------------------------------------------------------------- spawn
;  Create a worker task and let it run.  The worker counts up, yielding
;  between iterations, which exercises the context switch.
cmd_spawn:
                push    ebx

                push    dword worker_name
                push    dword worker_task
                call    task_create
                add     esp, 8

                cmp     eax, -1
                je      .failed

                push    eax
                push    dword fmt_spawned
                call    kprintf
                add     esp, 8

                ; hand the CPU over a few times so the new task runs
                mov     ebx, 8
.pump:
                call    task_yield
                dec     ebx
                jnz     .pump

                ; the worker has exited by now; release its stack
                call    task_reap
                jmp     .done
.failed:
                push    dword msg_spawn_failed
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                ret

; ------------------------------------------------------------ preempt
;  Prove that the scheduler can take the CPU away from a task that never
;  yields.  The spinner below only ever increments a counter; if the
;  timer interrupt is driving the scheduler, it still gets to run and
;  the shell still comes back.
cmd_preempt:
                push    ebx

                ; make the timer reschedule for us
                push    dword 1
                call    task_set_preemption
                add     esp, 4

                mov     dword [spin_counter], 0

                push    dword spinner_name
                push    dword spinner_task
                call    task_create
                add     esp, 8

                cmp     eax, -1
                je      .failed

                ; busy-wait in the shell: only preemption can let the
                ; spinner make progress
                mov     ebx, 400000
.wait:
                dec     ebx
                jnz     .wait

                push    dword [spin_counter]
                push    dword fmt_preempt
                call    kprintf
                add     esp, 8

                ; stop the spinner and go back to cooperative scheduling
                mov     dword [spin_stop], 1
                call    task_yield

                push    dword 0
                call    task_set_preemption
                add     esp, 4
                call    task_reap
                jmp     .done
.failed:
                push    dword msg_spawn_failed
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                ret

; A task that never yields: it just counts until it is told to stop.
spinner_task:
.loop:
                inc     dword [spin_counter]
                cmp     dword [spin_stop], 0
                je      .loop
                mov     dword [spin_stop], 0
                xor     eax, eax
                ret

; --------------------------------------------------------------- user
;  Run the sample program in ring 3 and report how it got on.
cmd_user:
                push    ebx

                mov     ebx, user_demo
                cmp     dword [argc], 2
                jb      .go
                CALL2   strcmp, dword [argv + 4], c_fault_arg
                test    eax, eax
                jnz     .go
                mov     ebx, user_faulter
.go:
                CALL1   kprintf, msg_entering

                push    ebx
                call    user_enter
                add     esp, 4

                push    eax
                push    dword fmt_user_exit
                call    kprintf
                add     esp, 8

                push    dword [syscall_rejected]
                push    dword [syscall_count]
                push    dword fmt_syscalls
                call    kprintf
                add     esp, 12

                pop     ebx
                ret

; ----------------------------------------------------------------- ls
cmd_ls:
                call    fs_list
                ret

; ----------------------------------------------------------------- df
cmd_df:
                call    fs_print_info
                ret

; ------------------------------------------------------------- format
cmd_format:
                cmp     dword [ata_present], 0
                je      .no_disk

                CALL1   kprintf, msg_formatting
                call    fs_format
                test    eax, eax
                jz      .failed

                CALL1   kprintf, msg_formatted
                ret
.failed:
                CALL1   kprintf, msg_format_failed
                ret
.no_disk:
                CALL1   kprintf, msg_no_disk
                ret

; -------------------------------------------------------------- write
;  write <name> <text...>
;
;  The remaining arguments are joined with single spaces, which is the
;  most useful reading of a command line for a plain text file.
cmd_write:
                push    ebx
                push    esi
                push    edi

                cmp     dword [fs_mounted], 0
                je      .unmounted
                cmp     dword [argc], 3
                jb      .usage

                mov     edi, filebuf            ; build the payload here
                mov     ebx, 2                  ; argv[2] onwards
.join:
                cmp     ebx, [argc]
                jae     .joined

                cmp     ebx, 2
                je      .copy
                mov     byte [edi], ' '         ; separator
                inc     edi
.copy:
                mov     esi, [argv + ebx * 4]
.chars:
                mov     al, [esi]
                test    al, al
                jz      .next_arg
                ; keep one byte spare for the trailing newline
                mov     ecx, edi
                sub     ecx, filebuf
                cmp     ecx, FILEBUF_MAX - 2
                jae     .joined
                mov     [edi], al
                inc     edi
                inc     esi
                jmp     .chars
.next_arg:
                inc     ebx
                jmp     .join
.joined:
                mov     byte [edi], 10          ; a text file ends in a newline
                inc     edi

                mov     ecx, edi
                sub     ecx, filebuf            ; payload length

                push    ecx
                push    dword filebuf
                push    dword [argv + 4]
                call    fs_create
                add     esp, 12
                test    eax, eax
                jz      .failed

                mov     ecx, edi
                sub     ecx, filebuf
                push    ecx
                push    dword [argv + 4]
                push    dword fmt_written
                call    kprintf
                add     esp, 12
                jmp     .done
.failed:
                CALL1   kprintf, msg_write_failed
                jmp     .done
.usage:
                CALL1   kprintf, msg_write_usage
                jmp     .done
.unmounted:
                CALL1   kprintf, msg_unmounted
.done:
                pop     edi
                pop     esi
                pop     ebx
                ret

; ---------------------------------------------------------------- cat
cmd_cat:
                push    ebx

                cmp     dword [fs_mounted], 0
                je      .unmounted
                cmp     dword [argc], 2
                jb      .usage

                push    dword FILEBUF_MAX - 1
                push    dword filebuf
                push    dword [argv + 4]
                call    fs_read
                add     esp, 12

                cmp     eax, -1
                je      .missing

                mov     ebx, eax
                mov     byte [filebuf + ebx], 0 ; terminate for %s
                CALL2   kprintf, fmt_word_raw, filebuf

                ; a file without a trailing newline would run into the
                ; prompt, so supply one
                test    ebx, ebx
                jz      .done
                cmp     byte [filebuf + ebx - 1], 10
                je      .done
                CALL1   kprintf, fmt_nl
                jmp     .done
.missing:
                CALL2   kprintf, fmt_no_file, dword [argv + 4]
                jmp     .done
.usage:
                CALL1   kprintf, msg_cat_usage
                jmp     .done
.unmounted:
                CALL1   kprintf, msg_unmounted
.done:
                pop     ebx
                ret

; ----------------------------------------------------------------- rm
cmd_rm:
                cmp     dword [fs_mounted], 0
                je      .unmounted
                cmp     dword [argc], 2
                jb      .usage

                CALL1   fs_delete, dword [argv + 4]
                test    eax, eax
                jz      .missing

                CALL2   kprintf, fmt_removed, dword [argv + 4]
                ret
.missing:
                CALL2   kprintf, fmt_no_file, dword [argv + 4]
                ret
.usage:
                CALL1   kprintf, msg_rm_usage
                ret
.unmounted:
                CALL1   kprintf, msg_unmounted
                ret

; The body of the spawned task: print a few lines and return, which
; sends it through task_exit.
worker_task:
                push    ebx
                mov     ebx, 3
.loop:
                push    ebx
                push    dword [worker_counter]
                push    dword fmt_worker
                call    kprintf
                add     esp, 8
                inc     dword [worker_counter]
                call    task_yield
                pop     ebx
                dec     ebx
                jnz     .loop
                pop     ebx
                xor     eax, eax
                ret

; -------------------------------------------------------------- alloc
cmd_alloc:
                push    ebx

                cmp     dword [argc], 2
                jb      .usage

                push    dword [argv + 4]
                call    atoi
                add     esp, 4
                test    eax, eax
                jz      .usage
                mov     ebx, eax

                push    ebx
                call    kmalloc
                add     esp, 4
                test    eax, eax
                jz      .failed

                mov     [last_alloc], eax
                push    eax
                push    ebx
                push    dword fmt_alloc
                call    kprintf
                add     esp, 12
                jmp     .done
.failed:
                push    dword msg_alloc_failed
                call    kprintf
                add     esp, 4
                jmp     .done
.usage:
                push    dword msg_alloc_usage
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                ret

; --------------------------------------------------------------- free
cmd_free:
                mov     eax, [last_alloc]
                test    eax, eax
                jz      .nothing

                push    eax
                call    kfree
                add     esp, 4

                push    dword [last_alloc]
                push    dword fmt_freed
                call    kprintf
                add     esp, 8
                mov     dword [last_alloc], 0
                ret
.nothing:
                push    dword msg_nothing_alloc
                call    kprintf
                add     esp, 4
                ret

; --------------------------------------------------------------- peek
cmd_peek:
                push    ebx
                cmp     dword [argc], 2
                jb      .usage

                push    dword [argv + 4]
                call    atoi
                add     esp, 4
                mov     ebx, eax

                mov     eax, [ebx]
                push    eax
                push    ebx
                push    dword fmt_peek
                call    kprintf
                add     esp, 12
                jmp     .done
.usage:
                push    dword msg_peek_usage
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                ret

; --------------------------------------------------------------- virt
cmd_virt:
                push    ebx
                cmp     dword [argc], 2
                jb      .usage

                push    dword [argv + 4]
                call    atoi
                add     esp, 4
                mov     ebx, eax

                push    ebx
                call    paging_get_physical
                add     esp, 4

                test    eax, eax
                jz      .unmapped

                push    eax
                push    ebx
                push    dword fmt_virt
                call    kprintf
                add     esp, 12
                jmp     .done
.unmapped:
                push    ebx
                push    dword fmt_unmapped
                call    kprintf
                add     esp, 8
                jmp     .done
.usage:
                push    dword msg_virt_usage
                call    kprintf
                add     esp, 4
.done:
                pop     ebx
                ret

; --------------------------------------------------------------- sleep
cmd_sleep:
                cmp     dword [argc], 2
                jb      .usage
                push    dword [argv + 4]
                call    atoi
                add     esp, 4
                push    eax
                call    pit_sleep_ms
                add     esp, 4
                ret
.usage:
                push    dword msg_sleep_usage
                call    kprintf
                add     esp, 4
                ret

; --------------------------------------------------------------- panic
cmd_panic:
                push    dword msg_manual_panic
                call    panic
                add     esp, 4
                ret

; --------------------------------------------------------------- crash
cmd_crash:
                ; deliberately trigger an exception so the handler and
                ; the register dump can be exercised
                xor     edx, edx
                xor     ecx, ecx
                mov     eax, 1
                div     ecx                     ; divide by zero
                ret

; -------------------------------------------------------------- colors
cmd_colors:
                push    ebx
                push    esi

                push    dword msg_colors
                call    kprintf
                add     esp, 4

                call    vga_get_color
                mov     esi, eax                ; remember it

                xor     ebx, ebx
.loop:
                cmp     ebx, 16
                jae     .done
                push    ebx
                call    vga_set_color
                add     esp, 4

                push    ebx
                push    dword fmt_color
                call    kprintf
                add     esp, 8

                inc     ebx
                jmp     .loop
.done:
                push    esi
                call    vga_set_color
                add     esp, 4
                push    dword fmt_nl
                call    kprintf
                add     esp, 4

                pop     esi
                pop     ebx
                ret

; --------------------------------------------------------------- about
cmd_about:
                push    dword msg_about
                call    kprintf
                add     esp, 4
                ret

; ---------------------------------------------------------------------
                section .rodata
prompt:         db      "jino> ", 0
delims:         db      " ", 9, 0

msg_welcome:    db      10, "Type 'help' for the list of commands.", 10, 10, 0
msg_help_header: db     "commands:", 10, 0
msg_help_footer: db     "type 'help <command>' for details", 10, 0
fmt_group:      db      "  %-10s", 0
fmt_group_item: db      "%s ", 0
fmt_help_unknown: db    "no such command: %s", 10, 0

g_system:       db      "system", 0
g_memory:       db      "memory", 0
g_files:        db      "files", 0
g_tasks:        db      "tasks", 0
g_debug:        db      "debug", 0
fmt_help:       db      "  %-10s %s", 10, 0
fmt_unknown:    db      "unknown command: %s (try 'help')", 10, 0
fmt_word:       db      "%s ", 0
fmt_nl:         db      10, 0

msg_uname:      db      "Jino-OS 1.0 i386 (assembly)", 10, 0

fmt_mem_phys:   db      "physical : %u KiB total, %u pages (%u used, %u KiB free)", 10, 0
fmt_mem_heap:   db      "heap     : %u bytes total, %u used, %u free", 10, 0
msg_paging_on:  db      "paging   : enabled, %u faults handled", 10, 0
msg_paging_off: db      "paging   : disabled", 10, 0

msg_heap_ok:    db      "heap is consistent", 10, 0
msg_heap_bad:   db      "heap is CORRUPTED", 10, 0

fmt_uptime:     db      "up %u seconds (%u min %u sec), %u timer ticks", 10, 0
fmt_date:       db      "%s UTC", 10, 0

fmt_sector:     db      "sector %u:", 10, 0
fmt_offset:     db      "  %04x  ", 0
fmt_hexbyte:    db      "%02x ", 0
msg_truncated:  db      "  ... (first 128 bytes shown)", 10, 0
msg_no_disk:    db      "no disk available", 10, 0
worker_name:    db      "worker", 0
fmt_spawned:    db      "spawned task %u", 10, 0
msg_spawn_failed: db    "could not create the task", 10, 0
fmt_worker:     db      "  worker running, iteration %u", 10, 0
msg_formatting: db      "creating a filesystem on ata0...", 10, 0
msg_formatted:  db      "filesystem ready", 10, 0
msg_format_failed: db   "format failed", 10, 0
msg_unmounted:  db      "no filesystem mounted (try: format)", 10, 0
msg_write_usage: db     "usage: write <name> <text...>", 10, 0
msg_cat_usage:  db      "usage: cat <name>", 10, 0
msg_rm_usage:   db      "usage: rm <name>", 10, 0
msg_write_failed: db    "write failed: the name may be too long or the disk full", 10, 0
fmt_written:    db      "wrote %s (%u bytes)", 10, 0
fmt_removed:    db      "removed %s", 10, 0
fmt_word_raw:   db      "%s", 0
fmt_no_file:    db      "no such file: %s", 10, 0
msg_entering:   db      "dropping to ring 3...", 10, 0
fmt_user_exit:  db      "back in ring 0, the program exited with %d", 10, 0
fmt_syscalls:   db      "%u system call(s), %u rejected", 10, 0
spinner_name:   db      "spinner", 0
fmt_preempt:    db      "preempted spinner reached %u iterations", 10, 0
msg_read_usage: db      "usage: read <lba>", 10, 0
msg_read_failed: db     "read failed", 10, 0

fmt_alloc:      db      "allocated %u bytes at 0x%08x", 10, 0
msg_alloc_usage: db     "usage: alloc <bytes>", 10, 0
msg_alloc_failed: db    "allocation failed", 10, 0
fmt_freed:      db      "freed 0x%08x", 10, 0
msg_nothing_alloc: db   "nothing to free", 10, 0

fmt_peek:       db      "[0x%08x] = 0x%08x", 10, 0
msg_peek_usage: db      "usage: peek <address>", 10, 0

fmt_virt:       db      "virtual 0x%08x -> physical 0x%08x", 10, 0
fmt_unmapped:   db      "virtual 0x%08x is not mapped", 10, 0
msg_virt_usage: db      "usage: virt <address>", 10, 0

msg_sleep_usage: db     "usage: sleep <milliseconds>", 10, 0
msg_manual_panic: db    "panic requested from the shell", 0

msg_colors:     db      "palette: ", 0
fmt_color:      db      "%x", 0

msg_about:      db      10, "  Jino-OS", 10 \
                     ,  "  A small x86 operating system written entirely in assembly.", 10 \
                     ,  "  Bootloader: two stage, real mode to protected mode.", 10 \
                     ,  "  Kernel: GDT, IDT, PIC, PIT, paging, heap, tasks, drivers.", 10, 10, 0

; ---- command names ---------------------------------------------------
c_help:     db "help", 0
c_clear:    db "clear", 0
c_echo:     db "echo", 0
c_uname:    db "uname", 0
c_mem:      db "mem", 0
c_memmap:   db "memmap", 0
c_heap:     db "heap", 0
c_cpu:      db "cpu", 0
c_uptime:   db "uptime", 0
c_date:     db "date", 0
c_disk:     db "disk", 0
c_read:     db "read", 0
c_ps:       db "ps", 0
c_spawn:    db "spawn", 0
c_preempt:  db "preempt", 0
c_ls:       db "ls", 0
c_cat:      db "cat", 0
c_write:    db "write", 0
c_rm:       db "rm", 0
c_format:   db "format", 0
c_df:       db "df", 0
c_user:     db "user", 0
c_fault_arg: db "fault", 0
c_alloc:    db "alloc", 0
c_free:     db "free", 0
c_peek:     db "peek", 0
c_virt:     db "virt", 0
c_sleep:    db "sleep", 0
c_colors:   db "colors", 0
c_about:    db "about", 0
c_panic:    db "panic", 0
c_crash:    db "crash", 0

; ---- help text -------------------------------------------------------
h_help:     db "show this list", 0
h_clear:    db "clear the screen", 0
h_echo:     db "print the arguments", 0
h_uname:    db "system identification", 0
h_mem:      db "memory statistics", 0
h_memmap:   db "BIOS memory map", 0
h_heap:     db "kernel heap blocks", 0
h_cpu:      db "processor information", 0
h_uptime:   db "time since boot", 0
h_date:     db "real time clock", 0
h_disk:     db "ATA drive information", 0
h_read:     db "hex dump a disk sector", 0
h_ps:       db "list kernel tasks", 0
h_spawn:    db "start a demo kernel task", 0
h_preempt:  db "demonstrate preemptive scheduling", 0
h_ls:       db "list the files on the disk", 0
h_cat:      db "print a file: cat <name>", 0
h_write:    db "store a file: write <name> <text>", 0
h_rm:       db "delete a file: rm <name>", 0
h_format:   db "create a fresh filesystem", 0
h_df:       db "filesystem usage", 0
h_user:     db "run a program in ring 3: user [fault]", 0
h_alloc:    db "allocate heap memory", 0
h_free:     db "release the last allocation", 0
h_peek:     db "read a memory address", 0
h_virt:     db "translate a virtual address", 0
h_sleep:    db "pause for milliseconds", 0
h_colors:   db "show the text palette", 0
h_about:    db "about this system", 0
h_panic:    db "trigger a kernel panic", 0
h_crash:    db "trigger a divide by zero", 0

                align   4
; The names shown under each heading by a bare "help".
                align   4
l_system:       dd c_help, c_clear, c_echo, c_uname, c_cpu, c_uptime
                dd c_date, c_colors, c_about, 0
l_memory:       dd c_mem, c_memmap, c_heap, c_alloc, c_free, c_peek, c_virt, 0
l_files:        dd c_ls, c_cat, c_write, c_rm, c_format, c_df, c_disk, c_read, 0
l_tasks:        dd c_ps, c_spawn, c_preempt, c_sleep, c_user, 0
l_debug:        dd c_panic, c_crash, 0

help_groups:
                dd g_system, l_system
                dd g_memory, l_memory
                dd g_files,  l_files
                dd g_tasks,  l_tasks
                dd g_debug,  l_debug
                dd 0, 0

command_table:
                dd c_help,   cmd_help,   h_help
                dd c_clear,  cmd_clear,  h_clear
                dd c_echo,   cmd_echo,   h_echo
                dd c_uname,  cmd_uname,  h_uname
                dd c_mem,    cmd_mem,    h_mem
                dd c_memmap, cmd_memmap, h_memmap
                dd c_heap,   cmd_heap,   h_heap
                dd c_cpu,    cmd_cpu,    h_cpu
                dd c_uptime, cmd_uptime, h_uptime
                dd c_date,   cmd_date,   h_date
                dd c_disk,   cmd_disk,   h_disk
                dd c_read,   cmd_read,   h_read
                dd c_ps,     cmd_ps,     h_ps
                dd c_spawn,  cmd_spawn,  h_spawn
                dd c_preempt, cmd_preempt, h_preempt
                dd c_ls,     cmd_ls,     h_ls
                dd c_cat,    cmd_cat,    h_cat
                dd c_write,  cmd_write,  h_write
                dd c_rm,     cmd_rm,     h_rm
                dd c_format, cmd_format, h_format
                dd c_df,     cmd_df,     h_df
                dd c_user,   cmd_user,   h_user
                dd c_alloc,  cmd_alloc,  h_alloc
                dd c_free,   cmd_free,   h_free
                dd c_peek,   cmd_peek,   h_peek
                dd c_virt,   cmd_virt,   h_virt
                dd c_sleep,  cmd_sleep,  h_sleep
                dd c_colors, cmd_colors, h_colors
                dd c_about,  cmd_about,  h_about
                dd c_panic,  cmd_panic,  h_panic
                dd c_crash,  cmd_crash,  h_crash
                dd 0, 0, 0

; ---------------------------------------------------------------------
                section .bss
                alignb  4
cmdline:        resb    CMDLINE_MAX
argv:           resd    MAX_ARGS
argc:           resd    1
saveptr:        resd    1
last_alloc:     resd    1
worker_counter: resd    1
spin_counter:   resd    1
spin_stop:      resd    1
timebuf:        resb    64
                alignb  4
sector_buffer:  resb    512
filebuf:        resb    FILEBUF_MAX
