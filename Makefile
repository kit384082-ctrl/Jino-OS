ENTRY(_start)
SECTIONS
{
    . = 0x100000;
    .text : {
        *(.text)
    }
    .rodata : {
        *(.rodata)
    }
    .data : {
        *(.data)
    }
    .bss : {
        *(COMMON)
        *(.bss)
    }
}

test:
	mkdir -p tests
	gcc -o tests/test_shell tests/test_shell.c
	./tests/test_shell
