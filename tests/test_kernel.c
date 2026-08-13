#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <stdlib.h>

void vga_write(const char* msg) {
    (void)msg;
}

#include "../kernel.c"

void dummy_handler1() {}
void dummy_handler2() {}

int main() {
    printf("Starting JinoServer routes tests...\n");

    // Test 1: Normal route registration
    jserver_init();
    assert(routes_count == 0);

    jserver_route("/api/users", dummy_handler1);
    assert(routes_count == 1);
    assert(strcmp(routes[0].path, "/api/users") == 0);
    assert(routes[0].handler == dummy_handler1);

    // Test 2: Max routes capacity
    for (int i = 1; i < MAX_ROUTES; i++) {
        char path[32];
        sprintf(path, "/api/test%d", i);
        jserver_route(path, dummy_handler2);
    }
    assert(routes_count == MAX_ROUTES);

    // Test 3: Exceeding max routes
    jserver_route("/api/overflow", dummy_handler1);
    assert(routes_count == MAX_ROUTES);

    // Test 4: Path truncation
    jserver_init();
    char long_path[100];
    for (int i = 0; i < 99; i++) {
        long_path[i] = 'A';
    }
    long_path[99] = '\0';

    jserver_route(long_path, dummy_handler1);
    assert(routes_count == 1);
    assert(strlen(routes[0].path) == 63); // Max path length is 63
    assert(routes[0].path[62] == 'A');
    assert(routes[0].path[63] == '\0');

    printf("All JinoServer route tests passed successfully!\n");
    return 0;
}
