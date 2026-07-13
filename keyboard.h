{
  "lang_name": "English",
  "lang_code": "en",
  "boot": {
    "title": "Jino OS v3.0 Hybrid Edition",
    "subtitle": "Console + GUI + Easy Server Installer",
    "select_language": "Select system language / Выберите язык системы:",
    "options": "1) English (EN)  2) Русский (RU)",
    "prompt": "Choose [1-2, default EN]: ",
    "chosen": "Language set to English. System will boot in English.",
    "loading_kernel": "Loading JinoKernel 3.0...",
    "loading_mem": "Memory Manager: 32 MB",
    "loading_fs": "JinoFS v3 mounted",
    "loading_gui": "JinoGUI Window Manager ready (type 'gui' or 'startx' to launch)",
    "loading_servers": "Server Manager ready",
    "loading_repo": "Package repository",
    "loading_errors": "Error system loaded",
    "loading_curl": "curl loaded",
    "ok": "[OK]"
  },
  "motd": "Welcome to Jino OS v3.0 Hybrid! Console is primary, GUI is optional. Type 'help', 'gui', 'jpkg list'",
  "help": {
    "title": "Jino OS v3.0 Hybrid - Help",
    "intro": "Hybrid Edition: Console is main, GUI is optional layer. No GUI removed - it coexists.",
    "quick": "QUICK START:",
    "quick_items": [
      "help - this help",
      "cmds - list all 100+ commands",
      "errors - list all error codes with explanations",
      "gui / startx / jindowm - launch graphical interface (window manager)",
      "exit-gui / console - return to console from GUI",
      "jpkg list - list available server packages (18)",
      "srv list - list installed servers",
      "curl --help - full curl manual"
    ],
    "fs": "FILE SYSTEM:",
    "fs_items": "ls, dir, ll, la, pwd, cd, cat, bat, mkdir, rmdir, rm -r, cp, mv, find, tree, du, df",
    "text": "TEXT PROCESSING:",
    "text_items": "echo, write, edit, head, tail, wc, grep, hexdump, base64, diff",
    "sys": "SYSTEM:",
    "sys_items": "ver, uname, sysinfo, date, clear, history, mem, ps, top, reboot, shutdown",
    "net": "NETWORK / SERVERS / CURL:",
    "net_items": "curl <url> [-o file] [-X POST] [-d data] [-H header] [-i] [-v], wget, ping, ifconfig, jpkg, srv, deploy, jdb",
    "gui": "GRAPHICAL INTERFACE (NEW in v3.0):",
    "gui_items": [
      "gui / startx - start JinoWM graphical desktop (keeps console underneath)",
      "gui --browser - open browser hybrid desktop (emulator/index.html)",
      "In GUI: Terminal app still available - console never removed",
      "File Manager, Browser, Editor, Server Monitor in GUI",
      "Type 'man gui' for GUI manual"
    ]
  },
  "errors": {
    "title": "Full error list Jino OS (23 codes)",
    "detail_prompt": "For details: errors JNO-001 or errors 001"
  },
  "curl": {
    "help_title": "curl - Jino OS Full Implementation v3.0",
    "usage": "Usage: curl [options] <url>"
  },
  "gui": {
    "starting": "Starting JinoGUI Window Manager...",
    "started": "JinoGUI started. Desktop environment loaded.",
    "desktop": "Desktop: double-click icons, right-click for menu, Terminal keeps console",
    "exit": "Exiting GUI, returning to console...",
    "not_available": "GUI not available in pure console mode, but you can open emulator/index.html in browser for Hybrid GUI",
    "browser_hint": "Browser Hybrid GUI: open file emulator/index.html"
  },
  "server": {
    "installer": "Easy Server Installer: jpkg + srv",
    "list": "Available packages: nginx, apache, api-server, file-server, nodejs, wordpress, mysql, etc. Use jpkg list"
  },
  "prompt": {
    "console": "jino@jino-pc",
    "gui": "Jino GUI Terminal"
  }
}
