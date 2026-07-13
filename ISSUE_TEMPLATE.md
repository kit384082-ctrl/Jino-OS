# 🚀 Jino OS - С чего начать

Ты попросил полноценную ОС Jino - я сделал 3 уровня:

## 1. LEVEL 0 - Настоящее ядро (C + ASM)
Папка `src/`
- `boot/boot.asm` - бутлоадер который переводит CPU из 16-bit Real Mode в 32-bit Protected Mode и загружает ядро
- `kernel/kernel.c` - ядро JinoKernel
- `kernel/memory.c` - менеджер памяти (куча с coalescing)
- `drivers/vga.c` / `keyboard.c` - драйверы
- `shell/shell.c` - JinoSH
- `gui/gui.c` - JinoWM оконный менеджер VGA 320x200
- `fullstack/jserver.c + jdb.c` - FullStack: HTTP сервер + БД внутри ядра
- `Makefile` + `linker.ld` - сборка в ISO для QEMU/VirtualBox

Это компилируется в `jino.iso`:
```bash
make iso
qemu-system-i386 -cdrom jino.iso
```

## 2. LEVEL 1 - Консольная ОС (Python) - работает ПРЯМО СЕЙЧАС
```bash
python3 tools/jino_console.py
```
Полная эмуляция:
- JinoFS с файлами и папками
- Процессы ps
- Память mem
- JinoDB (jdb set/get/list)
- JinoServer (server start)
- JinoScript (.japp файлы)
- Команды: help, ls, cd, cat, echo, touch, mkdir, rm, write, gui, run, ver

## 3. LEVEL 2 - Графическая ОС в браузере (FullStack GUI) - работает ПРЯМО СЕЙЧАС
Открой `emulator/index.html` - это полноценный Windows 98-подобный рабочий стол:

Иконки:
- 📁 My Computer - файловый менеджер JinoFS
- 💻 JinoSH Terminal - терминал
- 📝 Notepad - редактор с сохранением в FS
- 🌐 JinoServer - встроенный веб сервер (смотрит /www/index.html через iframe)
- 🗄️ JinoDB - база данных с SET/GET
- ℹ️ About

Фишки GUI:
- Перетаскивание окон
- Панель задач с кнопкой Start Jino
- Правый клик по рабочему столу
- Анимация загрузки BIOS

## FullStack концепция Jino

Jino задумана как первая ОС где FullStack встроен в ядро:

```
[App: hello.japp]
    ↓
[JinoGUI] → отрисовка окна
[JinoServer] → route("/api/data", handler) - http сервер в ядре
[JinoDB] → db.set("key","value") - база на уровне FS
[JinoFS] → файлы /www/index.html отдаются сервером
```

Пример приложения:
```js
// /apps/myapp.japp
window.create("My Jino App", 100,100,300,200);
server.route("/api/hello", () => "Hello from Jino OS!");
db.set("counter", (db.get("counter")||0)+1);
print("App started");
```

## Что дальше?
- v0.5: пайпы, ELF loader, network драйвер NE2000
- v1.0: TCP/IP стек, DooM порт, браузер JinoBrowse
- v2.0: компилятор GCC внутри ОС

Все файлы уже у тебя в workspace. Запускай!
