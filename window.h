#include "vga.h"
static uint16_t* vga_buffer = (uint16_t*)0xB8000;
static uint8_t cursor_x=0, cursor_y=0;
static uint8_t color=0x0A;

void vga_init(){ cursor_x=0; cursor_y=0; vga_clear(); }
void vga_set_color(uint8_t fg, uint8_t bg){ color = fg | bg<<4; }
void vga_clear(){
    for(int y=0;y<25;y++) for(int x=0;x<80;x++) vga_buffer[y*80+x]=(color<<8)|' ';
    cursor_x=0; cursor_y=0;
}
static void scroll(){
    if(cursor_y>=25){
        for(int y=0;y<24;y++) for(int x=0;x<80;x++) vga_buffer[y*80+x]=vga_buffer[(y+1)*80+x];
        for(int x=0;x<80;x++) vga_buffer[24*80+x]=(color<<8)|' ';
        cursor_y=24;
    }
}
void vga_putc(char c){
    if(c=='\n'){ cursor_x=0; cursor_y++; scroll(); return; }
    if(c=='\r'){ cursor_x=0; return; }
    if(c=='\b'){ if(cursor_x>0){cursor_x--; vga_buffer[cursor_y*80+cursor_x]=(color<<8)|' ';} return; }
    vga_buffer[cursor_y*80+cursor_x]=(color<<8)|c;
    cursor_x++; if(cursor_x>=80){cursor_x=0; cursor_y++; scroll();}
}
void vga_write(const char* s){ while(*s) vga_putc(*s++); }

void vga_set_mode_graphics_320x200(){
    // через порты VGA - упрощено, реальная инициализация требует BIOS int 10h в бутлоадере
    // Здесь просто заглушка, в реале бутлоадер должен установить 0x13
}
void vga_put_pixel(int x, int y, uint8_t color){
    uint8_t* fb = (uint8_t*)0xA0000;
    fb[y*320+x]=color;
}
