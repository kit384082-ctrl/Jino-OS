#include "keyboard.h"
#include "../lib/types.h"

static uint8_t kbd_queue[256];
static int q_head=0, q_tail=0;
static char scancode_to_ascii[128] = {
 0,27,'1','2','3','4','5','6','7','8','9','0','-','=','\b',
 '\t','q','w','e','r','t','y','u','i','o','p','[',']','\n',0,
 'a','s','d','f','g','h','j','k','l',';','\'','`',0,'\\',
 'z','x','c','v','b','n','m',',','.','/',0,'*',0,' ',0,
};

void keyboard_init(){ q_head=q_tail=0; }

void keyboard_push(uint8_t scancode){
    if(scancode & 0x80) return; // отпускание
    char c = scancode_to_ascii[scancode];
    if(c){ kbd_queue[q_tail]=c; q_tail=(q_tail+1)%256; }
}

char keyboard_getchar(){
    while(q_head==q_tail){ asm volatile("hlt"); /* ждать прерывания */ }
    char c = kbd_queue[q_head];
    q_head=(q_head+1)%256;
    return c;
}

// ISR будет вызывать keyboard_handler
void keyboard_handler(){
    uint8_t scancode; asm volatile("inb $0x60, %0" : "=a"(scancode));
    keyboard_push(scancode);
}
