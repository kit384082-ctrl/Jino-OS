ASM=nasm
CC=i686-elf-gcc
LD=i686-elf-ld
CFLAGS=-ffreestanding -nostdlib -fno-builtin -Wall -Wextra -O2 -I src/lib -I src
LDFLAGS=-T linker.ld

OBJS=build/kernel.o build/memory.o build/vga.o build/shell.o build/idt.o build/keyboard.o build/fs.o build/jserver.o build/jdb.o build/gui.o build/window.o build/desktop.o

all: jino.iso

build:
	mkdir -p build

build/kernel.o: src/kernel/kernel.c
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/kernel/%.c
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/drivers/%.c
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/shell/%.c
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/gui/%.c
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/fullstack/%.c
	$(CC) $(CFLAGS) -c $< -o $@

kernel.bin: $(OBJS) linker.ld
	$(LD) $(LDFLAGS) -o kernel.bin $(OBJS)

jino.iso: kernel.bin
	mkdir -p isodir/boot/grub
	cp kernel.bin isodir/boot/
	echo 'set timeout=0\nset default=0\nmenuentry "Jino OS 3.0 Hybrid Console+GUI" { multiboot /boot/kernel.bin\n boot }' > isodir/boot/grub/grub.cfg
	grub-mkrescue -o jino.iso isodir

clean:
	rm -rf build isodir *.iso *.bin

run: jino.iso
	qemu-system-i386 -cdrom jino.iso -m 64
