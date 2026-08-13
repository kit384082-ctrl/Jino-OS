; =====================================================================
;  Jino-OS  ::  pic.asm — 8259A programmable interrupt controllers
; ---------------------------------------------------------------------
;  The BIOS leaves IRQ0-7 mapped onto vectors 8-15, which collide with
;  the CPU exceptions.  We remap the pair to 32-47 and start with every
;  line masked; drivers unmask what they need.
; =====================================================================

                bits    32
%include "kernel.inc"

                global  pic_init
                global  pic_send_eoi
                global  pic_mask_irq
                global  pic_unmask_irq
                global  pic_set_mask
                global  pic_get_mask
                global  pic_disable
                global  pic_get_isr
                global  pic_get_irr

ICW1_INIT       equ     0x10
ICW1_ICW4       equ     0x01
ICW4_8086       equ     0x01

                section .text

; ---------------------------------------------------------------------
; pic_init — remap to 0x20/0x28 and mask everything except the cascade.
; ---------------------------------------------------------------------
pic_init:
                push    ebp
                mov     ebp, esp

                ; remember the current masks (the BIOS may have set some)
                in      al, PIC1_DATA
                mov     [saved_mask1], al
                in      al, PIC2_DATA
                mov     [saved_mask2], al

                ; ICW1: begin initialisation, ICW4 will follow
                mov     al, ICW1_INIT | ICW1_ICW4
                out     PIC1_CMD, al
                IO_WAIT
                out     PIC2_CMD, al
                IO_WAIT

                ; ICW2: vector offsets
                mov     al, 0x20                ; master -> 32
                out     PIC1_DATA, al
                IO_WAIT
                mov     al, 0x28                ; slave  -> 40
                out     PIC2_DATA, al
                IO_WAIT

                ; ICW3: wiring between the two chips
                mov     al, 0x04                ; slave is on IRQ2
                out     PIC1_DATA, al
                IO_WAIT
                mov     al, 0x02                ; slave identity
                out     PIC2_DATA, al
                IO_WAIT

                ; ICW4: 8086 mode
                mov     al, ICW4_8086
                out     PIC1_DATA, al
                IO_WAIT
                out     PIC2_DATA, al
                IO_WAIT

                ; mask all lines but keep the cascade open
                mov     al, 0xFB                ; 1111 1011 -> IRQ2 enabled
                out     PIC1_DATA, al
                IO_WAIT
                mov     al, 0xFF
                out     PIC2_DATA, al
                IO_WAIT

                pop     ebp
                ret

; ---------------------------------------------------------------------
; pic_send_eoi(irq)
; ---------------------------------------------------------------------
pic_send_eoi:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                cmp     eax, 8
                jb      .master
                mov     al, PIC_EOI
                out     PIC2_CMD, al            ; the slave first
                IO_WAIT
.master:
                mov     al, PIC_EOI
                out     PIC1_CMD, al
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pic_mask_irq(irq)
; ---------------------------------------------------------------------
pic_mask_irq:
                push    ebp
                mov     ebp, esp
                push    ebx
                mov     ecx, [ebp + 8]
                cmp     ecx, 8
                jae     .slave

                in      al, PIC1_DATA
                mov     ah, 1
                shl     ah, cl
                or      al, ah
                out     PIC1_DATA, al
                jmp     .done
.slave:
                sub     ecx, 8
                in      al, PIC2_DATA
                mov     ah, 1
                shl     ah, cl
                or      al, ah
                out     PIC2_DATA, al
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pic_unmask_irq(irq)
; ---------------------------------------------------------------------
pic_unmask_irq:
                push    ebp
                mov     ebp, esp
                push    ebx
                mov     ecx, [ebp + 8]
                cmp     ecx, 8
                jae     .slave

                in      al, PIC1_DATA
                mov     ah, 1
                shl     ah, cl
                not     ah
                and     al, ah
                out     PIC1_DATA, al
                jmp     .done
.slave:
                sub     ecx, 8
                in      al, PIC2_DATA
                mov     ah, 1
                shl     ah, cl
                not     ah
                and     al, ah
                out     PIC2_DATA, al
                ; make sure the cascade line stays open
                in      al, PIC1_DATA
                and     al, ~(1 << 2)
                out     PIC1_DATA, al
.done:
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pic_set_mask(mask16)
; ---------------------------------------------------------------------
pic_set_mask:
                push    ebp
                mov     ebp, esp
                mov     eax, [ebp + 8]
                out     PIC1_DATA, al
                IO_WAIT
                shr     eax, 8
                out     PIC2_DATA, al
                pop     ebp
                ret

; ---------------------------------------------------------------------
; pic_get_mask -> EAX (slave in the high byte)
; ---------------------------------------------------------------------
pic_get_mask:
                xor     eax, eax
                in      al, PIC2_DATA
                shl     eax, 8
                in      al, PIC1_DATA
                ret

; ---------------------------------------------------------------------
; pic_disable — mask every line, e.g. before switching to the APIC.
; ---------------------------------------------------------------------
pic_disable:
                mov     al, 0xFF
                out     PIC1_DATA, al
                IO_WAIT
                out     PIC2_DATA, al
                ret

; ---------------------------------------------------------------------
; pic_get_isr / pic_get_irr -> EAX
; ---------------------------------------------------------------------
pic_get_isr:
                mov     al, 0x0B                ; OCW3: read ISR
                out     PIC1_CMD, al
                out     PIC2_CMD, al
                IO_WAIT
                xor     eax, eax
                in      al, PIC2_CMD
                shl     eax, 8
                in      al, PIC1_CMD
                ret

pic_get_irr:
                mov     al, 0x0A                ; OCW3: read IRR
                out     PIC1_CMD, al
                out     PIC2_CMD, al
                IO_WAIT
                xor     eax, eax
                in      al, PIC2_CMD
                shl     eax, 8
                in      al, PIC1_CMD
                ret

; ---------------------------------------------------------------------
                section .bss
saved_mask1:    resb    1
saved_mask2:    resb    1
