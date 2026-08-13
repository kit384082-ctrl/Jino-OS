/* =====================================================================
 *  Jino-OS  ::  linker.ld
 *  The kernel is a flat binary loaded by stage2 at physical 1 MiB.
 * ===================================================================== */

OUTPUT_FORMAT(elf32-i386)
OUTPUT_ARCH(i386)
ENTRY(_start)

KERNEL_BASE = 0x00100000;

SECTIONS
{
    . = KERNEL_BASE;

    __kernel_start = .;

    .text ALIGN(4K) : {
        __text_start = .;
        *(.text.entry)
        *(.text)
        *(.text.*)
        __text_end = .;
    }

    .rodata ALIGN(4K) : {
        __rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        __rodata_end = .;
    }

    .data ALIGN(4K) : {
        __data_start = .;
        *(.data)
        *(.data.*)
        __data_end = .;
    }

    .bss ALIGN(4K) : {
        __bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        . = ALIGN(4K);
        __bss_end = .;
    }

    /* The kernel stack is kept out of the range clear_bss zeroes,
       because clear_bss itself runs on it. */
    .stack ALIGN(4K) (NOLOAD) : {
        __stack_start = .;
        *(.stack)
        . = ALIGN(4K);
        __stack_end = .;
    }

    __kernel_end = .;

    /DISCARD/ : {
        *(.comment)
        *(.note.*)
        *(.eh_frame)
    }
}
