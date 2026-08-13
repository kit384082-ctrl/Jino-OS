; =====================================================================
;  Jino-OS  ::  kmain.asm — kernel initialisation
; ---------------------------------------------------------------------
;  Brings every subsystem up in dependency order, prints a short report
;  and then hands the machine over to the shell.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  kmain
                global  kernel_version

                extern  vga_init
                extern  vga_clear
                extern  vga_puts
                extern  vga_set_color
                extern  vga_fill_row
                extern  serial_init
                extern  kprintf
                extern  kputs
                extern  gdt_init
                extern  gdt_set_kernel_stack
                extern  idt_init
                extern  idt_enable
                extern  idt_register_handler
                extern  pic_init
                extern  pit_init
                extern  keyboard_init
                extern  rtc_init
                extern  cpu_detect
                extern  cpu_print_info
                extern  pmm_init
                extern  pmm_total_pages
                extern  pmm_used_pages
                extern  paging_init
                extern  heap_init
                extern  heap_total
                extern  ata_init
                extern  ata_print_info
                extern  fs_init
                extern  fs_print_info
                extern  syscall_init
                extern  user_init
                extern  user_map_range
                extern  user_area_start
                extern  user_program_size
                extern  task_init
                extern  shell_run
                extern  panic
                extern  kernel_stack_top
                extern  __kernel_start
                extern  __kernel_end
                extern  pit_sleep_ms

TIMER_HZ        equ     100

                section .text

; ---------------------------------------------------------------------
; kmain(magic, bootinfo)
; ---------------------------------------------------------------------
kmain:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                mov     esi, [ebp + 12]         ; boot information block

                ; ---- console first, so we can report progress --------
                call    vga_init
                call    serial_init

                call    banner

                ; ---- verify the hand-off -----------------------------
                mov     eax, [ebp + 8]
                cmp     eax, BOOTINFO_MAGIC
                je      .magic_ok
                push    dword msg_bad_magic
                call    panic
                add     esp, 4
.magic_ok:

                ; ---- descriptor tables -------------------------------
                call    step_gdt
                call    gdt_init

                mov     eax, kernel_stack_top
                push    eax
                call    gdt_set_kernel_stack
                add     esp, 4
                call    step_ok

                call    step_idt
                call    idt_init
                call    step_ok

                ; ---- interrupt controller and timer ------------------
                call    step_pic
                call    pic_init
                call    step_ok

                call    step_pit
                push    dword TIMER_HZ
                call    pit_init
                add     esp, 4
                call    step_ok

                ; ---- physical memory ---------------------------------
                call    step_pmm
                push    esi
                call    pmm_init
                add     esp, 4
                call    step_ok

                ; ---- paging ------------------------------------------
                call    step_paging
                call    paging_init
                call    step_ok

                ; ---- the kernel heap ---------------------------------
                call    step_heap
                call    heap_init
                call    step_ok

                ; ---- input -------------------------------------------
                call    step_keyboard
                call    keyboard_init
                call    step_ok

                ; ---- clock -------------------------------------------
                call    step_rtc
                call    rtc_init
                call    step_ok

                ; ---- processor identification ------------------------
                call    step_cpu
                call    cpu_detect
                call    step_ok

                ; ---- storage -----------------------------------------
                call    step_ata
                call    ata_init
                call    step_ok

                ; ---- filesystem --------------------------------------
                call    step_fs
                call    fs_init
                call    step_ok

                ; ---- ring 3 ------------------------------------------
                call    step_user
                call    syscall_init
                call    user_init
                ; open the user program's own pages to ring 3
                mov     eax, [user_program_size]
                add     eax, PAGE_SIZE - 1
                shr     eax, PAGE_SHIFT
                push    eax
                push    dword [user_area_start]
                call    user_map_range
                add     esp, 8
                call    step_ok

                ; ---- tasking -----------------------------------------
                call    step_task
                call    task_init
                call    step_ok

                ; ---- a couple of handlers of our own -----------------
                push    dword breakpoint_handler
                push    dword 3
                call    idt_register_handler
                add     esp, 8

                ; ---- interrupts on --------------------------------
                call    idt_enable

                ; ---- report ------------------------------------------
                push    dword msg_nl
                call    kprintf
                add     esp, 4

                call    cpu_print_info
                call    ata_print_info
                call    fs_print_info
                call    report_memory

                push    dword msg_ready
                call    kprintf
                add     esp, 4

                ; ---- the shell owns the machine from here ------------
                call    shell_run

                ; shell_run does not return, but just in case
                push    dword msg_shell_returned
                call    panic
                add     esp, 4

                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; banner — the splash shown at the top of the screen
; ---------------------------------------------------------------------
banner:
                push    ebp
                mov     ebp, esp

                push    dword VGA_ATTR(COLOR_WHITE, COLOR_BLUE)
                call    vga_set_color
                add     esp, 4

                push    dword logo1
                call    kprintf
                add     esp, 4

                push    dword VGA_ATTR(COLOR_LGREY, COLOR_BLACK)
                call    vga_set_color
                add     esp, 4

                push    dword logo2
                call    kprintf
                add     esp, 4

                pop     ebp
                ret

; ---------------------------------------------------------------------
; report_memory — the summary printed after initialisation
; ---------------------------------------------------------------------
report_memory:
                push    ebp
                mov     ebp, esp
                push    ebx

                mov     eax, [pmm_total_pages]
                shl     eax, 2                  ; pages -> KiB
                mov     ebx, eax

                mov     eax, __kernel_end
                sub     eax, __kernel_start
                shr     eax, 10                 ; kernel size in KiB

                push    dword [heap_total]
                push    eax
                push    dword [pmm_total_pages]
                push    ebx
                push    dword fmt_memory
                call    kprintf
                add     esp, 20

                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; breakpoint_handler(frame) — INT 3 should not be fatal.
; ---------------------------------------------------------------------
breakpoint_handler:
                push    ebp
                mov     ebp, esp
                push    dword msg_breakpoint
                call    kprintf
                add     esp, 4
                pop     ebp
                ret

; ---------------------------------------------------------------------
;  Progress reporting helpers
; ---------------------------------------------------------------------
%macro STEP 2
%1:
                push    dword %2
                push    dword fmt_step
                call    kprintf
                add     esp, 8
                ret
%endmacro

STEP step_gdt,      s_gdt
STEP step_idt,      s_idt
STEP step_pic,      s_pic
STEP step_pit,      s_pit
STEP step_pmm,      s_pmm
STEP step_paging,   s_paging
STEP step_heap,     s_heap
STEP step_keyboard, s_keyboard
STEP step_rtc,      s_rtc
STEP step_cpu,      s_cpu
STEP step_ata,      s_ata
STEP step_fs,       s_fs
STEP step_user,     s_user
STEP step_task,     s_task

step_ok:
                push    dword VGA_ATTR(COLOR_LGREEN, COLOR_BLACK)
                call    vga_set_color
                add     esp, 4
                push    dword msg_ok
                call    kprintf
                add     esp, 4
                push    dword VGA_ATTR(COLOR_LGREY, COLOR_BLACK)
                call    vga_set_color
                add     esp, 4
                ret

; ---------------------------------------------------------------------
                section .rodata
kernel_version: db      "Jino-OS 1.0", 0

logo1:          db      "                    J I N O - O S   v 1 . 0                     ", 10, 0
logo2:          db      "        an x86 operating system written in pure assembly", 10, 10, 0

fmt_step:       db      "  %-28s", 0
msg_ok:         db      "[ ok ]", 10, 0

s_gdt:          db      "global descriptor table", 0
s_idt:          db      "interrupt descriptor table", 0
s_pic:          db      "interrupt controller", 0
s_pit:          db      "interval timer", 0
s_pmm:          db      "physical memory manager", 0
s_paging:       db      "paging", 0
s_heap:         db      "kernel heap", 0
s_keyboard:     db      "ps/2 keyboard", 0
s_rtc:          db      "real time clock", 0
s_cpu:          db      "cpu identification", 0
s_ata:          db      "ata storage", 0
s_fs:           db      "jinofs filesystem", 0
s_user:         db      "ring 3 user mode", 0
s_task:         db      "task scheduler", 0

fmt_memory:     db      "memory: %u KiB usable (%u pages), kernel %u KiB, heap %u bytes", 10, 0
msg_ready:      db      10, "system ready.", 10, 0
msg_nl:         db      10, 0
msg_breakpoint: db      "breakpoint trap", 10, 0

msg_bad_magic:  db      "bad boot signature: the loader did not hand over correctly", 0
msg_shell_returned: db  "the shell returned unexpectedly", 0
