{
  "lang_name": "Русский",
  "lang_code": "ru",
  "boot": {
    "title": "Jino OS v3.0 Гибридное издание",
    "subtitle": "Консоль + Графика + Установщик серверов",
    "select_language": "Выберите язык системы / Select system language:",
    "options": "1) English (EN)  2) Русский (RU)",
    "prompt": "Выбор [1-2, по умолчанию EN]: ",
    "chosen": "Язык установлен: Русский. Система загрузится на русском.",
    "loading_kernel": "Загрузка JinoKernel 3.0...",
    "loading_mem": "Менеджер памяти: 32 MB",
    "loading_fs": "JinoFS v3 смонтирована",
    "loading_gui": "JinoGUI готов (введи 'gui' или 'startx' для запуска)",
    "loading_servers": "Менеджер серверов готов",
    "loading_repo": "Репозиторий пакетов",
    "loading_errors": "Система ошибок загружена",
    "loading_curl": "curl загружен",
    "ok": "[OK]"
  },
  "motd": "Добро пожаловать в Jino OS v3.0 Гибрид! Консоль - основа, GUI - опция. Введи 'help', 'gui', 'jpkg list'",
  "help": {
    "title": "Jino OS v3.0 Гибрид - Справка",
    "intro": "Гибридное издание: консоль - основа, графика - опциональный слой.",
    "quick": "БЫСТРЫЙ СТАРТ:",
    "quick_items": [
      "help - эта справка",
      "cmds - все 100+ команд",
      "errors - все коды ошибок",
      "gui / startx / jindowm - запустить графический рабочий стол",
      "exit-gui / console - вернуться в консоль",
      "jpkg list - список серверов",
      "srv list - установленные сервера",
      "curl --help - справка curl"
    ],
    "fs": "ФАЙЛОВАЯ СИСТЕМА:",
    "fs_items": "ls, dir, ll, la, pwd, cd, cat, bat, mkdir, rmdir, rm -r, cp, mv, find, tree, du, df",
    "text": "ТЕКСТ:",
    "text_items": "echo, write, edit, head, tail, wc, grep, hexdump, base64, diff",
    "sys": "СИСТЕМА:",
    "sys_items": "ver, uname, sysinfo, date, clear, history, mem, ps, top, reboot, shutdown",
    "net": "СЕТЬ / СЕРВЕРА / CURL:",
    "net_items": "curl <url> [-o file] [-X POST] [-d data] [-H header] [-i] [-v], wget, ping, ifconfig, jpkg, srv, deploy, jdb",
    "gui": "ГРАФИЧЕСКИЙ ИНТЕРФЕЙС (НОВОЕ в v3.0):",
    "gui_items": [
      "gui / startx - запустить графический рабочий стол (консоль остается внизу)",
      "gui --browser - открыть гибридный рабочий стол в браузере (emulator/index.html)",
      "В GUI: приложение Terminal - консоль никуда не делась",
      "Файловый менеджер, Браузер, Редактор, Монитор серверов в GUI",
      "Введи 'man gui' для справки по GUI"
    ]
  },
  "errors": {
    "title": "Полный список ошибок Jino OS (23 кода):",
    "detail_prompt": "Для деталей: errors JNO-001 или errors 001"
  },
  "curl": {
    "help_title": "curl - Jino OS Полная реализация v3.0",
    "usage": "Использование: curl [опции] <url>"
  },
  "gui": {
    "starting": "Запуск JinoGUI...",
    "started": "JinoGUI запущен. Рабочий стол загружен.",
    "desktop": "Рабочий стол: двойной клик по иконкам, правый клик меню, Terminal - та же консоль",
    "exit": "Выход из GUI, возврат в консоль...",
    "not_available": "GUI недоступен в чистой консоли, но можно открыть emulator/index.html в браузере для гибрида",
    "browser_hint": "Браузерный гибрид: открой emulator/index.html"
  },
  "server": {
    "installer": "Установщик серверов: jpkg + srv",
    "list": "Доступные пакеты: nginx, apache, api-server, file-server, nodejs, wordpress, mysql и т.д. Используй jpkg list"
  },
  "prompt": {
    "console": "jino@jino-pc",
    "gui": "Jino GUI Терминал"
  }
}
