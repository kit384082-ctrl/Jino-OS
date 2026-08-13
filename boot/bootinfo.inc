; =====================================================================
;  Jino-OS  ::  bootinfo.inc
;  Shared layout of the hand-off block between stage2 and the kernel.
;  Lives at physical 0x00000500, safely below the boot sector.
; =====================================================================

%ifndef JINO_BOOTINFO_INC
%define JINO_BOOTINFO_INC

BOOTINFO_ADDR       equ 0x00000500
BOOTINFO_MAGIC      equ 0x4F4E494A          ; 'JINO'
BOOTINFO_SIZE       equ 64

BI_MAGIC            equ 0                   ; dd  BOOTINFO_MAGIC
BI_DRIVE            equ 4                   ; dd  BIOS boot drive
BI_E820_COUNT       equ 8                   ; dd  number of map entries
BI_E820_ADDR        equ 12                  ; dd  pointer to the entries
BI_LOWMEM_KB        equ 16                  ; dd  conventional memory
BI_HIGHMEM_KB       equ 20                  ; dd  memory above 1 MiB
BI_KERNEL_LBA       equ 24                  ; dd  where we came from
BI_KERNEL_SECT      equ 28                  ; dd  kernel size in sectors
BI_KERNEL_PHYS      equ 32                  ; dd  load address

E820_ADDR           equ 0x00000600
E820_MAX            equ 48
E820_ENTRY_SIZE     equ 24

E820_BASE           equ 0
E820_LENGTH         equ 8
E820_TYPE           equ 16
E820_ACPI           equ 20

E820_USABLE         equ 1
E820_RESERVED       equ 2
E820_ACPI_RECLAIM   equ 3
E820_ACPI_NVS       equ 4
E820_BAD            equ 5

%endif ; JINO_BOOTINFO_INC
