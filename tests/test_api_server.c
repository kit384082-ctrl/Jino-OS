#include <stdio.h>
#include <assert.h>
#include <string.h>

// Mock types and headers
typedef int win_type_t;
#define WIN_TYPE_TERMINAL 1

typedef struct {
    int id;
    win_type_t type;
    int x, y, w, h;
    char title[32];
} jwindow_t;

// Mock the GUI window creation
int jgui_create_window(const char* title, int x, int y, int w, int h) {
    static int fake_id = 0;
    return fake_id++;
}

#define _WINDOW_H_
#define _GUI_H_

static jwindow_t win_table[16];
static int win_count=0;

int window_create(win_type_t type, const char* title, int x,int y,int w,int h){
    if (win_count >= 16) return -1;
    int id=jgui_create_window(title,x,y,w,h);
    if(id>=0){
        win_table[win_count].id=id;
        win_table[win_count].type=type;
        win_table[win_count].x=x; win_table[win_count].y=y;
        win_table[win_count].w=w; win_table[win_count].h=h;
        int i=0; while(title[i] && i<31){ win_table[win_count].title[i]=title[i]; i++; } win_table[win_count].title[i]=0;
        win_count++;
        // Special handling for TERMINAL - it embeds console, console not removed!
        if(type==WIN_TYPE_TERMINAL){
            // Terminal window keeps JinoSH running, so console is alive inside GUI
            // This proves console remains in system even with GUI
        }
    }
    return id;
}
void window_close(int id){ /* mark unused */ }
void window_minimize(int id){ }
void window_maximize(int id){ }
void window_focus(int id){ }
void window_list(){ }
int main() {
    win_count = 0;
    for (int i = 0; i < 16; i++) {
        char title[32];
        sprintf(title, "Window %d", i);
        int id = window_create(0, title, 10, 10, 100, 100);
        assert(id >= 0);
    }

    int id = window_create(0, "Window 17", 10, 10, 100, 100);
    assert(id == -1);

    printf("Tests passed!\n");
    return 0;
}
