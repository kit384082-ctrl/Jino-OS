; =====================================================================
;  Jino-OS  ::  kernel.inc — shared constants and helper macros
; =====================================================================

%ifndef JINO_KERNEL_INC
%define JINO_KERNEL_INC

; --------------------------------------------------------- boot info
BOOTINFO_ADDR       equ 0x00000500
BOOTINFO_MAGIC      equ 0x4F4E494A          ; 'JINO'

BI_MAGIC            equ 0
BI_DRIVE            equ 4
BI_E820_COUNT       equ 8
BI_E820_ADDR        equ 12
BI_LOWMEM_KB        equ 16
BI_HIGHMEM_KB       equ 20
BI_KERNEL_LBA       equ 24
BI_KERNEL_SECT      equ 28
BI_KERNEL_PHYS      equ 32

E820_ENTRY_SIZE     equ 24
E820_BASE           equ 0
E820_LENGTH         equ 8
E820_TYPE           equ 16

E820_USABLE         equ 1

; ------------------------------------------------------ memory layout
KERNEL_PHYS_BASE    equ 0x00100000
KERNEL_STACK_SIZE   equ 0x4000              ; 16 KiB

PAGE_SIZE           equ 4096
PAGE_SHIFT          equ 12

PAGE_PRESENT        equ 1 << 0
PAGE_WRITE          equ 1 << 1
PAGE_USER           equ 1 << 2
PAGE_WRITETHROUGH   equ 1 << 3
PAGE_NOCACHE        equ 1 << 4
PAGE_ACCESSED       equ 1 << 5
PAGE_DIRTY          equ 1 << 6
PAGE_HUGE           equ 1 << 7

; ------------------------------------------------------ segmentation
SEG_NULL            equ 0x00
SEG_KCODE           equ 0x08
SEG_KDATA           equ 0x10
SEG_UCODE           equ 0x18
SEG_UDATA           equ 0x20
SEG_TSS             equ 0x28

; ---------------------------------------------------------- hardware
PIC1_CMD            equ 0x20
PIC1_DATA           equ 0x21
PIC2_CMD            equ 0xA0
PIC2_DATA           equ 0xA1
PIC_EOI             equ 0x20

PIT_CH0             equ 0x40
PIT_CMD             equ 0x43
PIT_FREQ            equ 1193182

KBD_DATA            equ 0x60
KBD_STATUS          equ 0x64
KBD_CMD             equ 0x64

CMOS_ADDR           equ 0x70
CMOS_DATA           equ 0x71

COM1_BASE           equ 0x3F8

VGA_MEMORY          equ 0x000B8000
VGA_WIDTH           equ 80
VGA_HEIGHT          equ 25
VGA_CRTC_INDEX      equ 0x3D4
VGA_CRTC_DATA       equ 0x3D5

; ------------------------------------------------------- text colours
COLOR_BLACK         equ 0x0
COLOR_BLUE          equ 0x1
COLOR_GREEN         equ 0x2
COLOR_CYAN          equ 0x3
COLOR_RED           equ 0x4
COLOR_MAGENTA       equ 0x5
COLOR_BROWN         equ 0x6
COLOR_LGREY         equ 0x7
COLOR_DGREY         equ 0x8
COLOR_LBLUE         equ 0x9
COLOR_LGREEN        equ 0xA
COLOR_LCYAN         equ 0xB
COLOR_LRED          equ 0xC
COLOR_LMAGENTA      equ 0xD
COLOR_YELLOW        equ 0xE
COLOR_WHITE         equ 0xF

%define VGA_ATTR(fg, bg) ((bg) << 4 | (fg))

; ------------------------------------------------------------- macros

; Build a stack frame and preserve the callee-saved registers.
%macro ENTER 0
                push    ebp
                mov     ebp, esp
%endmacro

%macro LEAVE_RET 0
                mov     esp, ebp
                pop     ebp
                ret
%endmacro

; Push a 32-bit argument list and call, then clean the stack up.
%macro CALL1 2
                push    dword %2
                call    %1
                add     esp, 4
%endmacro

%macro CALL2 3
                push    dword %3
                push    dword %2
                call    %1
                add     esp, 8
%endmacro

%macro CALL3 4
                push    dword %4
                push    dword %3
                push    dword %2
                call    %1
                add     esp, 12
%endmacro

; A short delay for slow ISA hardware.
%macro IO_WAIT 0
                push    eax
                mov     al, 0
                out     0x80, al
                pop     eax
%endmacro

%endif ; JINO_KERNEL_INC
