"""Kernel initialisation and the subsystems it brings up."""

import pytest

from conftest import boot_with


class TestInitialisation:
    @pytest.mark.parametrize(
        "subsystem",
        [
            "global descriptor table",
            "interrupt descriptor table",
            "interrupt controller",
            "interval timer",
            "physical memory manager",
            "paging",
            "kernel heap",
            "ps/2 keyboard",
            "real time clock",
            "cpu identification",
            "ata storage",
            "task scheduler",
        ],
    )
    def test_subsystem_reports_ok(self, booted, subsystem):
        serial = booted.serial_text()
        line = next((l for l in serial.splitlines() if subsystem in l), None)
        assert line is not None, f"{subsystem} was never initialised"
        assert "[ ok ]" in line, f"{subsystem} did not report success"

    def test_reaches_the_ready_state(self, booted):
        assert "system ready." in booted.serial_text()

    def test_does_not_panic_during_boot(self, booted):
        assert "KERNEL PANIC" not in booted.serial_text()

    def test_shell_prompt_is_shown(self, booted):
        assert "jino>" in booted.screen_text()


class TestProtectedMode:
    def test_paging_is_enabled(self, booted):
        from unicorn.x86_const import UC_X86_REG_CR0

        cr0 = booted.uc.reg_read(UC_X86_REG_CR0)
        assert cr0 & 0x00000001, "protected mode bit is not set"
        assert cr0 & 0x80000000, "paging bit is not set"

    def test_page_directory_is_loaded(self, booted):
        from unicorn.x86_const import UC_X86_REG_CR3

        assert booted.uc.reg_read(UC_X86_REG_CR3) != 0

    def test_kernel_segments_are_flat(self, booted):
        from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_DS

        assert booted.uc.reg_read(UC_X86_REG_CS) == 0x08
        assert booted.uc.reg_read(UC_X86_REG_DS) == 0x10


class TestCpuDetection:
    def test_vendor_is_reported(self, booted):
        assert "cpu: vendor" in booted.serial_text()

    def test_features_are_decoded(self, booted):
        line = next(
            l for l in booted.serial_text().splitlines() if "cpu: features" in l
        )
        # any x86 that can run this kernel has these
        assert "fpu" in line
        assert "tsc" in line

    def test_family_and_model_are_parsed(self, booted):
        assert "family" in booted.serial_text()


class TestMemoryReport:
    def test_usable_memory_is_reported(self, booted):
        line = next(l for l in booted.serial_text().splitlines() if "memory:" in l)
        assert "KiB usable" in line

    def test_detects_the_configured_amount_of_ram(self, booted):
        line = next(l for l in booted.serial_text().splitlines() if "memory:" in l)
        kib = int(line.split()[1])
        # 64 MiB of emulated RAM, minus what the low megabyte holds back
        assert 60_000 < kib < 66_000

    def test_page_count_matches_the_byte_count(self, booted):
        line = next(l for l in booted.serial_text().splitlines() if "memory:" in l)
        kib = int(line.split()[1])
        pages = int(line.split("(")[1].split()[0])
        assert pages * 4 == kib


class TestExceptionHandling:
    """The kernel must survive - and report - a fault."""

    @staticmethod
    @pytest.fixture(scope="class")
    def crashed(image):
        return boot_with(image, "crash\r")

    def test_panic_banner_is_printed(self, crashed):
        assert "KERNEL PANIC" in crashed.serial_text()

    def test_exception_is_identified(self, crashed):
        assert "divide by zero" in crashed.serial_text()

    def test_registers_are_dumped(self, crashed):
        serial = crashed.serial_text()
        for register in ("eax", "ebx", "esp", "eip", "cr0", "cr3"):
            assert register in serial

    def test_stack_trace_is_produced(self, crashed):
        assert "call trace:" in crashed.serial_text()

    def test_system_halts_cleanly(self, crashed):
        assert "system halted." in crashed.serial_text()
