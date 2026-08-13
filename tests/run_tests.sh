#!/bin/bash
set -e

echo "Setting up test environment..."
mkdir -p build_test/src/kernel build_test/src/drivers
cp kernel.c build_test/src/kernel/
touch build_test/src/kernel/jserver.h
touch build_test/src/drivers/vga.h

echo "Compiling tests..."
gcc -Ibuild_test/src/kernel tests/test_kernel.c -o tests/test_runner

echo "Running tests..."
./tests/test_runner

echo "Cleaning up..."
rm -rf build_test tests/test_runner
echo "Done."
