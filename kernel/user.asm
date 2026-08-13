; =====================================================================
;  Jino-OS  ::  user.asm — ring 3 support
; ---------------------------------------------------------------------
;  Everything up to now has run in ring 0, where a stray pointer can
;  take the machine down.  This module drops a task into ring 3, where
;  the only way back into the kernel is through int 0x80.
;
;  A user program is an ordinary function in the kernel image for the
;  moment — there is no loader yet — but it executes with CPL 3, on its
;  own stack, and with only the pages it was given marked PAGE_USER.
;  A ring 3 task that touches anything else takes a page fault instead
;  of corrupting the kernel.
;
;  The transition itself is the classic iret trick: push the ss, esp,
;  eflags, cs and eip the CPU should adopt, then iret into them.  The
;  return path is the TSS: esp0 points at the kernel stack that every
;  interrupt taken in ring 3 switches to.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  user_init
                global  user_enter
                global  user_map_range
                global  user_mode_active
                global  user_syscall_count
                global  user_exit_code
                global  user_returned

                extern  gdt_set_kernel_stack
                extern  paging_set_user
                extern  paging_is_enabled
                extern  kprintf

USER_STACK_PAGES equ    4                       ; 16 KiB

                section .text

; ---------------------------------------------------------------------
; user_init — prepare the ring 3 stack and note the kernel stack.
; ---------------------------------------------------------------------
user_init:
                ENTER

                mov     dword [user_mode_active], 0
                mov     dword [user_syscall_count], 0
                mov     dword [user_returned], 0
                mov     dword [user_exit_code], 0

                ; the stack ring 3 will run on
                CALL2   paging_set_user, user_stack, USER_STACK_PAGES

                LEAVE_RET

; ---------------------------------------------------------------------
; user_map_range(address, pages) -> EAX = pages opened
;
;   Hands a span of the identity map to ring 3.  Used to expose the
;   code a user task runs and any data it is allowed to see.
; ---------------------------------------------------------------------
user_map_range:
                ENTER
                push    dword [ebp + 12]
                push    dword [ebp + 8]
                call    paging_set_user
                add     esp, 8
                LEAVE_RET

; ---------------------------------------------------------------------
; user_enter(entry) -> EAX = the code the task exited with
;
;   Switches to ring 3 at `entry` and comes back when the task calls
;   sys_exit.  The kernel stack pointer is saved first so that the exit
;   syscall can simply restore it and return here, which avoids having
;   to unwind an interrupt frame by hand.
; ---------------------------------------------------------------------
user_enter:
                ENTER
                push    ebx
                push    esi
                push    edi

                ; Where sys_exit should come back to.  Saving esp after
                ; the pushes means the matching pops below still line up.
                ;
                ; ebp has to be kept as well: sys_exit returns straight
                ; out of an interrupt, abandoning the frame the stub had
                ; built, so the ebp this function was entered with is
                ; long gone by then.
                mov     [kernel_resume_esp], esp
                mov     [kernel_resume_ebp], ebp
                mov     dword [user_returned], 0
                mov     dword [user_mode_active], 1

                ; Interrupts taken in ring 3 land on this stack.  It has
                ; to be the stack we are on now, above the frame we just
                ; built, or the return path would overwrite it.
                CALL1   gdt_set_kernel_stack, user_kernel_stack_top

                mov     ecx, [ebp + 8]          ; entry point

                ; the segment registers ring 3 runs with
                mov     ax, SEG_UDATA | 3
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax

                ; build the frame iret needs: ss, esp, eflags, cs, eip
                push    dword SEG_UDATA | 3
                push    dword user_stack_top
                pushfd
                pop     eax
                or      eax, 1 << 9             ; interrupts on in ring 3
                and     eax, ~(3 << 12)         ; IOPL 0: no port access
                push    eax
                push    dword SEG_UCODE | 3
                push    ecx
                iret                            ; and we are in ring 3

; sys_exit lands here, on the kernel stack, with the exit code in EAX.
user_return_point:
                mov     esp, [kernel_resume_esp]
                mov     ebp, [kernel_resume_ebp]
                mov     dword [user_mode_active], 0
                mov     dword [user_returned], 1

                mov     ax, SEG_KDATA
                mov     ds, ax
                mov     es, ax
                mov     fs, ax
                mov     gs, ax

                mov     eax, [user_exit_code]

                pop     edi
                pop     esi
                pop     ebx
                LEAVE_RET

; ---------------------------------------------------------------------
; user_leave(code) — called from the syscall handler for sys_exit.
;
;   Does not return to its caller; it abandons the interrupt frame and
;   resumes user_enter instead.
; ---------------------------------------------------------------------
                global  user_leave
user_leave:
                mov     eax, [esp + 4]
                mov     [user_exit_code], eax
                jmp     user_return_point

; ---------------------------------------------------------------------
                section .bss
                alignb  4
user_mode_active:   resd 1
user_syscall_count: resd 1
user_exit_code:     resd 1
user_returned:      resd 1
kernel_resume_esp:  resd 1
kernel_resume_ebp:  resd 1

; The stack ring 3 runs on.  It is in .bss rather than .stack because
; clearing it at boot is harmless — nothing is stored here before then.
                alignb  PAGE_SIZE
user_stack:         resb PAGE_SIZE * USER_STACK_PAGES
user_stack_top:

; Interrupts taken while in ring 3 switch to this stack via the TSS.
                alignb  PAGE_SIZE
user_kernel_stack:  resb PAGE_SIZE * 2
user_kernel_stack_top:
