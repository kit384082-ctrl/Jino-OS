#ifndef GUI_H
#define GUI_H
// JinoWM - Window Manager v3.0 Hybrid Edition
// Console remains primary, GUI is optional layer
void gui_init();
void gui_enter(); // Enter graphical mode, console stays in background
void gui_exit();  // Return to console
int jgui_create_window(const char* title, int x, int y, int w, int h);
void jgui_draw_rect(int win, int x,int y,int w,int h, int color);
void jgui_draw_text(int win, int x, int y, const char* text, int color);
void gui_draw_desktop();
#endif
