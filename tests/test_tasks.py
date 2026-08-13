"""Kernel threads: creation, context switching and teardown."""

import re

import pytest

from conftest import boot_with


@pytest.fixture(scope="module")
def spawned(image):
    return boot_with(image, "spawn\rps\r")


class TestTaskCreation:
    def test_the_kernel_task_exists_at_boot(self, image):
        output = boot_with(image, "ps\r").screen_text()
        assert "kernel" in output
        assert "running" in output

    def test_spawn_reports_a_new_task_id(self, spawned):
        assert re.search(r"spawned task \d+", spawned.screen_text())

    def test_the_worker_actually_runs(self, spawned):
        assert "worker running" in spawned.screen_text()


class TestContextSwitching:
    def test_the_worker_is_scheduled_repeatedly(self, spawned):
        """Each iteration means a full switch out to the shell and back."""
        iterations = re.findall(r"worker running, iteration (\d+)", spawned.screen_text())
        assert len(iterations) == 3
        assert iterations == ["0", "1", "2"]

    def test_control_returns_to_the_shell(self, spawned):
        """After the worker exits, the prompt must come back."""
        screen = spawned.screen_text()
        position = screen.index("worker running, iteration 2")
        assert "jino>" in screen[position:]

    def test_the_shell_still_works_afterwards(self, image):
        output = boot_with(image, "spawn\runame\r").screen_text()
        assert "Jino-OS 1.0 i386" in output

    def test_the_kernel_task_accumulated_time(self, spawned):
        """Yielding back and forth should show up in the tick count."""
        line = next(
            l for l in spawned.screen_text().splitlines() if l.strip().startswith("0 ")
        )
        assert int(line.split()[-1]) > 0


class TestTaskTeardown:
    def test_the_finished_task_is_removed_from_the_list(self, spawned):
        """Once the worker returns, only the kernel task should remain."""
        screen = spawned.screen_text()
        listing = screen[screen.index("id  name"):]
        assert "worker" not in listing

    def test_repeated_spawning_does_not_exhaust_memory(self, image):
        """The stack of an exited task has to find its way back."""
        machine = boot_with(image, "spawn\rspawn\rspawn\rheap\r")
        output = machine.screen_text()
        assert output.count("spawned task") == 3
        assert "heap is consistent" in output

    def test_task_stacks_are_returned_to_the_heap(self, image):
        """A regression guard: exited tasks used to leak their stacks."""
        output = boot_with(image, "spawn\rspawn\rspawn\rmem\r").screen_text()
        heap_line = next(l for l in output.splitlines() if l.startswith("heap"))
        used = int(heap_line.split(",")[1].split()[0])
        assert used == 0, f"{used} bytes still held after the tasks exited"

    def test_the_heap_coalesces_after_the_tasks_exit(self, image):
        """Freed stacks must merge back into one block, not fragment."""
        output = boot_with(image, "spawn\rspawn\rspawn\rheap\r").screen_text()
        listing = output[output.index("#   address"):]
        assert listing.count("free") == 1
        assert "used" not in listing

    def test_no_panic_during_the_task_lifecycle(self, spawned):
        assert "KERNEL PANIC" not in spawned.serial_text()


class TestPreemption:
    """The timer must be able to take the CPU from a task that never yields."""

    @staticmethod
    @pytest.fixture(scope="class")
    def preempted(image):
        return boot_with(image, "preempt\rps\runame\r", timer=5_000)

    def test_the_spinner_makes_progress(self, preempted):
        """The shell busy-waits; only preemption lets the spinner run."""
        match = re.search(
            r"preempted spinner reached (\d+) iterations", preempted.screen_text()
        )
        assert match, f"unexpected output: {preempted.screen_text()}"
        assert int(match.group(1)) > 0

    def test_control_returns_to_the_shell(self, preempted):
        assert "Jino-OS 1.0 i386" in preempted.screen_text()

    def test_the_spinner_is_cleaned_up(self, preempted):
        screen = preempted.screen_text()
        listing = screen[screen.index("id  name"):]
        assert "spinner" not in listing

    def test_no_panic_under_preemption(self, preempted):
        assert "KERNEL PANIC" not in preempted.serial_text()

    def test_interrupts_are_still_acknowledged(self, preempted):
        """A missed EOI would stop the timer, so ticks must keep coming."""
        line = next(
            l for l in preempted.screen_text().splitlines() if l.strip().startswith("0 ")
        )
        assert int(line.split()[-1]) > 0
