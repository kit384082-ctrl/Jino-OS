#ifndef JSERVER_H
#define JSERVER_H
// JinoServer - встроенный HTTP сервер на уровне ядра
void jserver_init();
void jserver_listen(int port);
void jserver_route(const char* path, void (*handler)());
#endif
