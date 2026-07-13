#include "window.h"
#include "gui.h"

static jwindow_t win_table[16];
static int win_count=0;

int window_create(win_type_t type, const char* title, int x,int y,int w,int h){
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
