"""Ring 3: dropping to user mode, system calls and the barrier between them."""

import re

import pytest

from conftest import boot_with


@pytest.fixture(scope="module")
def demo(image):
    """The sample user program, run to completion."""
    return boot_with(image, "user\r", timer=5000)


@pytest.fixture(scope="module")
def faulter(image):
    """The user program that tries to read kernel memory."""
    return boot_with(image, "user fault\r", timer=5000)


class TestEnteringUserMode:
    def test_the_shell_announces_the_switch(self, demo):
        assert "dropping to ring 3" in demo.screen_text()

    def test_user_code_actually_runs(self, demo):
        assert "[ring 3] hello from user mode" in demo.screen_text()

    def test_control_comes_back_to_the_kernel(self, demo):
        assert "back in ring 0" in demo.screen_text()

    def test_the_machine_returns_to_the_prompt(self, demo):
        # Reaching the prompt means the return path unwound cleanly
        # rather than leaving the kernel stranded on the wrong stack.
        assert demo.stop_reason == "idle: waiting for input"


class TestSystemCalls:
    def test_write_reaches_the_screen(self, demo):
        assert "[ring 3] exiting" in demo.screen_text()

    def test_version_is_copied_out_to_the_caller(self, demo):
        # The string lives in kernel memory; ring 3 only ever sees the
        # copy the kernel made in its buffer.
        assert "Jino-OS 1.0" in demo.screen_text()

    def test_uptime_comes_back_as_a_number(self, demo):
        assert re.search(r"\d+ ms since boot", demo.screen_text())

    def test_every_call_the_program_made_was_counted(self, demo):
        match = re.search(r"(\d+) system call\(s\), (\d+) rejected", demo.screen_text())
        assert match, "the shell did not report the call counters"
        assert int(match.group(1)) == 9
        assert int(match.group(2)) == 0

    def test_the_exit_code_survives_the_trip(self, demo):
        assert "exited with 42" in demo.screen_text()


class TestMemoryProtection:
    def test_a_pointer_into_the_kernel_is_refused(self, faulter):
        assert "the kernel refused, as it should" in faulter.screen_text()

    def test_the_program_does_not_get_away_with_it(self, faulter):
        assert "which is a bug" not in faulter.screen_text()

    def test_the_refusal_is_counted(self, faulter):
        match = re.search(r"(\d+) system call\(s\), (\d+) rejected", faulter.screen_text())
        assert match, "the shell did not report the call counters"
        assert int(match.group(2)) == 1

    def test_the_kernel_survives_the_attempt(self, faulter):
        assert "exited with 0" in faulter.screen_text()
        assert faulter.stop_reason == "idle: waiting for input"
