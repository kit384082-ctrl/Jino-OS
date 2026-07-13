#include "gui.h"
#include "../drivers/vga.h"
#include "../lib/types.h"
#include "../kernel/memory.h"

#define MAX_WINDOWS 16
#define SCREEN_W 320
#define SCREEN_H 200

typedef struct {
    int x,y,w,h;
    char title[32];
    int used;
    int active;
    uint8_t* buffer; // window buffer
    int z_order;
} window_t;

static window_t windows[MAX_WINDOWS];
static int next_z=0;
static int gui_mode=0; // 0=text, 1=graphics
static int mouse_x=160, mouse_y=100;

void gui_init(){
    for(int i=0;i<MAX_WINDOWS;i++) windows[i].used=0;
    gui_mode=0;
    next_z=0;
}

void gui_early_init(){ gui_init(); }

void gui_draw_desktop(){
    // Draw background - teal
    for(int y=0;y<SCREEN_H;y++){
        for(int x=0;x<SCREEN_W;x++){
            uint8_t col = 3; // cyan
            if((x/10 + y/10)%2==0) col=3;
            else col=11;
            vga_put_pixel(x,y,col);
        }
    }
    // Taskbar at bottom
    for(int y=SCREEN_H-20;y<SCREEN_H;y++){
        for(int x=0;x<SCREEN_W;x++){
            vga_put_pixel(x,y,7); // gray
        }
    }
    // Start button
    for(int y=SCREEN_H-18;y<SCREEN_H-2;y++){
        for(int x=2;x<60;x++){
            vga_put_pixel(x,y,10); // green
        }
    }
}

static void draw_window(window_t* win){
    // window border and title bar
    int wx=win->x, wy=win->y, ww=win->w, wh=win->h;
    // border
    for(int y=wy;y<wy+wh;y++){
        for(int x=wx;x<wx+ww;x++){
            if(x<0||x>=SCREEN_W||y<0||y>=SCREEN_H) continue;
            uint8_t col=7;
            if(y==wy) col=15; // title top white
            else if(y==wy+10) col=0; // title bottom
            else if(y<wy+10) col= (win->active ? 1 : 8); // title bar blue/gray
            else col=7; // body
            vga_put_pixel(x,y,col);
        }
    }
    // title text would be drawn via font (simulated)
}

void gui_enter(){
    gui_mode=1;
    vga_set_mode_graphics_320x200();
    gui_draw_desktop();
    
    // Create default windows: Terminal (console remains!), File Manager, Browser
    // Terminal window - shows console is still alive
    window_t* term=&windows[0];
    term->used=1; term->active=1;
    term->x=10; term->y=10; term->w=140; term->h=100;
    for(int i=0;i<32 && "Terminal - JinoSH (console alive)"[i];i++) term->title[i]="Terminal - JinoSH (console alive)"[i];
    term->z_order=next_z++;

    window_t* files=&windows[1];
    files->used=1; files->active=0;
    files->x=160; files->y=10; files->w=140; files->h=100;
    for(int i=0;i<32 && "File Manager - JinoFS"[i];i++) files->title[i]="File Manager - JinoFS"[i];
    files->z_order=next_z++;

    window_t* browser=&windows[2];
    browser->used=1; browser->active=0;
    browser->x=40; browser->y=60; browser->w=200; browser->h=110;
    for(int i=0;i<32 && "Browser - JinoServer :80"[i];i++) browser->title[i]="Browser - JinoServer :80"[i];
    browser->z_order=next_z++;

    // Draw all windows sorted by z
    for(int z=0;z<next_z;z++){
        for(int i=0;i<MAX_WINDOWS;i++){
            if(windows[i].used && windows[i].z_order==z) draw_window(&windows[i]);
        }
    }

    // Simple GUI loop - wait for keyboard to exit
    while(gui_mode){
        // In real OS, handle mouse, keyboard, window events
        // For now, press ESC to exit GUI back to console
        // This would be handled by keyboard ISR
        asm volatile("hlt");
        // Check if exit requested (simulated)
        // gui_mode would be set to 0 by gui_exit()
    }

    // Return to text mode
    vga_init();
}

void gui_exit(){
    gui_mode=0;
}

int jgui_create_window(const char* title, int x, int y, int w, int h){
    for(int i=0;i<MAX_WINDOWS;i++){
        if(!windows[i].used){
            windows[i].used=1;
            windows[i].x=x; windows[i].y=y; windows[i].w=w; windows[i].h=h;
            windows[i].active=0;
            windows[i].z_order=next_z++;
            int j=0;
            while(title[j] && j<31){ windows[i].title[j]=title[j]; j++; }
            windows[i].title[j]=0;
            if(gui_mode) draw_window(&windows[i]);
            return i;
        }
    }
    return -1;
}

void jgui_draw_rect(int win, int x,int y,int w,int h, int color){
    if(win<0||win>=MAX_WINDOWS||!windows[win].used) return;
    window_t* wptr=&windows[win];
    for(int yy=y;yy<y+h;yy++){
        for(int xx=x;xx<x+w;xx++){
            int sx=wptr->x+xx;
            int sy=wptr->y+10+yy;
            if(sx>=0&&sx<SCREEN_W&&sy>=0&&sy<SCREEN_H){
                vga_put_pixel(sx,sy,color);
            }
        }
    }
}

void jgui_draw_text(int win, int x, int y, const char* text, int color){
    // Simplified text drawing in window - would use font bitmap
}
