# 🌀 Jino OS v3.1 Hybrid - Windows-like GUI + Console + Easy Server Installer

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version: 3.1](https://img.shields.io/badge/Version-3.1-blue.svg)
![Platform: i386](https://img.shields.io/badge/Platform-i386%20%7C%20Python%20%7C%20Browser-green.svg)
![Language: EN/RU](https://img.shields.io/badge/Lang-EN%2FRU-brightgreen.svg)
![Mode: Hybrid](https://img.shields.io/badge/Mode-Console%20%2B%20GUI-orange.svg)

**DOS-based FullStack OS with Windows-like GUI, but console remains primary and alive inside Terminal (like cmd.exe in Windows). Translated to English, language selection before installation.**

> **Hybrid Philosophy:** Console is primary, GUI is optional layer on top - console never removed! GUI is Windows-like, but Terminal app **is** the main console.

---

## ✨ Features v3.1

### 🌍 Language Selection Before Installation (Fixed!)
- **At first boot:** `Select system language: 1) English (EN) 2) Русский (RU)`
- Choice saved to `/tmp/jino_config.json`, can switch anytime: `lang en` | `lang ru`
- Browser GUI: language selector overlay with animations, fixed buttons (now work!), EN/RU indicator in taskbar, Settings app
- All messages translated: `lang/en.json`, `lang/ru.json`
- **FIXED:** Language buttons now work 100% - with hover animations, click events, localStorage, reset button

### 🖥️ Windows-like GUI - Gradual Progress, Console Stays!
- **Windows 10/11 style:** Start button (⊞ Start Jino), taskbar, draggable windows with title bar (─ □ ✕), task buttons, clock, language indicator
- **Desktop icons:** 💻 Terminal (console alive! cmd.exe), 📁 This PC/File Explorer, 📝 Notepad, 🌐 Browser Edge, 🗄️ Database, ⚠️ Errors, ⚙️ Settings, ℹ️ About, 🗑️ Recycle Bin - double-click to open
- **Animations:** fadeIn, slideUp, scaleIn for boot, window open/close, Start menu slide, icons hover lift, typewriter boot logs
- **Hybrid proof:** Terminal window IS the main console with 100+ commands, jpkg, srv, curl, errors - same JinoFS. `gui` command in console launches GUI simulation, `exit-gui` returns to pure console but console was never removed.
- **Real kernel GUI:** `src/gui/gui.c` VGA 320x200 + 80x25 text, `window.c`, `desktop.c` with 6 default windows
- **Browser:** `emulator/index.html` - Windows-like desktop with console terminal embedded

### 💻 Console (Primary, Never Removed!)
- 100+ commands: `ls`, `cat`, `mkdir`, `rm`, `echo`, `head`, `tail`, `grep`, `hexdump`, `base64`, `mem`, `ps`, `calc`, `cowsay`
- `tools/jino_console.py` v3.1 - Python implementation with real HTTP servers

### 📦 Easy Server Installer (jpkg + srv)
- **18 packages:** nginx, apache, jino-web, file-server, api-server, python-api, nodejs, php-server, wordpress, mysql, postgres, redis, chat-server, game-server, minecraft + templates static, express, flask
- `jpkg list`, `jpkg search nginx`, `jpkg install nginx --port 8080 --name myweb`, `jpkg info`, `jpkg uninstall`
- `srv list`, `srv create`, `srv start`, `srv stop`, `srv restart --all`, `srv status`, `srv logs`, `srv delete`, `srv new` (wizard), `srv quick nginx` (install+start), `deploy . --port 8000 --name site`

### 🌐 Full curl Implementation
- Real HTTP via urllib: `-X METHOD`, `-H header`, `-d data`, `-d @file`, `-o file`, `-O`, `-i`, `-v`, `-L`, `--connect-timeout`, `-u user:pass`
- Protocols: `http://`, `https://`, `file:///www/index.html`, `/www/index.html`, `localhost:8080`
- `curl --help`, `wget` alias
- Methods: GET, POST, PUT, DELETE, PATCH, HEAD
- Saves to JinoFS: `curl http://localhost:8080/ -o /tmp/page.html`

### ⚠️ Full Error Explanations (23 codes JNO-001..023)
- Each error with border, title, message, context, cause, fix, example
- Example `cat /nope.txt` -> JNO-001 with full box
- `errors` list all, `errors JNO-001` detail, auto triggered on every failing command
- Includes: file not found, dir not found, is dir, not dir, permission denied, file exists, dir not empty, command not found, invalid args, port in use, server not found, package not found, already running, not running, invalid port/path, connection refused, timeout, invalid URL, HTTP error, write error, JDB key not found, invalid method

### 🎨 Animations (New in v3.1)
- Boot: typewriter logs with slideUp
- Language selector: fadeIn + scaleIn, buttons hover with gradient shine and lift
- Desktop icons: slideUp staggered, hover lift + scale + shadow
- Windows: scaleIn with cubic-bezier bounce, closing reverse
- Taskbar: slideUp, Start menu slideUp, hover effects
- Terminal: fadeIn, etc.

### 📄 GitHub Ready
- **LICENSE:** MIT - easy, permissive, free for commercial use, keep copyright. See `LICENSE` file.
- **README.md:** GitHub badges, features, quick start, structure, screenshots description
- **.gitignore:** Python, build, runtime, OS, IDE
- **CONTRIBUTING.md:** How to contribute
- `docs/SERVERS.md`, `docs/CURL.md`, `docs/ERRORS.md`, `docs/architecture.md`

---

## 🚀 Quick Start

### Console (primary)

```bash
git clone https://github.com/yourname/Jino-OS.git
cd Jino-OS
python3 tools/jino_console.py
```

On first boot:
```
============================================================
  Jino OS v3.0 Hybrid Edition
  Console + GUI + Easy Server Installer
============================================================
Select system language / Выберите язык системы:
  1) English (EN)  2) Русский (RU)
Choose [1-2, default EN]: 1
Language set to English
[OK] JinoKernel 3.0 Hybrid loaded
...
Welcome to Jino OS v3.0 Hybrid! Console is primary, GUI optional.
Type help, gui for GUI, jpkg list, lang en|ru
```

Try:
```bash
help
lang ru
help  # now in Russian
lang en

ls
cat /readme.txt
mkdir /www/mysite
echo "<h1>Hello Jino</h1>" > /www/mysite/index.html

jpkg list
jpkg install nginx --port 8080 --name myweb
srv list
srv start myweb
curl http://localhost:8080/ -i -v
curl http://localhost:8080/api/status
curl file:///www/index.html -o /tmp/copy.html

errors
errors JNO-001
cat /nope.txt  # triggers JNO-001 with full explanation

gui  # launch Windows-like GUI simulation in console (ASCII)
# Inside GUI sim: terminal, files, exit-gui

ver
```

### Graphical Hybrid (browser, Windows-like)

Open `emulator/index.html` in browser:

1. **Language selector overlay** appears first - click **English** or **Русский** (FIXED! Now buttons work with hover animations and shine effect)
2. Boot logs with typewriter animation in selected language
3. Desktop appears with fadeIn animation - icons slideUp staggered
4. Taskbar slideUp - Start Jino button, EN/RU indicator (click to switch), clock
5. Double-click **Terminal** - full console inside GUI, same 100+ commands, `jpkg list`, `srv list`, `curl --help`, `errors`, `lang en|ru` - proves console alive!
6. Double-click **This PC**, **Browser**, **Errors**, **Settings** - Windows with scaleIn animation
7. Start menu with slideUp animation, Programs list
8. Settings -> switch EN/RU, shows MIT License

- `emulator/index.html` - v3.1 Hybrid Windows-like + animations + fixed lang buttons
- `emulator/console_server.html` - pure console server edition
- `emulator/console.html` - simple console

### Kernel Build (real ISO)

Requires `i686-elf-gcc`, `nasm`, `grub-mkrescue`

```bash
make iso
qemu-system-i386 -cdrom jino.iso -m 64
# In QEMU: select language, help, gui -> enters VGA 320x200 desktop, ESC to return to console
```

---

## 📁 Project Structure

```
JinoOS/
├── tools/jino_console.py      # Main OS: console + GUI launcher + server manager + curl + errors + lang
├── lang/en.json, ru.json      # Translations (EN/RU)
├── packages/repo.json         # 18 server packages repo
├── emulator/
│   ├── index.html             # Hybrid Windows-like GUI + Console + EN/RU selector + animations (FIXED buttons)
│   ├── console_server.html    # Pure console server edition
│   └── console.html           # Simple console
├── src/
│   ├── boot/boot.asm          # Bootloader 16->32 bit MBR
│   ├── kernel/kernel.c        # JinoKernel 3.0 Hybrid with jino_lang
│   ├── drivers/vga.c, keyboard.c
│   ├── shell/shell.c          # JinoSH with gui, lang commands
│   ├── gui/gui.h, gui.c, window.h, window.c, desktop.c # JinoWM v3.1 Windows-like, console remains
│   └── fullstack/jdb.c, jserver.c, jserver.h
├── docs/
│   ├── SERVERS.md             # Server installer guide
│   ├── CURL.md                # curl full manual
│   ├── ERRORS.md              # 23 errors full explanations
│   └── architecture.md
├── templates/                 # Server templates
├── LICENSE                    # MIT License - easy permissive
├── README.md                  # This file (GitHub ready, English)
├── CONTRIBUTING.md
├── .gitignore
└── Makefile, linker.ld
```

---

## 🔧 Commands Cheat Sheet

### Language
```bash
lang en | lang ru | lang --list
# Switch anytime, saved to /tmp/jino_config.json
```

### File System
```bash
ls, ll, la, pwd, cd, cat, bat, mkdir, rmdir, rm -r, cp, mv, find, tree, du, df, stat
```

### Text
```bash
echo "hi" > /tmp/hi.txt
echo "more" >> /tmp/hi.txt
cat /tmp/hi.txt
head -n 5 /readme.txt
tail -n 5 /readme.txt
wc /readme.txt
grep hello /readme.txt
hexdump /readme.txt
base64 /readme.txt
base64 -d <encoded>
```

### System
```bash
ver, sysinfo, date, clear, history, mem, ps, top, reboot, shutdown, exit
errors, errors JNO-001
```

### Servers (Easy Installer)
```bash
jpkg list
jpkg search nginx
jpkg install nginx --port 8080 --name myweb --root /www/myweb
jpkg info nginx
jpkg uninstall myweb

srv list
srv create myblog --template static --port 8080 --root /www/myblog
srv start myblog
srv start --all
srv stop myblog
srv restart myblog
srv status myblog
srv logs myblog
srv delete myblog
srv new           # wizard
srv quick nginx   # install+start in 1

deploy . --port 9000 --name quicksite
deploy /www --port 8000
```

### Network / curl (Full)
```bash
curl --help

curl file:///www/index.html
curl /www/index.html
curl http://localhost:8080/
curl http://localhost:8080/api/status -i -v
curl http://localhost:8080/ -o /tmp/page.html -L
curl -X POST http://localhost:3000/api/jdb -d '{"k":"v"}' -H "Content-Type: application/json"
curl https://api.github.com/users/github -i
wget http://localhost:8080/ -O /tmp/wget.html

ping localhost
ifconfig
jdb set mykey myvalue
jdb get mykey
jdb list
```

### GUI (Windows-like, console remains)
```bash
gui              # launch GUI simulation in console (ASCII)
gui --browser    # try to open browser hybrid GUI
startx           # alias for gui
jindowm          # alias
exit-gui         # return to console (in GUI simulation)
# In browser GUI: double-click Terminal icon -> console alive inside!
```

---

## 🎨 Screenshots (description, as text preview)

**Language selector (fixed!):**
- Gradient background black->dark blue, box with green border and glow
- Two big buttons with flag emoji, hover lifts + green glow + shine animation
- Reset button

**Boot:**
- Black background, green text, typewriter logs appearing one by one with slide

**Desktop - Windows-like:**
- Teal radial gradient wallpaper
- Icons: Terminal (cmd.exe), This PC, Notepad, Browser Edge, Database, Errors, Settings, About, Recycle Bin - hover lifts
- Taskbar: dark gradient, Start button (⊞ Start Jino) with hover, task buttons with bottom blue border for active, EN/RU indicator, clock

**Window:**
- Rounded corners, blue title bar gradient #0078d7, shadow, controls ─ □ ✕ (close red on hover)
- ScaleIn animation on open (bounce)

**Terminal inside GUI:**
- Black #0c0c0c, green #0f0 input, cmd.exe style, full console commands

---

## 📝 License - MIT (Easy)

MIT License is the easiest, most permissive - free for commercial use, private use, modification, distribution. Just keep copyright notice.

See `LICENSE` file for full text.

```
MIT License - Copyright (c) 2026 Jino OS - 
Permission is hereby granted...
```

Why MIT? As you requested "лицензию полегче" (easier license) - MIT is easiest.

---

## 🤝 Contributing

See `CONTRIBUTING.md`

Quick:
```bash
git checkout -b feature/my-feature
# edit tools/jino_console.py or emulator/index.html
python3 tools/jino_console.py  # test
git commit -m "Add feature"
git push
# PR
```

---

## 📦 Build Info

- Version: 3.1 Hybrid
- Build: 2026-07-13
- Language: EN/RU selectable at boot (default EN)
- Mode: Console primary + GUI optional (hybrid, Windows-like)
- Files: 20+ in JinoFS
- Servers: 18 packages
- Errors: 23 codes with full explanations
- curl: Full implementation
- GUI: Windows-like with animations, console remains
- GitHub: Ready with LICENSE MIT, README, .gitignore, CONTRIBUTING
- 

---

## 🔗 Links

- Emulator: `emulator/index.html` (Windows-like Hybrid, fixed lang buttons + animations)
- Console Server: `emulator/console_server.html`
- Docs: `docs/SERVERS.md`, `docs/CURL.md`, `docs/ERRORS.md`
- Kernel: `src/kernel/kernel.c` Hybrid
- GUI: `src/gui/` JinoWM v3.1

---

**Jino OS v3.1 Hybrid - Windows-like GUI + Console alive (like cmd.exe in Windows) - EN/RU - GitHub Ready - MIT - Animations Fixed!**
