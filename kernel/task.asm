; =====================================================================
;  Jino-OS  ::  task.asm — cooperative/preemptive kernel threads
; ---------------------------------------------------------------------
;  Round-robin scheduling over a fixed table of kernel-mode tasks.  A
;  context switch simply saves the callee-saved registers and EFLAGS on
;  the outgoing stack, swaps ESP and returns into the incoming one.
;
;      struct task {
;          u32   esp;        // saved stack pointer
;          u32   stack_base; // for the debugger and for teardown
;          u32   state;
;          u32   id;
;          u32   ticks;      // how much CPU time it has had
;          char  name[24];
;      };
; =====================================================================

                bits    32
%include "kernel.inc"

                global  task_init
                global  task_create
                global  task_yield
                global  task_exit
                global  task_schedule
                global  task_schedule_from_irq
                global  task_current_id
                global  task_count
                global  task_list
                global  task_sleep
                global  task_set_preemption
                global  task_print
                global  task_reap
                global  task_resched_if_needed

                extern  kmalloc
                extern  kfree
                extern  kprintf
                extern  memset
                extern  strncpy
                extern  pit_ticks
                extern  pit_set_callback

MAX_TASKS       equ     16
TASK_STACK_SIZE equ     8192

; task states
STATE_UNUSED    equ     0
STATE_READY     equ     1
STATE_RUNNING   equ     2
STATE_SLEEPING  equ     3
STATE_ZOMBIE    equ     4

; structure layout
T_ESP           equ     0
T_STACK         equ     4
T_STATE         equ     8
T_ID            equ     12
T_TICKS         equ     16
T_WAKEUP        equ     20
T_NAME          equ     24
T_SIZE          equ     48

                section .text

; ---------------------------------------------------------------------
; task_init — turn the current thread of execution into task 0.
; ---------------------------------------------------------------------
task_init:
                push    ebp
                mov     ebp, esp
                push    edi

                push    dword MAX_TASKS * T_SIZE
                push    dword 0
                push    dword task_list
                call    memset
                add     esp, 12

                ; slot 0 describes whatever is running right now
                mov     edi, task_list
                mov     dword [edi + T_STATE], STATE_RUNNING
                mov     dword [edi + T_ID], 0
                mov     dword [edi + T_TICKS], 0
                mov     dword [edi + T_STACK], 0

                push    dword 24
                push    dword name_kernel
                lea     eax, [edi + T_NAME]
                push    eax
                call    strncpy
                add     esp, 12

                mov     dword [current_task], 0
                mov     dword [task_count], 1
                mov     dword [next_id], 1
                mov     dword [preemption_on], 0

                pop     edi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; task_create(entry, name) -> EAX = task id, or -1 on failure
; ---------------------------------------------------------------------
task_create:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                ; ---- find a free slot --------------------------------
                xor     ebx, ebx
.find_slot:
                cmp     ebx, MAX_TASKS
                jae     .no_slot
                mov     eax, ebx
                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]
                cmp     dword [esi + T_STATE], STATE_UNUSED
                je      .got_slot
                inc     ebx
                jmp     .find_slot
.got_slot:

                ; ---- a stack for it ----------------------------------
                push    dword TASK_STACK_SIZE
                call    kmalloc
                add     esp, 4
                test    eax, eax
                jz      .no_memory
                mov     [esi + T_STACK], eax

                ; build the initial frame at the top of the stack
                lea     edi, [eax + TASK_STACK_SIZE]
                and     edi, ~15                ; keep it aligned

                ; The frame task_switch expects to pop, from the top:
                ;   edi esi ebx ebp eflags <return address>
                sub     edi, 4
                mov     dword [edi], task_trampoline    ; return address

                sub     edi, 4
                mov     dword [edi], 0x00000202         ; eflags, IF set

                sub     edi, 4
                mov     dword [edi], 0                  ; ebp
                sub     edi, 4
                mov     dword [edi], 0                  ; ebx
                sub     edi, 4
                mov     eax, [ebp + 8]
                mov     [edi], eax                      ; esi = entry point
                sub     edi, 4
                mov     dword [edi], 0                  ; edi

                mov     [esi + T_ESP], edi

                ; ---- bookkeeping -------------------------------------
                mov     eax, [next_id]
                mov     [esi + T_ID], eax
                inc     dword [next_id]
                mov     dword [esi + T_STATE], STATE_READY
                mov     dword [esi + T_TICKS], 0
                mov     dword [esi + T_WAKEUP], 0

                mov     ecx, [ebp + 12]
                test    ecx, ecx
                jnz     .have_name
                mov     ecx, name_unnamed
.have_name:
                push    eax
                push    dword 24
                push    ecx
                lea     eax, [esi + T_NAME]
                push    eax
                call    strncpy
                add     esp, 12
                pop     eax

                inc     dword [task_count]
                jmp     .done

.no_slot:
.no_memory:
                mov     eax, -1
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; task_trampoline — the first thing a new task runs.  ESI holds its
;                   entry point; when that returns we exit cleanly.
; ---------------------------------------------------------------------
task_trampoline:
                sti
                call    esi
                push    eax
                call    task_exit
                add     esp, 4
                ; task_exit never comes back
.hang:          hlt
                jmp     .hang

; ---------------------------------------------------------------------
; task_yield — give up the rest of this time slice.
; ---------------------------------------------------------------------
task_yield:
                call    task_reap
                call    task_schedule
                ret

; ---------------------------------------------------------------------
; task_reap — release the stack of a task that has exited.
;   task_exit cannot free its own stack while it is still standing on
;   it, so it leaves the pointer here for whoever runs next.
; ---------------------------------------------------------------------
task_reap:
                pushfd
                cli
                mov     eax, [pending_free]
                test    eax, eax
                jz      .nothing
                mov     dword [pending_free], 0
                push    eax
                call    kfree
                add     esp, 4
.nothing:
                popfd
                ret

; ---------------------------------------------------------------------
; task_schedule — pick the next runnable task and switch to it.
; ---------------------------------------------------------------------
task_schedule:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                pushfd
                cli

                cmp     dword [task_count], 2
                jb      .nothing_to_do

                ; ---- wake anyone whose sleep has expired -------------
                call    wake_sleepers

                ; ---- round robin from the current slot ---------------
                mov     ebx, [current_task]
                mov     ecx, ebx
                xor     edx, edx                ; how many we inspected
.search:
                inc     ecx
                cmp     ecx, MAX_TASKS
                jb      .no_wrap
                xor     ecx, ecx
.no_wrap:
                inc     edx
                cmp     edx, MAX_TASKS
                ja      .nothing_to_do

                mov     eax, ecx
                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]
                cmp     dword [esi + T_STATE], STATE_READY
                jne     .search

                ; ---- perform the switch ------------------------------
                mov     eax, ebx
                imul    eax, eax, T_SIZE
                lea     edi, [task_list + eax]  ; outgoing task

                cmp     dword [edi + T_STATE], STATE_RUNNING
                jne     .outgoing_kept
                mov     dword [edi + T_STATE], STATE_READY
.outgoing_kept:
                mov     dword [esi + T_STATE], STATE_RUNNING
                inc     dword [esi + T_TICKS]
                mov     [current_task], ecx

                lea     eax, [esi + T_ESP]      ; &new->esp
                lea     edx, [edi + T_ESP]      ; &old->esp
                push    eax
                push    edx
                call    task_switch
                add     esp, 8

.nothing_to_do:
                popfd
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; task_switch(old_esp_ptr, new_esp_ptr)
;   Saves the callee-saved state on the outgoing stack, records ESP and
;   loads the incoming one.  The layout matches what task_create builds.
; ---------------------------------------------------------------------
task_switch:
                mov     eax, [esp + 4]          ; &old->esp
                mov     edx, [esp + 8]          ; &new->esp

                pushfd
                push    ebp
                push    ebx
                push    esi
                push    edi

                mov     [eax], esp              ; save the outgoing stack
                mov     esp, [edx]              ; adopt the incoming one

                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                popfd
                ret

; ---------------------------------------------------------------------
; wake_sleepers — move sleeping tasks back to ready when their deadline
;                 has passed.
; ---------------------------------------------------------------------
wake_sleepers:
                push    ebx
                push    esi
                mov     ecx, [pit_ticks]
                xor     ebx, ebx
.loop:
                cmp     ebx, MAX_TASKS
                jae     .done
                mov     eax, ebx
                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]
                cmp     dword [esi + T_STATE], STATE_SLEEPING
                jne     .next
                mov     eax, [esi + T_WAKEUP]
                cmp     ecx, eax
                jb      .next
                mov     dword [esi + T_STATE], STATE_READY
.next:
                inc     ebx
                jmp     .loop
.done:
                pop     esi
                pop     ebx
                ret

; ---------------------------------------------------------------------
; task_sleep(ticks) — block this task for a while.
; ---------------------------------------------------------------------
task_sleep:
                push    ebp
                mov     ebp, esp
                push    esi

                mov     eax, [current_task]
                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]

                mov     eax, [pit_ticks]
                add     eax, [ebp + 8]
                mov     [esi + T_WAKEUP], eax
                mov     dword [esi + T_STATE], STATE_SLEEPING

                call    task_schedule

                pop     esi
                pop     ebp
                ret

; ---------------------------------------------------------------------
; task_exit(status) — retire the running task.
; ---------------------------------------------------------------------
task_exit:
                push    ebp
                mov     ebp, esp
                push    esi

                cli
                mov     eax, [current_task]
                test    eax, eax
                jz      .cannot_exit            ; task 0 is the kernel

                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]

                mov     dword [esi + T_STATE], STATE_UNUSED
                dec     dword [task_count]

                mov     eax, [esi + T_STACK]
                test    eax, eax
                jz      .no_stack
                ; NOTE: the stack we are standing on belongs to this
                ; task, so it can only be released once we have left it.
                mov     [pending_free], eax
                mov     dword [esi + T_STACK], 0
.no_stack:
                ; Switch away for the last time.  task_schedule cannot
                ; help here: it refuses to run with a single task left,
                ; and this one is already gone.  So pick the next
                ; runnable task by hand and jump straight into it,
                ; discarding the state of the dying task.
                call    pick_next_runnable      ; -> ESI, ECX = slot
                test    esi, esi
                jz      .cannot_exit

                mov     dword [esi + T_STATE], STATE_RUNNING
                inc     dword [esi + T_TICKS]
                mov     [current_task], ecx

                ; a one-way switch: nothing of ours needs preserving
                mov     esp, [esi + T_ESP]
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                popfd
                ret

.cannot_exit:
                sti
.hang:
                hlt
                jmp     .hang

; ---------------------------------------------------------------------
; pick_next_runnable -> ESI = task pointer (0 when there is none),
;                       ECX = its slot index
; ---------------------------------------------------------------------
pick_next_runnable:
                push    ebx
                mov     ebx, [current_task]
                mov     ecx, ebx
                xor     edx, edx
.search:
                inc     ecx
                cmp     ecx, MAX_TASKS
                jb      .no_wrap
                xor     ecx, ecx
.no_wrap:
                inc     edx
                cmp     edx, MAX_TASKS
                ja      .none

                mov     eax, ecx
                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]
                cmp     dword [esi + T_STATE], STATE_READY
                jne     .search
                pop     ebx
                ret
.none:
                xor     esi, esi
                pop     ebx
                ret

; ---------------------------------------------------------------------
; task_schedule_from_irq(frame) — the timer callback used when
;                                 preemption is switched on.
;
;   Switching stacks here would strand the rest of the interrupt path,
;   most importantly the end-of-interrupt the PIC is waiting for.  So we
;   only raise a flag; irq_common acts on it once the hardware has been
;   dealt with and it is safe to leave.
; ---------------------------------------------------------------------
task_schedule_from_irq:
                push    ebp
                mov     ebp, esp
                cmp     dword [preemption_on], 0
                je      .done
                mov     dword [need_resched], 1
.done:
                pop     ebp
                ret

; ---------------------------------------------------------------------
; task_resched_if_needed — called at the tail of the IRQ path, after the
;                          EOI, with the frame about to be restored.
; ---------------------------------------------------------------------
task_resched_if_needed:
                cmp     dword [need_resched], 0
                je      .done
                mov     dword [need_resched], 0
                call    task_reap
                call    task_schedule
.done:
                ret

; ---------------------------------------------------------------------
; task_set_preemption(enable)
; ---------------------------------------------------------------------
task_set_preemption:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                mov     [preemption_on], eax
                test    eax, eax
                jz      .disable
                push    dword task_schedule_from_irq
                call    pit_set_callback
                add     esp, 4
                jmp     .done
.disable:
                push    dword 0
                call    pit_set_callback
                add     esp, 4
.done:
                pop     ebp
                ret

; ---------------------------------------------------------------------
; task_current_id -> EAX
; ---------------------------------------------------------------------
task_current_id:
                mov     eax, [current_task]
                imul    eax, eax, T_SIZE
                mov     eax, [task_list + eax + T_ID]
                ret

; ---------------------------------------------------------------------
; task_print — a process listing
; ---------------------------------------------------------------------
task_print:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi

                push    dword hdr_tasks
                call    kprintf
                add     esp, 4

                xor     ebx, ebx
.loop:
                cmp     ebx, MAX_TASKS
                jae     .done
                mov     eax, ebx
                imul    eax, eax, T_SIZE
                lea     esi, [task_list + eax]
                cmp     dword [esi + T_STATE], STATE_UNUSED
                je      .next

                mov     eax, [esi + T_STATE]
                cmp     eax, 4
                jbe     .state_ok
                xor     eax, eax
.state_ok:
                mov     edx, [state_names + eax * 4]

                lea     eax, [esi + T_NAME]
                push    dword [esi + T_TICKS]
                push    edx
                push    eax
                push    dword [esi + T_ID]
                push    dword fmt_task
                call    kprintf
                add     esp, 20
.next:
                inc     ebx
                jmp     .loop
.done:
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
                section .rodata
name_kernel:    db      "kernel", 0
name_unnamed:   db      "task", 0
hdr_tasks:      db      "  id  name                      state     ticks", 10, 0
fmt_task:       db      "  %-3u %-24s  %-8s  %u", 10, 0

s_unused:       db      "unused", 0
s_ready:        db      "ready", 0
s_running:      db      "running", 0
s_sleeping:     db      "sleeping", 0
s_zombie:       db      "zombie", 0

                align   4
state_names:    dd      s_unused, s_ready, s_running, s_sleeping, s_zombie

                section .bss
                alignb  4
task_list:      resb    MAX_TASKS * T_SIZE
current_task:   resd    1
task_count:     resd    1
next_id:        resd    1
preemption_on:  resd    1
need_resched:   resd    1
pending_free:   resd    1
