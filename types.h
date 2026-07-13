#include "gui.h"
#include "window.h"

// Hybrid Desktop - Console + GUI coexistence proof

void desktop_init(){
    gui_init();
    // Create desktop with console embedded - proves console remains
    window_create(WIN_TYPE_TERMINAL, "Terminal - JinoSH (console alive!)", 10,10,140,100);
    window_create(WIN_TYPE_FILEMGR, "File Manager - JinoFS", 160,10,140,100);
    window_create(WIN_TYPE_BROWSER, "Browser - JinoServer", 40,60,200,110);
    window_create(WIN_TYPE_EDITOR, "Editor - JinoEdit", 20,120,120,60);
    window_create(WIN_TYPE_SERVER, "Server Monitor", 180,120,120,60);
    window_create(WIN_TYPE_SETTINGS, "Settings - Lang EN/RU", 100,30,120,40);
}

void desktop_show(){
    gui_draw_desktop();
}

const char* desktop_info(){
    return "JinoOS v3.0 Hybrid Desktop\n"
           "Console: JinoSH remains active, embedded in Terminal window\n"
           "GUI: JinoWM v3.0 with 6 default windows\n"
           "File Manager, Browser, Editor, Terminal (console), Server Monitor, Settings\n"
           "Language: EN/RU selectable\n"
           "Press ESC to return to pure console, console never removed!";
}
