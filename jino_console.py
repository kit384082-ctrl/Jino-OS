# Инструменты Jino OS

## Консольная ОС (Python) - РАБОТАЕТ СРАЗУ
```
python3 tools/jino_console.py
```
Полноценная ОС с FS, процессами, БД, сервером.

## Графическая ОС (Browser)
Открой emulator/index.html - у тебя будет Windows-подобный рабочий стол Jino с:
- Мой компьютер (JinoFS)
- Терминал JinoSH
- Notepad
- JinoServer (FullStack веб сервер)
- JinoDB

## Сборка реального ISO
Требует i686-elf-gcc, nasm, grub

make
make run (qemu)
