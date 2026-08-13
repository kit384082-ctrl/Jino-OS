# =====================================================================
#  Jino-OS — build system
#  Everything (bootloader + kernel) is written in x86 assembly (NASM).
# =====================================================================

NASM      := nasm
LD        := ld
OBJCOPY   := objcopy
PYTHON    := python3

BUILD     := build
BOOT      := boot
KERNEL    := kernel
TOOLS     := tools

# ---------------------------------------------------------------- flags
NASMFLAGS_BIN := -f bin -I$(BOOT)/ -I$(KERNEL)/
NASMFLAGS_ELF := -f elf32 -I$(KERNEL)/ -g -F dwarf
LDFLAGS       := -m elf_i386 -T $(KERNEL)/linker.ld -nostdlib --no-warn-rwx-segments

# ---------------------------------------------------------------- files
KOBJS := \
	$(BUILD)/entry.o    \
	$(BUILD)/kmain.o    \
	$(BUILD)/gdt.o      \
	$(BUILD)/idt.o      \
	$(BUILD)/isr.o      \
	$(BUILD)/pic.o      \
	$(BUILD)/pit.o      \
	$(BUILD)/vga.o      \
	$(BUILD)/serial.o   \
	$(BUILD)/string.o   \
	$(BUILD)/printf.o   \
	$(BUILD)/pmm.o      \
	$(BUILD)/paging.o   \
	$(BUILD)/heap.o     \
	$(BUILD)/keyboard.o \
	$(BUILD)/rtc.o      \
	$(BUILD)/cpu.o      \
	$(BUILD)/ata.o      \
	$(BUILD)/fs.o       \
	$(BUILD)/syscall.o  \
	$(BUILD)/user.o     \
	$(BUILD)/userprog.o \
	$(BUILD)/task.o     \
	$(BUILD)/panic.o    \
	$(BUILD)/shell.o

IMG        := $(BUILD)/jino.img
KERNEL_BIN := $(BUILD)/kernel.bin
STAGE1     := $(BUILD)/stage1.bin
STAGE2     := $(BUILD)/stage2.bin

# Disk layout (LBA sectors)
STAGE2_LBA     := 1
STAGE2_SECTORS := 8
KERNEL_LBA     := 9

.PHONY: all clean run test image dirs info

all: image

dirs:
	@mkdir -p $(BUILD)

# ------------------------------------------------------------- kernel
$(BUILD)/%.o: $(KERNEL)/%.asm | dirs
	$(NASM) $(NASMFLAGS_ELF) $< -o $@

$(BUILD)/kernel.elf: $(KOBJS) $(KERNEL)/linker.ld
	$(LD) $(LDFLAGS) -o $@ $(KOBJS) -Map $(BUILD)/kernel.map

$(KERNEL_BIN): $(BUILD)/kernel.elf
	$(OBJCOPY) -O binary $< $@

# --------------------------------------------------------- bootloader
$(STAGE1): $(BOOT)/stage1.asm | dirs
	$(NASM) $(NASMFLAGS_BIN) \
		-DSTAGE2_LBA=$(STAGE2_LBA) -DSTAGE2_SECTORS=$(STAGE2_SECTORS) $< -o $@

# stage2 needs to know how many sectors the kernel occupies
$(STAGE2): $(BOOT)/stage2.asm $(KERNEL_BIN) | dirs
	$(NASM) $(NASMFLAGS_BIN) \
		-DKERNEL_LBA=$(KERNEL_LBA) \
		-DKERNEL_SECTORS=$$(( ( $$(stat -c%s $(KERNEL_BIN)) + 511 ) / 512 )) \
		$< -o $@

# --------------------------------------------------------------- image
image: $(IMG)

$(IMG): $(STAGE1) $(STAGE2) $(KERNEL_BIN) $(TOOLS)/mkimage.py
	@$(PYTHON) $(TOOLS)/mkimage.py \
		--stage1 $(STAGE1) \
		--stage2 $(STAGE2) --stage2-lba $(STAGE2_LBA) --stage2-sectors $(STAGE2_SECTORS) \
		--kernel $(KERNEL_BIN) --kernel-lba $(KERNEL_LBA) \
		--out $@

info: $(IMG)
	@echo "stage1 : $$(stat -c%s $(STAGE1)) bytes"
	@echo "stage2 : $$(stat -c%s $(STAGE2)) bytes"
	@echo "kernel : $$(stat -c%s $(KERNEL_BIN)) bytes ($$(( ( $$(stat -c%s $(KERNEL_BIN)) + 511 ) / 512 )) sectors)"
	@echo "image  : $$(stat -c%s $(IMG)) bytes"

# ------------------------------------------------------------ emulate
QEMU ?= qemu-system-i386
run: $(IMG)
	$(QEMU) -drive format=raw,file=$(IMG),index=0,if=ide -m 64 -serial stdio

# Software emulator (Unicorn) — works without QEMU installed
sim: $(IMG)
	$(PYTHON) $(TOOLS)/simulate.py $(IMG)

test: $(IMG)
	@$(PYTHON) -c "import unicorn, pytest" 2>/dev/null || { \
		echo "the test suite needs a couple of Python packages:"; \
		echo "    pip install -r requirements-dev.txt"; \
		exit 1; \
	}
	$(PYTHON) -m pytest -q tests

clean:
	rm -rf $(BUILD)
