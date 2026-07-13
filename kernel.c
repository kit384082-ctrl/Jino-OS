#include "jserver.h"
#include "../drivers/vga.h"
// Упрощенный HTTP сервер - работает через JinoNet стек
// В реале слушает сокеты, тут заглушка

static int routes_count=0;
#define MAX_ROUTES 16
typedef struct { char path[64]; void (*handler)(); } route_t;
static route_t routes[MAX_ROUTES];

void jserver_init(){
    vga_write("[OK] JinoServer init on :80\n");
    routes_count=0;
}
void jserver_route(const char* path, void (*handler)()){
    if(routes_count>=MAX_ROUTES) return;
    // strcpy simplified
    int i=0; while(path[i] && i<63){ routes[routes_count].path[i]=path[i]; i++; } routes[routes_count].path[i]=0;
    routes[routes_count].handler=handler;
    routes_count++;
}
void jserver_listen(int port){
    vga_write("JinoServer listening...\n");
}
