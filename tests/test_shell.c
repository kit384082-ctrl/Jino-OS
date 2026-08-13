#include <stdio.h>
#include <assert.h>
#include <stdint.h>

// Mock vga functions
int vga_put_pixel_called = 0;
void vga_put_pixel(int x, int y, int color) {
    vga_put_pixel_called = 1;
}
void vga_set_mode_graphics_320x200() {}
void vga_init() {}

// Define TEST_MODE so shell.c doesn't include other broken headers
#define TEST_MODE

// Include the source file we want to test
#include "../shell.c"

int main() {
    gui_init();

    // Test 1: invalid window ID (-1)
    vga_put_pixel_called = 0;
    jgui_draw_rect(-1, 0, 0, 10, 10, 0);
    assert(vga_put_pixel_called == 0);

    // Test 2: invalid window ID (MAX_WINDOWS)
    vga_put_pixel_called = 0;
    jgui_draw_rect(MAX_WINDOWS, 0, 0, 10, 10, 0);
    assert(vga_put_pixel_called == 0);

    // Test 3: unused window ID (0)
    vga_put_pixel_called = 0;
    jgui_draw_rect(0, 0, 0, 10, 10, 0);
    assert(vga_put_pixel_called == 0);

    // Test 4: Valid window, should call vga_put_pixel
    int win_id = jgui_create_window("Test", 10, 10, 50, 50);
    assert(win_id >= 0);

    vga_put_pixel_called = 0;
    jgui_draw_rect(win_id, 0, 0, 10, 10, 0);
    assert(vga_put_pixel_called == 1);

    printf("All jgui_draw_rect tests passed!\n");
    return 0;
}
