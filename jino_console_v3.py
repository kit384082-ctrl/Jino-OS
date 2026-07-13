#!/usr/bin/env python3
"""
Jino OS v2.2 CONSOLE SERVER EDITION - Easy Server Installer + Full Error Explanations + Real curl
No GUI, 100+ cmds, jpkg + srv + curl with detailed errors
Build: 2026-07-13 FULL-ERRORS+CURL
"""
import os, sys, time, json, shlex, base64, re, random, math
import shutil, datetime, socket, threading, urllib.request, urllib.parse, urllib.error
import http.client, ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION="2.2 Console Server + Errors + curl"
BUILD="2026-07-13 FULL-ERRORS"
C_RESET="\033[0m"; C_GREEN="\033[92m"; C_YELLOW="\033[93m"; C_CYAN="\033[96m"; C_RED="\033[91m"; C_MAGENTA="\033[95m"; C_BLUE="\033[94m"; C_BOLD="\033[1m"; C_DIM="\033[2m"
REPO_PATH="/home/user/JinoOS/packages/repo.json"
RUNTIME_ROOT="/tmp/jino_runtime"
SERVERS_DB="/tmp/jino_servers_db.json"

# ==================== ERROR SYSTEM ====================
ERRORS = {
    "JNO-001": {
        "title": "File not found / Файл не найден",
        "msg": "Указанный файл не существует в JinoFS",
        "cause": "Путь неверный, файл удален, опечатка в имени, не в том каталоге",
        "fix": "Проверь ls, find, pwd. Пример: ls /www, find / -name *.txt",
        "example": "cat /nope.txt -> JNO-001. Правильно: ls /, затем cat /readme.txt"
    },
    "JNO-002": {
        "title": "Directory not found / Папка не найдена",
        "msg": "Указанная директория не существует",
        "cause": "Неверный путь, папка не создана, cd в несуществующую папку",
        "fix": "Используй mkdir для создания, ls для проверки. cd /home/user",
        "example": "cd /nosuch -> JNO-002. Сделай: mkdir /nosuch, затем cd"
    },
    "JNO-003": {
        "title": "Is a directory / Это папка, а не файл",
        "msg": "Попытка прочитать папку как файл (cat, bat, etc)",
        "cause": "cat /www вместо cat /www/index.html",
        "fix": "Используй ls /www чтобы увидеть файлы внутри, затем cat /www/index.html",
        "example": "cat /www -> JNO-003. Правильно: ls /www, cat /www/index.html"
    },
    "JNO-004": {
        "title": "Not a directory / Не папка",
        "msg": "Попытка cd в файл, или mv папки в файл",
        "cause": "cd /readme.txt - readme.txt это файл",
        "fix": "Используй cat для файлов, cd только для папок. Проверь stat <path>",
        "example": "cd /readme.txt -> JNO-004. Правильно: cat /readme.txt"
    },
    "JNO-005": {
        "title": "Permission denied / Отказано в доступе",
        "msg": "Нет прав на операцию (симуляция)",
        "cause": "Попытка удалить / , изменить системный файл /etc/config.sys без прав",
        "fix": "Проверь chmod, не трогай /etc если не уверен. Для / - используй -r",
        "example": "rmdir / -> JNO-005. Нельзя удалять корень."
    },
    "JNO-006": {
        "title": "File exists / Файл уже существует",
        "msg": "Файл или папка уже существует",
        "cause": "mkdir существующей папки, cp в существующий файл без перезаписи, jpkg install существующего сервера",
        "fix": "Используй ls чтобы проверить, rm для удаления старого, или другое имя --name",
        "example": "mkdir /www -> JNO-006. /www уже есть. Используй mkdir /www/newsite"
    },
    "JNO-007": {
        "title": "Directory not empty / Папка не пуста",
        "msg": "Нельзя удалить непустую папку без -r",
        "cause": "rmdir /home/user когда там есть файлы",
        "fix": "Используй rm -r для рекурсивного удаления, или удали файлы внутри: ls /home/user, rm /home/user/*",
        "example": "rmdir /www -> JNO-007. Сделай rm -r /www или ls /www"
    },
    "JNO-008": {
        "title": "Command not found / Команда не найдена",
        "msg": "Неизвестная команда",
        "cause": "Опечатка, команда из другой ОС, GUI команда в консольной версии",
        "fix": "Напиши cmds для списка всех команд, help для справки, man <cmd>",
        "example": "sl -> JNO-008. Попробуй ls, cowsay, fortune"
    },
    "JNO-009": {
        "title": "Invalid arguments / Неверные аргументы",
        "msg": "Неправильное использование команды",
        "cause": "Не хватает аргументов, неверные флаги, неправильный порядок",
        "fix": "Используй man <cmd> или <cmd> без аргументов для подсказки",
        "example": "cp /readme.txt -> JNO-009. Нужно: cp src dst. Пример: cp /readme.txt /tmp/"
    },
    "JNO-010": {
        "title": "Port already in use / Порт занят",
        "msg": "Порт уже используется другим сервером",
        "cause": "Два сервера на одном порту, порт занят системой (80, 3000), сервер не остановлен",
        "fix": "srv list покажет занятые порты. Используй srv stop <name> или другой порт: --port 8081",
        "example": "srv start nginx (8080 занят) -> JNO-010. Сделай srv list, srv stop старый, или jpkg install nginx --port 8081"
    },
    "JNO-011": {
        "title": "Server not found / Сервер не найден",
        "msg": "Сервер с таким именем не установлен",
        "cause": "Опечатка в имени, сервер не устанавливался через jpkg, удален",
        "fix": "srv list покажет все установленные. jpkg list - все доступные. jpkg install <pkg>",
        "example": "srv start myblog -> JNO-011 если нет. Сделай srv list, затем jpkg install nginx --name myblog"
    },
    "JNO-012": {
        "title": "Package not found / Пакет не найден",
        "msg": "Пакет не найден в репозитории Jino",
        "cause": "Опечатка в имени пакета, пакет не существует, устаревший репо",
        "fix": "jpkg list покажет все 18 пакетов, jpkg search <term> для поиска, jpkg update",
        "example": "jpkg install ngnix -> JNO-012 (опечатка). Правильно: jpkg install nginx. Попробуй jpkg search nginx"
    },
    "JNO-013": {
        "title": "Server already running / Сервер уже запущен",
        "msg": "Попытка запустить уже запущенный сервер",
        "cause": "srv start дважды",
        "fix": "srv status <name> проверит, srv restart для перезапуска, srv stop затем start",
        "example": "srv start nginx когда уже running -> JNO-013. Сделай srv restart nginx"
    },
    "JNO-014": {
        "title": "Server not running / Сервер не запущен",
        "msg": "Попытка остановить не запущенный сервер",
        "cause": "srv stop на остановленном сервере",
        "fix": "srv status <name> покажет статус, srv list покажет running/stopped",
        "example": "srv stop nginx когда stopped -> JNO-014. Проверь srv status nginx"
    },
    "JNO-015": {
        "title": "Invalid port / Неверный порт",
        "msg": "Порт должен быть числом 1-65535, не привилегированный без root",
        "cause": "Буквы вместо числа, порт 0, порт >65535, порт <1024 без прав",
        "fix": "Используй порт 8000-9000 для тестов, 3000, 5000, 8080-8089. Пример: --port 8080",
        "example": "srv create my --port abc -> JNO-015. Правильно: --port 8080"
    },
    "JNO-016": {
        "title": "Invalid path / Неверный путь",
        "msg": "Путь содержит недопустимые символы или пуст",
        "cause": "Пустой путь, недопустимые символы, путь слишком длинный",
        "fix": "Используй абсолютные пути: /www, /home/user/docs. Избегай .. в середине",
        "example": "cd '' -> JNO-016. Правильно: cd /home/user"
    },
    "JNO-017": {
        "title": "Connection refused / Соединение отклонено",
        "msg": "curl не может подключиться к серверу - порт не слушает",
        "cause": "Сервер не запущен (srv start), неверный порт, firewall, сервер упал",
        "fix": "srv list покажет running. srv start <name>. Проверь порт: curl http://localhost:PORT/. Убедись что сервер на 127.0.0.1, не только JinoFS",
        "example": "curl http://localhost:8080/ когда сервер stopped -> JNO-017. Сделай srv start myserver"
    },
    "JNO-018": {
        "title": "Timeout / Истекло время ожидания",
        "msg": "Сервер не ответил за указанное время",
        "cause": "Медленный сервер, сеть, сервер завис, большой файл",
        "fix": "Попробуй снова, увеличь timeout: curl --connect-timeout 10 <url>. Проверь srv logs <name>, srv restart <name>",
        "example": "curl http://slow.site/ -> JNO-018. Попробуй curl --connect-timeout 10 http://slow.site/"
    },
    "JNO-019": {
        "title": "Invalid URL / Неверный URL",
        "msg": "URL имеет неверный формат",
        "cause": "Нет http://, опечатка, пробелы в URL, неподдерживаемый протокол",
        "fix": "Используй полный URL: http://localhost:8080/, https://example.com/api. Для файлов используй file:///www/index.html или просто cat /www/index.html",
        "example": "curl localhost:8080 -> JNO-019? Лучше curl http://localhost:8080/. Или curl file:///www/index.html для JinoFS"
    },
    "JNO-020": {
        "title": "HTTP error / HTTP ошибка",
        "msg": "Сервер вернул ошибку 4xx или 5xx",
        "cause": "404 - файл не найден на сервере, 403 - forbidden, 500 - ошибка сервера",
        "fix": "Проверь путь: /api/status существует, /nope нет. srv logs покажет логи. Для 500 - перезапусти сервер",
        "example": "curl http://localhost:8080/nope -> HTTP 404 JNO-020. Попробуй curl http://localhost:8080/api/status"
    },
    "JNO-021": {
        "title": "Write error / Ошибка записи",
        "msg": "Не удалось записать файл",
        "cause": "Диск полон (симуляция), неверный путь, нет прав",
        "fix": "Проверь df, путь. Попробуй другой путь: /tmp/",
        "example": "echo hi > / -> JNO-021. Нельзя писать в / напрямую. Пиши в /tmp/hi.txt"
    },
    "JNO-022": {
        "title": "JDB key not found / Ключ не найден в базе",
        "msg": "Ключ не существует в JinoDB",
        "cause": "jdb get несуществующего ключа",
        "fix": "jdb list покажет все ключи, jdb set <k> <v> для создания",
        "example": "jdb get nokey -> JNO-022. Сделай jdb list, затем jdb set nokey value"
    },
    "JNO-023": {
        "title": "Invalid method / Неверный HTTP метод",
        "msg": "curl -X с неподдерживаемым методом",
        "cause": "Методы: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS. Опечатка",
        "fix": "Используй: curl -X GET http://..., curl -X POST -d data ...",
        "example": "curl -X FOOBAR http://... -> JNO-023. Правильно: -X POST"
    }
}

def print_error(code, context="", extra=""):
    err = ERRORS.get(code)
    if not err:
        print(f"{C_RED}[{code}] Unknown error: {context}{C_RESET}")
        return
    print(f"{C_RED}{C_BOLD}┌─ ОШИБКА {code}: {err['title']}{C_RESET}")
    print(f"{C_RED}│ Сообщение: {err['msg']}{C_RESET}")
    if context:
        print(f"{C_RED}│ Контекст: {context}{C_RESET}")
    print(f"{C_YELLOW}│ Причина: {err['cause']}{C_RESET}")
    print(f"{C_GREEN}│ Решение: {err['fix']}{C_RESET}")
    print(f"{C_DIM}│ Пример: {err['example']}{C_RESET}")
    if extra:
        print(f"{C_CYAN}│ Доп: {extra}{C_RESET}")
    print(f"{C_RED}{C_BOLD}└─{C_RESET}")

def load_repo():
    try:
        with open(REPO_PATH,'r') as f: return json.load(f)
    except: return {"packages":[]}

class JinoFS:
    def __init__(self):
        self.files={}; self.dirs=set(["/"]); self.cwd="/"; self._init_defaults(); self.load_persist()
    def _init_defaults(self):
        now=time.time()
        def mkfile(p,c,perm="rw-r--r--"): self.files[self.norm(p)]={"content":c,"mtime":now,"perms":perm}; self.ensure_dir(os.path.dirname(self.norm(p)))
        def mkdir(p): self.ensure_dir(self.norm(p))
        mkdir("/bin"); mkdir("/etc"); mkdir("/etc/servers"); mkdir("/etc/jpkg"); mkdir("/home"); mkdir("/home/user"); mkdir("/www"); mkdir("/var"); mkdir("/tmp"); mkdir("/apps"); mkdir("/db"); mkdir("/usr"); mkdir("/system"); mkdir("/servers"); mkdir("/templates"); mkdir("/home/user/docs")
        mkfile("/readme.txt","Jino OS v2.2 Console Server Edition\nNo GUI, 100+ cmds, curl + full errors\n\nType 'help', 'cmds', 'jpkg list', 'srv list', 'curl --help'\n")
        mkfile("/autoexec.jino","echo Jino OS 2.2 Booted\nver\nsrv list\n")
        mkfile("/www/index.html","<html><head><title>JinoServer</title></head><body><h1>JinoServer v2.2 Works!</h1><p>Default :80</p><p><a href='/api/status'>/api/status</a> | <a href='/api/jdb'>/api/jdb</a></p></body></html>")
        mkfile("/etc/hosts","127.0.0.1 localhost\n127.0.0.1 jino.local\n")
        mkfile("/etc/config.sys","memory=32MB\nfs=JinoFS v2\nshell=JinoSH 2.2\nmode=console_server+errors\n")
        mkfile("/apps/hello.japp",'print("Hello Jino!")\n')
        mkfile("/home/user/notes.txt","Notes\n")
        mkfile("/system/motd.txt","Welcome to Jino OS v2.2! With full error explanations and curl.\n")
        mkfile("/home/user/test.json",'{"name":"Jino","version":"2.2","test":true}')
    def persist_file(self): return "/tmp/jino_fs_persist.json"
    def load_persist(self):
        try:
            pf=self.persist_file()
            if os.path.exists(pf):
                with open(pf,'r') as f:
                    data=json.load(f)
                    for k,v in data.get("files",{}).items():
                        if k not in self.files: self.files[k]=v
                    for d in data.get("dirs",[]): self.dirs.add(d)
        except: pass
    def save_persist(self):
        try:
            with open(self.persist_file(),'w') as f: json.dump({"files":self.files,"dirs":list(self.dirs)},f)
        except: pass
    def norm(self,p):
        if not p: return self.cwd
        p=str(p).strip()
        if not p.startswith("/"): p=os.path.join(self.cwd,p)
        p=os.path.normpath(p).replace("\\","/")
        if not p.startswith("/"): p="/"+p
        if len(p)>1 and p.endswith("/"): p=p[:-1]
        return p
    def ensure_dir(self,path):
        path=self.norm(path); parts=path.split("/"); cur=""
        for part in parts:
            if not part: cur="/"; self.dirs.add(cur); continue
            cur=cur.rstrip("/")+ "/"+part
            if cur=="": cur="/"
            self.dirs.add(cur)
    def is_dir(self,path): return self.norm(path) in self.dirs
    def is_file(self,path): return self.norm(path) in self.files
    def list_dir(self,path=None):
        if path is None: path=self.cwd
        path=self.norm(path)
        if path not in self.dirs:
            if not any(f.startswith(path+"/") for f in self.files) and path not in self.files: return None
        dirs=[]; files=[]
        for d in self.dirs:
            if d==path: continue
            if os.path.dirname(d)==path: dirs.append(os.path.basename(d))
        for fpath in self.files:
            if os.path.dirname(fpath)==path: files.append(os.path.basename(fpath))
        prefix=path if path=="/" else path+"/"
        for fpath in self.files:
            if fpath.startswith(prefix):
                rel=fpath[len(prefix):].split("/")[0]
                if "/" in fpath[len(prefix):] and rel not in dirs: dirs.append(rel)
        return sorted(dirs), sorted(files)
    def read(self,path):
        p=self.norm(path); return self.files[p]["content"] if p in self.files else None
    def stat(self,path):
        p=self.norm(path)
        if p in self.files: d=self.files[p]; return {"type":"file","size":len(d["content"]),"mtime":d["mtime"],"perms":d["perms"],"path":p}
        if p in self.dirs: return {"type":"dir","size":4096,"mtime":time.time(),"perms":"rwxr-xr-x","path":p}
        return None
    def write(self,path,content,perms=None):
        p=self.norm(path); self.ensure_dir(os.path.dirname(p)); now=time.time()
        old=self.files.get(p,{}).get("perms","rw-r--r--")
        self.files[p]={"content":content,"mtime":now,"perms":perms or old}; self.save_persist()
    def mkdir(self,path):
        p=self.norm(path)
        if p in self.files: return False,"File exists"
        if p in self.dirs: return False,"Exists"
        self.ensure_dir(p); self.save_persist(); return True,p
    def rmdir(self,path):
        p=self.norm(path)
        if p=="/": return False,"Cannot remove /"
        if p not in self.dirs: return False,"No such dir"
        prefix=p if p=="/" else p+"/"
        for f in self.files:
            if f.startswith(prefix) or os.path.dirname(f)==p: return False,"Dir not empty"
        for d in self.dirs:
            if d!=p and d.startswith(prefix): return False,"Dir not empty"
        self.dirs.remove(p); self.save_persist(); return True,"OK"
    def rm(self,path):
        p=self.norm(path)
        if p in self.files: del self.files[p]; self.save_persist(); return True
        return False
    def cp(self,src,dst):
        s=self.norm(src); d=self.norm(dst)
        if s not in self.files: return False,"src not found"
        if self.is_dir(d): d=d.rstrip("/")+ "/"+os.path.basename(s)
        self.write(d,self.files[s]["content"]); return True,d
    def mv(self,src,dst):
        s=self.norm(src); d=self.norm(dst)
        if s in self.files:
            if self.is_dir(d): d=d.rstrip("/")+ "/"+os.path.basename(s)
            self.write(d,self.files[s]["content"]); del self.files[s]; self.save_persist(); return True,d
        if s in self.dirs:
            if d in self.dirs: return False,"dst exists"
            new_dirs=set()
            for dirpath in self.dirs:
                if dirpath==s or dirpath.startswith(s+"/"): new_dirs.add(d+dirpath[len(s):])
                else: new_dirs.add(dirpath)
            new_files={}
            for fpath,fdata in self.files.items():
                if fpath==s or fpath.startswith(s+"/"): new_files[d+fpath[len(s):]]=fdata
                else: new_files[fpath]=fdata
            self.dirs=new_dirs; self.files=new_files; self.save_persist(); return True,d
        return False,"not found"

class ServerInstance:
    def __init__(self,config,fs_ref,jdb_ref):
        self.name=config.get("name"); self.type=config.get("type","static"); self.port=config.get("port",8080); self.root=config.get("root","/www"); self.config=config; self.fs=fs_ref; self.jdb=jdb_ref; self.status="stopped"; self.thread=None; self.httpd=None; self.logs=[]; self.start_time=None; self.real_root=os.path.join(RUNTIME_ROOT,self.name)
    def log(self,msg):
        ts=time.strftime("%H:%M:%S"); entry=f"[{ts}] {msg}"; self.logs.append(entry)
        if len(self.logs)>200: self.logs=self.logs[-200:]
        print(f"{C_DIM}[{self.name}] {entry}{C_RESET}")
    def ensure_real_fs(self):
        os.makedirs(self.real_root,exist_ok=True)
        root_norm=self.fs.norm(self.root)
        for fpath,fdata in self.fs.files.items():
            if fpath.startswith(root_norm):
                rel=fpath[len(root_norm):].lstrip("/")
                if not rel: rel="index.html"
                if fpath==root_norm and self.fs.stat(fpath)["type"]=="file": rel=os.path.basename(fpath)
                real_path=os.path.join(self.real_root,rel)
                os.makedirs(os.path.dirname(real_path),exist_ok=True)
                try:
                    with open(real_path,'w',encoding='utf-8',errors='ignore') as out:
                        content=fdata["content"].replace("{{SERVER_NAME}}",self.name).replace("{{PORT}}",str(self.port)).replace("{{ROOT}}",self.root).replace("{{ID}}",self.name).replace("{{SERVER_TYPE}}",self.type)
                        out.write(content)
                except: pass
        idx=os.path.join(self.real_root,"index.html")
        if not os.path.exists(idx):
            with open(idx,'w') as f: f.write(f"<html><body><h1>{self.name} - {self.type}</h1><p>Port {self.port} Root {self.root}</p><p><a href='/api/status'>/api/status</a></p></body></html>")
    def make_handler(self):
        fs_ref=self.fs; jdb_ref=self.jdb; server_name=self.name; server_config=self.config; real_root=self.real_root; logs_ref=self.logs
        class JinoHandler(BaseHTTPRequestHandler):
            def log_message(self,format,*args):
                msg=f"{self.client_address[0]} - {format%args}"; logs_ref.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
            def do_GET(self):
                if self.path.startswith("/api/"): self.handle_api(); return
                path=self.path.split("?")[0]
                if path=="/": path="/index.html"
                path=path.lstrip("/"); path=os.path.normpath(path).replace("..","")
                full=os.path.join(real_root,path)
                if os.path.isdir(full): full=os.path.join(full,"index.html")
                if os.path.exists(full) and os.path.isfile(full):
                    try:
                        with open(full,'rb') as f: data=f.read()
                        self.send_response(200)
                        if full.endswith(".html"): self.send_header("Content-Type","text/html")
                        elif full.endswith(".json"): self.send_header("Content-Type","application/json")
                        else: self.send_header("Content-Type","text/html")
                        self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(data)
                    except Exception as e: self.send_error(500,str(e))
                else:
                    vpath=server_config.get("root","/www").rstrip("/")+ "/"+path
                    vcontent=fs_ref.read(vpath)
                    if vcontent:
                        self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers(); self.wfile.write(vcontent.encode())
                    else:
                        self.send_response(404); self.send_header("Content-Type","text/html"); self.end_headers()
                        html=f"<h1>404 - {self.path}</h1><p>Server {server_name}</p><p><a href='/'>/</a> <a href='/api/status'>/api/status</a></p>"
                        self.wfile.write(html.encode())
            def handle_api(self):
                if self.path.startswith("/api/status"):
                    info={"server":server_name,"type":server_config.get("type"),"port":server_config.get("port"),"root":server_config.get("root"),"status":"running","uptime":time.time()-(server_config.get("start_time",time.time())),"jino_version":VERSION}
                    self.send_json(info)
                elif self.path.startswith("/api/jdb"): self.send_json(jdb_ref)
                elif self.path.startswith("/api/files"):
                    files=list(fs_ref.files.keys()); self.send_json({"files":files[:100],"count":len(files)})
                elif self.path.startswith("/api/echo"):
                    msg=self.path.split("msg=")[-1] if "msg=" in self.path else "hello"
                    self.send_json({"echo":msg,"server":server_name})
                else: self.send_json({"error":"unknown api","available":["/api/status","/api/jdb","/api/files","/api/echo"]})
            def do_POST(self):
                length=int(self.headers.get('Content-Length',0)); data=self.rfile.read(length).decode() if length else ""
                if self.path.startswith("/api/jdb"):
                    try:
                        obj=json.loads(data); jdb_ref.update(obj); self.send_json({"ok":True,"db":jdb_ref})
                    except: self.send_json({"ok":True,"received":data})
                else: self.send_json({"ok":True,"received":data})
            def do_PUT(self): self.do_POST()
            def do_DELETE(self):
                self.send_json({"ok":True,"deleted":self.path})
            def send_json(self,obj):
                self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(json.dumps(obj,indent=2).encode())
        return JinoHandler
    def is_port_free(self,port):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s: return s.connect_ex(('127.0.0.1',port))!=0
    def start(self):
        if self.status=="running": return False,"Already running"
        if not self.is_port_free(self.port): return False,f"Port {self.port} in use"
        self.ensure_real_fs(); handler=self.make_handler()
        try:
            self.httpd=ThreadingHTTPServer(("127.0.0.1",self.port),handler)
            self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True); self.thread.start()
            self.status="running"; self.start_time=time.time(); self.config["start_time"]=self.start_time
            self.log(f"Started on :{self.port} root {self.root}"); return True,f"Started {self.name} on http://localhost:{self.port}"
        except Exception as e: return False,str(e)
    def stop(self):
        if self.status!="running": return False,"Not running"
        try:
            if self.httpd: self.httpd.shutdown(); self.httpd.server_close()
            self.status="stopped"; self.log(f"Stopped"); return True,f"Stopped {self.name}"
        except Exception as e: return False,str(e)
    def restart(self): self.stop(); time.sleep(0.5); return self.start()
    def get_status(self):
        uptime=int(time.time()-self.start_time) if self.start_time else 0
        return {"name":self.name,"type":self.type,"port":self.port,"root":self.root,"status":self.status,"uptime":uptime,"real_root":self.real_root,"logs":self.logs[-20:]}

class ServerManager:
    def __init__(self,fs_ref,jdb_ref):
        self.fs=fs_ref; self.jdb=jdb_ref; self.servers={}; self.load()
    def load(self):
        try:
            if os.path.exists(SERVERS_DB):
                with open(SERVERS_DB,'r') as f:
                    data=json.load(f)
                    for cfg in data.get("servers",[]): self.servers[cfg["name"]]=ServerInstance(cfg,self.fs,self.jdb)
            for fpath,fdata in self.fs.files.items():
                if fpath.startswith("/etc/servers/") and fpath.endswith(".json"):
                    try:
                        cfg=json.loads(fdata["content"])
                        if cfg["name"] not in self.servers: self.servers[cfg["name"]]=ServerInstance(cfg,self.fs,self.jdb)
                    except: pass
            if "default" not in self.servers:
                cfg={"name":"default","type":"static","port":80,"root":"/www"}; self.servers["default"]=ServerInstance(cfg,self.fs,self.jdb); self.save()
        except Exception as e: print(f"Load servers error {e}")
    def save(self):
        try:
            data={"servers":[s.config for s in self.servers.values()]}
            with open(SERVERS_DB,'w') as f: json.dump(data,f,indent=2)
            for srv in self.servers.values(): self.fs.write(f"/etc/servers/{srv.name}.json",json.dumps(srv.config,indent=2))
        except Exception as e: print(f"Save error {e}")
    def list_servers(self): return list(self.servers.values())
    def get(self,name): return self.servers.get(name)
    def create(self,name,template="static",port=8080,root="/www",extra=None):
        if name in self.servers: return False,f"Server {name} exists"
        self.fs.ensure_dir(root)
        if template=="static":
            html=f"<html><body><h1>{name} - {template}</h1><p>Port {port} Root {root}</p></body></html>"
            if not self.fs.is_file(f"{root}/index.html"): self.fs.write(f"{root}/index.html",html)
        cfg={"name":name,"type":template,"port":int(port),"root":root,"created":time.time()}
        if extra: cfg.update(extra)
        self.servers[name]=ServerInstance(cfg,self.fs,self.jdb); self.save(); return True,cfg
    def delete(self,name):
        srv=self.servers.get(name)
        if not srv: return False,"Not found"
        if srv.status=="running": srv.stop()
        del self.servers[name]; self.save()
        if self.fs.is_file(f"/etc/servers/{name}.json"): self.fs.rm(f"/etc/servers/{name}.json")
        return True,f"Deleted {name}"
    def start(self,name):
        srv=self.get(name)
        if not srv: return False,"Not found"
        return srv.start()
    def stop(self,name):
        srv=self.get(name)
        if not srv: return False,"Not found"
        return srv.stop()
    def restart(self,name):
        srv=self.get(name)
        if not srv: return False,"Not found"
        return srv.restart()
    def start_all(self):
        res=[]
        for name in self.servers:
            ok,msg=self.start(name); res.append((name,ok,msg))
        return res
    def stop_all(self):
        res=[]
        for name in self.servers:
            ok,msg=self.stop(name); res.append((name,ok,msg))
        return res

class PackageManager:
    def __init__(self,fs_ref,srv_manager,jdb_ref):
        self.fs=fs_ref; self.srv=srv_manager; self.jdb=jdb_ref; self.repo=load_repo()
    def list_packages(self,filter_type=None):
        pkgs=self.repo.get("packages",[])
        if filter_type: pkgs=[p for p in pkgs if p.get("type")==filter_type or p.get("category")==filter_type]
        return pkgs
    def search(self,term):
        term=term.lower(); res=[]
        for p in self.repo.get("packages",[]):
            if term in p["name"].lower() or term in p.get("description","").lower() or term in p.get("category",""): res.append(p)
        return res
    def get_pkg(self,name):
        for p in self.repo.get("packages",[]):
            if p["name"]==name: return p
        return None
    def install(self,name,port=None,custom_name=None,root=None):
        pkg=self.get_pkg(name)
        if not pkg: return False,f"Package {name} not found. Try jpkg list"
        srv_name=custom_name or pkg["name"]
        srv_port=port or pkg.get("port",8080)
        srv_root=root or pkg.get("root",f"/www/{srv_name}")
        srv_type=pkg.get("type","static")
        if srv_type=="template": srv_type=name
        for dep in pkg.get("dependencies",[]):
            if dep not in [s.name for s in self.srv.list_servers()]:
                print(f"{C_YELLOW}Installing dep {dep}...{C_RESET}")
                self.install(dep)
        self.fs.ensure_dir(srv_root)
        if name in ("nginx","apache","jino-web","static","file-server"):
            html=f"<html><head><title>{srv_name}</title><style>body{{background:#0a0a0a;color:#0f0;font-family:monospace;padding:20px}} h1{{color:#ff0}} .box{{border:1px solid #0f0;padding:12px;margin:12px 0}}</style></head><body><h1>🌀 {srv_name} ({name} v{pkg.get('version')})</h1><div class='box'>Port {srv_port} Root {srv_root}</div><div class='box'><a href='/api/status' style='color:#0ff'>/api/status</a> | <a href='/api/jdb' style='color:#0ff'>/api/jdb</a></div></body></html>"
            self.fs.write(f"{srv_root}/index.html",html)
        elif name in ("api-server","python-api","nodejs","express","flask"):
            self.fs.write(f"{srv_root}/index.html",f"<h1>{srv_name} API</h1><p>Port {srv_port}</p>")
        elif name in ("wordpress","php-server"):
            self.fs.write(f"{srv_root}/index.html",f"<h1>{srv_name} - WordPress sim</h1><p>Port {srv_port}</p>")
        elif name in ("mysql","postgres","redis"):
            self.fs.write(f"{srv_root}/README.txt",f"{name} DB sim Port {srv_port}")
        elif name=="chat-server":
            self.fs.write(f"{srv_root}/index.html","<h1>Chat Server</h1><div id=chat></div><input id=msg><button onclick=\"send()\">Send</button>")
        ok,res=self.srv.create(srv_name,template=srv_type if srv_type!="server" else "static",port=srv_port,root=srv_root,extra={"pkg":name,"version":pkg.get("version")})
        if not ok: return False,res
        return True,f"Installed {name} as '{srv_name}' on :{srv_port} root {srv_root}. Run 'srv start {srv_name}'"

class JinoOS:
    def __init__(self):
        self.fs=JinoFS()
        self.jdb={"visits":"1","user":"jino","hostname":"jino-pc","boot_time":str(int(time.time()))}
        self.history=[]; self.aliases={"ll":"ls -l","la":"ls -a","dir":"ls","..":"cd ..","h":"history","?":"help","cls":"clear"}
        self.env={"USER":"jino","HOME":"/home/user","PATH":"/bin","SHELL":"/bin/jinosh","OS":"Jino OS 2.2","TERM":"jino-256color","PWD":self.fs.cwd,"HOST":"jino-pc","EDITOR":"nano"}
        self.srv_manager=ServerManager(self.fs,self.jdb)
        self.pkg_manager=PackageManager(self.fs,self.srv_manager,self.jdb)
        self.uptime_start=time.time(); self.last_exit_code=0
    def boot(self):
        print(C_GREEN+C_BOLD+r"""
     ██╗██╗███╗   ██╗ ██████╗      ██████╗ ███████╗
     ██║██║████╗  ██║██═══██╗    ██╔═══██╗██╔════╝
     ██║██║██╔██╗ ██║██║   ██║    ██║   ██║███████╗
██   ██║██║██║╚██╗██║██║   ██║    ██║   ██║╚════██║
╚█████╔╝██║██║ ╚████║╚██████╔╝    ╚██████╔╝███████║
 ╚════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝      ╚═════╝ ╚══════╝

          CONSOLE SERVER EDITION v2.2 - ERRORS + CURL + EASY INSTALL
"""+C_RESET)
        print(f"{C_CYAN}Jino OS {VERSION} | {BUILD} | 32MB | i386{C_RESET}")
        print(f"{C_GREEN}[OK] JinoFS v2 {len(self.fs.files)} files{C_RESET}")
        print(f"{C_GREEN}[OK] Server Manager {len(self.srv_manager.servers)} servers{C_RESET}")
        print(f"{C_GREEN}[OK] Repo {len(self.pkg_manager.repo.get('packages',[]))} packages{C_RESET}")
        print(f"{C_GREEN}[OK] Error system 23 codes loaded{C_RESET}")
        print(f"{C_GREEN}[OK] curl 2.2 full implementation{C_RESET}")
        print(f"Type {C_BOLD}help{C_RESET}, {C_BOLD}errors{C_RESET}, {C_BOLD}curl --help{C_RESET}, {C_BOLD}jpkg list{C_RESET}")
        print()

    def parse(self,line):
        stripped=line.strip()
        if not stripped: return [],None,False
        first=stripped.split()[0]
        if first in self.aliases: line=self.aliases[first]+" "+" ".join(stripped.split()[1:])
        redirect_out=None; redirect_append=False
        if ">" in line and "curl" not in line.split()[0]: # don't parse > for curl with data?
            # careful: curl data may contain >, but we handle simple
            # Only parse redirection if not inside quotes for last part
            m=re.search(r'\s*(>>|>)\s*([^\s]+)\s*$', line)
            if m:
                op=m.group(1); target=m.group(2)
                # avoid capturing if target looks like URL part? simple check
                if not target.startswith("http"):
                    redirect_out=target; redirect_append=(op==">>"); line=line[:m.start()].strip()
        try: parts=shlex.split(line)
        except: parts=line.split()
        return parts,redirect_out,redirect_append

    # HELP / ERRORS
    def cmd_help(self,args):
        print(f"{C_BOLD}{C_GREEN}Jino OS v2.2 - Help{C_RESET}")
        print(f"{C_YELLOW}100+ команд + серверы + curl + полные ошибки{C_RESET}")
        print("")
        print("Сервера:")
        print("  jpkg list | jpkg install <pkg> [--port P] [--name N]")
        print("  srv list | srv start <name> | srv new | srv quick <pkg>")
        print("  deploy <path> --port 8000")
        print("")
        print("Сеть:")
        print("  curl <url> [-o file] [-X POST] [-d data] [-H header] [-i] [-v] [-L]")
        print("  curl --help для полной справки")
        print("  wget <url> [-O file] (alias curl)")
        print("  ping, ifconfig")
        print("")
        print("Файлы: ls ll pwd cd cat bat mkdir rmdir rm cp mv find tree du df")
        print("Текст: echo write edit head tail wc grep hexdump base64")
        print("Система: ver sysinfo date clear history mem ps errors")
        print("Фан: calc cowsay banner matrix")
        print("")
        print("Ошибки: команда errors покажет все коды и объяснения")

    def cmd_errors(self,args):
        if args and args[0] in ERRORS:
            code=args[0].upper()
            if not code.startswith("JNO-"): code="JNO-"+code
            err=ERRORS.get(code)
            if err:
                print(f"{C_BOLD}{code}: {err['title']}{C_RESET}")
                print(f"Сообщение: {err['msg']}")
                print(f"Причина: {err['cause']}")
                print(f"Решение: {err['fix']}")
                print(f"Пример: {err['example']}")
            return
        print(f"{C_BOLD}Полный список ошибок Jino OS (23 кода):{C_RESET}")
        for code,err in ERRORS.items():
            print(f"{C_RED}{code}{C_RESET}: {err['title']}")
            print(f"  {C_DIM}{err['msg']}{C_RESET}")
        print(f"\n{C_YELLOW}Для подробностей: errors JNO-001  или errors 001{C_RESET}")
        print(f"{C_CYAN}Пример: cat /nope.txt вызовет JNO-001 с полным объяснением{C_RESET}")

    # JPKG / SRV (with enhanced errors)
    def cmd_jpkg(self,args):
        if not args:
            print_error("JNO-009","jpkg без аргументов","Используй: jpkg list, jpkg install <pkg>")
            return
        sub=args[0]
        if sub=="list":
            filt=args[1] if len(args)>1 else None
            pkgs=self.pkg_manager.list_packages(filt)
            print(f"{C_BOLD}Repo - {len(pkgs)} pkgs{C_RESET}")
            print(f"{'NAME':<20} {'VER':<10} {'PORT':<6} {'TYPE':<10} DESC")
            print("-"*90)
            for p in pkgs: print(f"{C_GREEN}{p['name']:<20}{C_RESET} {p.get('version',''):<10} {str(p.get('port','-')):<6} {p.get('type',''):<10} {p.get('description','')[:50]}")
        elif sub=="search":
            term=args[1] if len(args)>1 else ""
            if not term:
                print_error("JNO-009","jpkg search без термина","Пример: jpkg search nginx")
                return
            res=self.pkg_manager.search(term)
            if not res:
                print_error("JNO-012",f"search '{term}' ничего не нашел",f"Попробуй: jpkg list, jpkg search {term[:3]}")
            else:
                print(f"Search '{term}' {len(res)} found:")
                for p in res: print(f" {p['name']:<20} {p.get('description','')}")
        elif sub=="install":
            if len(args)<2:
                print_error("JNO-009","jpkg install без имени пакета","Пример: jpkg install nginx --port 8080 --name myweb")
                return
            pkg_name=args[1]; port=None; custom_name=None; root=None; i=2
            while i < len(args):
                if args[i]=="--port" and i+1<len(args):
                    try: port=int(args[i+1])
                    except:
                        print_error("JNO-015",f"Неверный порт {args[i+1]}","Порт должен быть числом 1-65535, пример: --port 8080")
                        return
                    i+=2; continue
                if args[i]=="--name" and i+1<len(args): custom_name=args[i+1]; i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            print(f"{C_YELLOW}Installing {pkg_name}...{C_RESET}")
            ok,msg=self.pkg_manager.install(pkg_name,port=port,custom_name=custom_name,root=root)
            if not ok:
                if "not found" in msg.lower():
                    print_error("JNO-012",msg,f"Доступные: jpkg list. Попробуй jpkg search {pkg_name[:3]}")
                elif "exists" in msg.lower():
                    print_error("JNO-006",msg,f"Сервер уже есть. Используй другое имя: --name {pkg_name}2 или srv delete {custom_name or pkg_name}")
                else:
                    print(f"{C_RED}{msg}{C_RESET}")
            else:
                print(f"{C_GREEN}{msg}{C_RESET}")
        elif sub in ("uninstall","remove"):
            if len(args)<2:
                print_error("JNO-009","jpkg uninstall без имени","Пример: jpkg uninstall myweb или srv delete myweb")
                return
            ok,msg=self.srv_manager.delete(args[1])
            if not ok:
                print_error("JNO-011",msg,f"Проверь srv list")
            else:
                print(msg)
        elif sub=="info":
            if len(args)<2:
                print_error("JNO-009","jpkg info без имени","Пример: jpkg info nginx")
                return
            pkg=self.pkg_manager.get_pkg(args[1])
            if not pkg:
                print_error("JNO-012",f"Пакет {args[1]} не найден","jpkg list покажет все")
            else:
                print(json.dumps(pkg,indent=2))
        else:
            print_error("JNO-008",f"jpkg {sub} неизвестная подкоманда","Доступные: list, search, install, uninstall, info")

    def cmd_srv(self,args):
        if not args:
            print_error("JNO-009","srv без аргументов","Использование: srv list, srv start <name>, srv new, srv quick <pkg>")
            return
        sub=args[0]
        if sub in ("list","ls","l"):
            servers=self.srv_manager.list_servers()
            if not servers: print("(no servers) jpkg list"); return
            print(f"{C_BOLD}{'NAME':<15} {'TYPE':<12} {'PORT':<6} {'STATUS':<10} {'ROOT':<20} URL{C_RESET}")
            print("-"*90)
            for s in servers:
                st=s.get_status(); col=C_GREEN if st["status"]=="running" else C_RED
                print(f"{st['name']:<15} {st['type']:<12} {str(st['port']):<6} {col}{st['status']:<10}{C_RESET} {st['root']:<20} http://localhost:{st['port']}")
        elif sub=="create":
            if len(args)<2:
                print_error("JNO-009","srv create без имени","Пример: srv create myblog --template static --port 8080 --root /www/myblog")
                return
            name=args[1]; template="static"; port=8080; root=f"/www/{name}"; i=2
            while i < len(args):
                if args[i]=="--template" and i+1<len(args): template=args[i+1]; i+=2; continue
                if args[i]=="--port" and i+1<len(args):
                    try: port=int(args[i+1])
                    except:
                        print_error("JNO-015",f"Порт {args[i+1]} не число","Пример: --port 8080")
                        return
                    i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            if not 1 <= port <= 65535:
                print_error("JNO-015",f"Порт {port} вне диапазона 1-65535","Используй 8000-9000 для тестов")
                return
            ok,res=self.srv_manager.create(name,template=template,port=port,root=root)
            if not ok:
                print_error("JNO-006",res,f"Сервер уже есть. Используй другое имя или srv delete {name}")
            else:
                print(f"{C_GREEN}Server {name} created template={template} port={port} root={root}{C_RESET}")
        elif sub=="start":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.start_all(): print(f"{name}: {msg}")
                    return
                print_error("JNO-009","srv start без имени","Пример: srv start myblog или srv start --all")
                return
            ok,msg=self.srv_manager.start(args[1])
            if not ok:
                if "in use" in msg.lower():
                    print_error("JNO-010",msg,f"srv list покажет занятые порты. Попробуй: srv stop <другой> или srv create с другим портом")
                elif "Not found" in msg:
                    print_error("JNO-011",msg,f"srv list - все установленные, jpkg list - доступные для установки")
                elif "Already running" in msg:
                    print_error("JNO-013",msg,f"srv status {args[1]} покажет, srv restart {args[1]} для перезапуска")
                else:
                    print(f"{C_RED}{msg}{C_RESET}")
            else:
                print(f"{C_GREEN}{msg}{C_RESET}")
        elif sub=="stop":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.stop_all(): print(f"{name}: {msg}")
                    return
                print_error("JNO-009","srv stop без имени","Пример: srv stop myblog или srv stop --all")
                return
            ok,msg=self.srv_manager.stop(args[1])
            if not ok:
                if "Not running" in msg:
                    print_error("JNO-014",msg,f"Сервер уже остановлен. srv status {args[1]} покажет статус")
                elif "Not found" in msg:
                    print_error("JNO-011",msg,f"srv list покажет все")
                else:
                    print(msg)
            else:
                print(f"{C_GREEN}{msg}{C_RESET}")
        elif sub=="restart":
            if len(args)<2:
                print_error("JNO-009","srv restart без имени","Пример: srv restart myblog")
                return
            ok,msg=self.srv_manager.restart(args[1])
            if not ok:
                print_error("JNO-011" if "Not found" in msg else "JNO-010",msg,"")
            else:
                print(f"{C_GREEN}{msg}{C_RESET}")
        elif sub=="status":
            name=args[1] if len(args)>1 else None
            if name:
                srv=self.srv_manager.get(name)
                if not srv:
                    print_error("JNO-011",f"Сервер {name} не найден","srv list покажет все")
                else:
                    print(json.dumps(srv.get_status(),indent=2))
            else: self.cmd_srv(["list"])
        elif sub=="logs":
            if len(args)<2:
                print_error("JNO-009","srv logs без имени","Пример: srv logs myblog")
                return
            srv=self.srv_manager.get(args[1])
            if not srv:
                print_error("JNO-011",f"Сервер {args[1]} не найден","srv list")
            else:
                print(f"Logs {srv.name}:")
                for l in srv.logs[-50:]: print(l)
                if not srv.logs:
                    print("(no logs yet, start server and curl it)")
        elif sub in ("delete","remove","rm","del"):
            if len(args)<2:
                print_error("JNO-009","srv delete без имени","Пример: srv delete myblog")
                return
            ok,msg=self.srv_manager.delete(args[1])
            if not ok:
                print_error("JNO-011",msg,"srv list")
            else:
                print(f"{C_GREEN}{msg}{C_RESET}")
        elif sub=="new":
            print(f"{C_BOLD}=== Server Wizard ==={C_RESET}")
            name=input("Name (myblog): ").strip()
            if not name:
                print_error("JNO-016","Пустое имя сервера","Введи имя: myblog, mysite, api")
                return
            print("Templates: static, api-server, file-server, python-api, nodejs, wordpress, chat-server, mysql, redis")
            template=input("Template [static]: ").strip() or "static"
            port_str=input("Port [8080]: ").strip() or "8080"
            try: port=int(port_str)
            except:
                print_error("JNO-015",f"Порт '{port_str}' не число","Введи число: 8080")
                return
            if not 1 <= port <= 65535:
                print_error("JNO-015",f"Порт {port} вне диапазона","1-65535, используй 8080")
                return
            root_default=f"/www/{name}" if template in ("static","file-server","wordpress") else f"/apps/{name}"
            root=input(f"Root [{root_default}]: ").strip() or root_default
            ok,res=self.srv_manager.create(name,template=template,port=port,root=root)
            if not ok:
                print_error("JNO-006",res,f"Используй другое имя")
                return
            print(f"{C_GREEN}Created {name}{C_RESET}")
            if input("Start now? Y/n: ").lower()!="n":
                ok2,msg2=self.srv_manager.start(name)
                if not ok2:
                    if "in use" in msg2:
                        print_error("JNO-010",msg2,f"Порт {port} занят, попробуй другой")
                    else:
                        print(msg2)
                else:
                    print(f"{C_GREEN}{msg2}{C_RESET}")
        elif sub=="quick":
            if len(args)<2:
                print_error("JNO-009","srv quick без пакета","Пример: srv quick nginx --port 8080")
                return
            pkg=args[1]; port=None
            if "--port" in args:
                idx=args.index("--port")
                if idx+1 < len(args):
                    try: port=int(args[idx+1])
                    except:
                        print_error("JNO-015",f"Порт {args[idx+1]} не число","")
                        return
            print(f"Quick install {pkg}...")
            ok,msg=self.pkg_manager.install(pkg,port=port)
            if not ok:
                if "not found" in msg.lower():
                    print_error("JNO-012",msg,"jpkg list для списка")
                else:
                    print(f"{C_RED}{msg}{C_RESET}")
                return
            print(f"{C_GREEN}{msg}{C_RESET}")
            srv_name=pkg
            ok2,msg2=self.srv_manager.start(srv_name)
            if not ok2:
                print_error("JNO-010" if "in use" in msg2 else "JNO-011",msg2,"")
            else:
                print(f"{C_GREEN}{msg2}{C_RESET}")
        elif sub=="info":
            if len(args)<2:
                print_error("JNO-009","srv info без имени","Пример: srv info myblog")
                return
            srv=self.srv_manager.get(args[1])
            if not srv:
                print_error("JNO-011",f"Сервер {args[1]} не найден","srv list")
            else:
                print(json.dumps(srv.config,indent=2))
        else:
            print_error("JNO-008",f"srv {sub} неизвестно","Доступные: list, create, start, stop, restart, status, logs, delete, new, quick, info")

    def cmd_deploy(self,args):
        path="."; port=8000; name=None; i=0
        while i < len(args):
            if args[i]=="--port" and i+1<len(args):
                try: port=int(args[i+1])
                except:
                    print_error("JNO-015",f"Порт {args[i+1]} не число","")
                    return
                i+=2; continue
            if args[i]=="--name" and i+1<len(args): name=args[i+1]; i+=2; continue
            if not args[i].startswith("--"): path=args[i]
            i+=1
        abs_path=self.fs.norm(path)
        if not name:
            name=os.path.basename(abs_path) or f"deploy{port}"
            if name=="/": name=f"site{port}"
        root=abs_path
        if self.fs.is_file(root): root=os.path.dirname(root)
        # check if path exists
        if not self.fs.is_dir(root) and not self.fs.is_file(abs_path) and not any(f.startswith(root+"/") for f in self.fs.files):
            print_error("JNO-002",f"Путь {path} -> {root} не найден","Проверь ls, pwd. Пример: deploy /www --port 8000")
            return
        print(f"Deploying {abs_path} as '{name}' :{port}...")
        ok,res=self.srv_manager.create(name,template="static",port=port,root=root)
        if not ok:
            print_error("JNO-006",res,f"Используй другое имя: --name {name}2 или srv delete {name}")
            return
        ok2,msg2=self.srv_manager.start(name)
        if not ok2:
            print_error("JNO-010" if "in use" in msg2 else "JNO-011",msg2,"")
        else:
            print(f"{C_GREEN}{msg2}{C_RESET}")

    # ==================== CURL FULL IMPLEMENTATION ====================
    def cmd_curl(self,args):
        # Help
        if not args or "--help" in args or "-h" in args:
            print(f"""{C_BOLD}{C_GREEN}curl - Jino OS Full Implementation v2.2{C_RESET}
Использование: curl [options] <url>

URL форматы:
  http://localhost:8080/          - локальный Jino сервер
  http://localhost:8080/api/status - API endpoint
  https://example.com/api         - внешний сайт (реальный интернет)
  file:///www/index.html          - файл из JinoFS
  /www/index.html                 - файл из JinoFS (сокращенно)

Опции:
  -X, --request METHOD            - HTTP метод: GET, POST, PUT, DELETE, PATCH, HEAD (default GET)
  -H, --header "Key: Value"       - добавить заголовок (можно несколько)
  -d, --data DATA                 - данные для POST/PUT (строка или @file)
      --data-urlencode DATA       - URL encode данные
  -o, --output FILE               - сохранить ответ в файл (JinoFS)
  -O, --remote-name               - сохранить с именем из URL
  -i, --include                   - показать заголовки ответа
  -v, --verbose                   - подробный вывод (запрос+ответ)
  -s, --silent                    - тихий режим (без прогресса)
  -L, --location                  - следовать редиректам
  --connect-timeout SEC           - таймаут подключения (default 5)
  -u, --user USER:PASS            - Basic Auth
  --help, -h                      - эта справка

Примеры:
  curl http://localhost:8080/
  curl http://localhost:3000/api/status
  curl http://localhost:8080/api/jdb -i
  curl -X POST http://localhost:3000/api/jdb -d '{{"new":"val"}}' -H "Content-Type: application/json"
  curl https://api.github.com/users/github
  curl file:///www/index.html
  curl /www/index.html
  curl http://localhost:8080/ -o /tmp/page.html
  curl http://localhost:8080/ -v
  curl http://localhost:8080/ -L
  curl https://example.com --connect-timeout 10

Ошибки:
  JNO-017 Connection refused - сервер не запущен, проверь srv list и srv start
  JNO-018 Timeout - сервер не ответил, попробуй --connect-timeout
  JNO-019 Invalid URL - неверный формат URL
  JNO-020 HTTP error - сервер вернул 4xx/5xx, проверь путь, srv logs
""")
            return

        # Parse args manually
        url=None
        method="GET"
        headers={}
        data=None
        output_file=None
        remote_name=False
        include_headers=False
        verbose=False
        silent=False
        follow_redirects=False
        timeout=5
        auth=None

        i=0
        while i < len(args):
            a=args[i]
            if a in ("-X","--request") and i+1 < len(args):
                method=args[i+1].upper()
                if method not in ("GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS"):
                    print_error("JNO-023",f"Неверный метод {method}","Допустимые: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS")
                    return
                i+=2; continue
            elif a in ("-H","--header") and i+1 < len(args):
                hv=args[i+1]
                if ":" in hv:
                    k,v=hv.split(":",1)
                    headers[k.strip()]=v.strip()
                else:
                    print_error("JNO-009",f"Неверный заголовок {hv}","Формат: -H \"Content-Type: application/json\"")
                    return
                i+=2; continue
            elif a in ("-d","--data","--data-raw","--data-urlencode"):
                if i+1 < len(args):
                    data=args[i+1]
                    if data.startswith("@"):
                        # file from JinoFS
                        fpath=data[1:]
                        fcontent=self.fs.read(fpath)
                        if fcontent is None:
                            print_error("JNO-001",f"Файл данных {fpath} не найден для -d @{fpath}","Проверь путь")
                            return
                        data=fcontent
                    if method=="GET":
                        method="POST"
                else:
                    print_error("JNO-009","-d без данных","Пример: -d '{\"key\":\"val\"}' или -d @/home/user/data.json")
                    return
                i+=2; continue
            elif a in ("-o","--output") and i+1 < len(args):
                output_file=args[i+1]
                i+=2; continue
            elif a in ("-O","--remote-name"):
                remote_name=True
                i+=1; continue
            elif a in ("-i","--include"):
                include_headers=True
                i+=1; continue
            elif a in ("-v","--verbose"):
                verbose=True
                i+=1; continue
            elif a in ("-s","--silent"):
                silent=True
                i+=1; continue
            elif a in ("-L","--location"):
                follow_redirects=True
                i+=1; continue
            elif a=="--connect-timeout" and i+1 < len(args):
                try: timeout=int(args[i+1])
                except:
                    print_error("JNO-015",f"Таймаут {args[i+1]} не число","Пример: --connect-timeout 10")
                    return
                i+=2; continue
            elif a in ("-u","--user") and i+1 < len(args):
                auth=args[i+1]
                i+=2; continue
            elif a.startswith("http://") or a.startswith("https://") or a.startswith("file://") or (a.startswith("/") and "." in a) or ("localhost" in a):
                if not url:
                    url=a
                else:
                    # maybe extra url? treat as data? but take last
                    url=a
                i+=1; continue
            elif not a.startswith("-") and not url:
                # could be URL without http? like localhost:8080/ or /www/index.html or example.com
                url=a
                i+=1; continue
            else:
                # unknown flag
                if a.startswith("-"):
                    print_error("JNO-008",f"Неизвестный флаг curl {a}","Попробуй curl --help для списка")
                    return
                i+=1

        if not url:
            print_error("JNO-019","URL не указан","Пример: curl http://localhost:8080/ или curl /www/index.html")
            return

        # Normalize URL - if starts with / and is JinoFS file, treat as file://
        if url.startswith("/"):
            # check if it's JinoFS file
            if self.fs.is_file(url) or self.fs.is_dir(url):
                url="file://"+url
            else:
                # maybe path like /api/status without host? Try localhost default?
                # If current servers running, try default server?
                # For simplicity, treat as http://localhost:80 + url if url starts with /
                if url.startswith("/api/") or url.startswith("/www/"):
                    url="http://localhost:80"+url
                else:
                    # check if file exists later
                    url="file://"+url

        # file:// handling
        if url.startswith("file://"):
            fpath=url[7:]
            if not fpath: fpath="/"
            content=self.fs.read(fpath)
            if content is None:
                # try list dir
                listing=self.fs.list_dir(fpath)
                if listing:
                    dirs,files=listing
                    content=f"Directory listing {fpath}:\n"
                    for d in dirs: content+=f"[DIR] {d}/\n"
                    for f in files: content+=f"[FILE] {f}\n"
                else:
                    print_error("JNO-001",f"Файл {fpath} не найден в JinoFS","Проверь ls {os.path.dirname(fpath)}")
                    return
            if verbose:
                print(f"> GET {url}")
                print(f"> Host: JinoFS")
                print(f">")
                print(f"< HTTP/1.1 200 OK")
                print(f"< Content-Type: text/html")
                print(f"< Content-Length: {len(content)}")
            if include_headers:
                print(f"HTTP/1.1 200 OK\nContent-Type: text/html\nContent-Length: {len(content)}\n")
            if output_file:
                self.fs.write(output_file, content)
                if not silent:
                    print(f"Saved to {output_file} ({len(content)} bytes)")
            else:
                if not silent or include_headers or verbose:
                    print(content)
            return

        # HTTP/HTTPS handling
        # Ensure URL has scheme
        if not url.startswith("http://") and not url.startswith("https://"):
            # try to add http:// if looks like localhost:port or domain
            if ":" in url or "." in url or "localhost" in url:
                url="http://"+url
            else:
                print_error("JNO-019",f"URL {url} без схемы http:// или https://","Пример: http://localhost:8080/ или https://example.com")
                return

        # Parse URL
        try:
            parsed=urllib.parse.urlparse(url)
            if not parsed.hostname:
                print_error("JNO-019",f"Неверный URL {url} - нет хоста","Пример: http://localhost:8080/ или https://api.github.com")
                return
            host=parsed.hostname
            port=parsed.port or (443 if parsed.scheme=="https" else 80)
            path=parsed.path or "/"
            if parsed.query: path+="?"+parsed.query
        except Exception as e:
            print_error("JNO-019",f"Не удалось распарсить URL {url}: {e}","Пример: http://localhost:8080/api/status")
            return

        if verbose and not silent:
            print(f"*   Trying {host}:{port}...")
            print(f"* Connected to {host} port {port}")

        # Build request
        try:
            # Prepare data
            req_data=None
            if data:
                if isinstance(data,str):
                    req_data=data.encode()
                else:
                    req_data=data

            req=urllib.request.Request(url, data=req_data, method=method)
            # headers
            for k,v in headers.items():
                req.add_header(k,v)
            if auth:
                # Basic auth
                import base64 as b64
                enc=b64.b64encode(auth.encode()).decode()
                req.add_header("Authorization", f"Basic {enc}")
            if data and "Content-Type" not in headers and "content-type" not in [h.lower() for h in headers]:
                # default
                if data.strip().startswith("{"):
                    req.add_header("Content-Type","application/json")
                else:
                    req.add_header("Content-Type","application/x-www-form-urlencoded")
            if verbose and not silent:
                print(f"> {method} {path} HTTP/1.1")
                print(f"> Host: {host}:{port}")
                for k,v in headers.items():
                    print(f"> {k}: {v}")
                if data and not silent:
                    print(f">")
                    print(f"> {data[:200]}")
                print(f">")

            # Create context for https (ignore cert for simplicity)
            ctx=None
            if parsed.scheme=="https":
                ctx=ssl.create_default_context()
                ctx.check_hostname=False
                ctx.verify_mode=ssl.CERT_NONE

            # Handle redirects manually if follow_redirects else let urllib handle? We'll implement simple
            opener=urllib.request.build_opener(urllib.request.HTTPRedirectHandler() if follow_redirects else urllib.request.HTTPHandler())
            # Use urlopen with timeout
            response=urllib.request.urlopen(req, timeout=timeout, context=ctx)

            status=response.status
            resp_headers=response.headers
            body=response.read()

            # Try decode body
            try: body_text=body.decode('utf-8', errors='replace')
            except: body_text=str(body)

            if verbose and not silent:
                print(f"< HTTP/1.1 {status} {response.reason}")
                for hk,hv in resp_headers.items():
                    print(f"< {hk}: {hv}")
                print(f"<")

            if include_headers and not silent:
                print(f"HTTP/1.1 {status} {response.reason}")
                for hk,hv in resp_headers.items():
                    print(f"{hk}: {hv}")
                print("")

            # Check HTTP error status for JNO-020
            if status >= 400:
                if not silent:
                    print_error("JNO-020",f"HTTP {status} {response.reason} для {url}",f"Путь {path} не найден (404) или ошибка сервера (500). Проверь srv logs {host}, curl {url} -v для деталей")
                # Still show body if not silent? Show
                if output_file:
                    self.fs.write(output_file, body_text)
                    print(f"Saved error body to {output_file}")
                else:
                    if not silent:
                        print(body_text[:2000])
                return

            # Save or print
            if remote_name:
                # extract filename from URL
                fname=os.path.basename(parsed.path) or "index.html"
                if not fname or fname=="/": fname="index.html"
                out_path=self.fs.norm(fname)
                # if CWD relative, save to CWD
                if not output_file:
                    output_file=out_path
            if output_file:
                # save to JinoFS
                self.fs.write(output_file, body_text)
                if not silent:
                    print(f"{C_GREEN}Saved {len(body)} bytes to {output_file}{C_RESET}")
                    print(f"URL: {url} -> {output_file}")
            else:
                if not silent:
                    print(body_text)

        except urllib.error.HTTPError as e:
            # HTTP error with code
            try: body=e.read().decode()
            except: body=str(e)
            print_error("JNO-020",f"HTTP {e.code} {e.reason} для {url}: {body[:200]}","Проверь URL, путь. Для локальных: srv list, srv logs <name>. Для внешних: URL правильный?")
            if verbose:
                print(f"< HTTP/1.1 {e.code} {e.reason}")
                print(body[:1000])
            if output_file:
                self.fs.write(output_file, body)
                print(f"Saved error body to {output_file}")
        except urllib.error.URLError as e:
            reason=str(e.reason) if hasattr(e,'reason') else str(e)
            if "Connection refused" in reason or "refused" in reason.lower():
                print_error("JNO-017",f"Connection refused к {host}:{port} - {reason}","Сервер не запущен. Проверь: srv list (должен быть running), srv start <name>, порт правильный? Пример: curl http://localhost:8080/")
            elif "timed out" in reason.lower() or "timeout" in reason.lower():
                print_error("JNO-018",f"Timeout к {url}: {reason}","Сервер медленный или не отвечает. Попробуй: curl --connect-timeout 10 {url}, srv logs <name>, srv restart <name>")
            elif "Name or service not known" in reason or "getaddrinfo failed" in reason:
                print_error("JNO-019",f"DNS ошибка для {host}: {reason}","Проверь хост, /etc/hosts. Для локальных используй localhost, 127.0.0.1, jino.local. Пример: curl http://localhost:8080/")
            else:
                print_error("JNO-017",f"URLError {url}: {reason}","Проверь URL, сервер запущен, интернет (для внешних). Пример: ping {host}")
        except socket.timeout:
            print_error("JNO-018",f"Timeout подключения к {url} за {timeout}с","Увеличь таймаут: curl --connect-timeout 10 {url}. Проверь srv status")
        except ConnectionRefusedError:
            print_error("JNO-017",f"Connection refused {host}:{port}","Сервер не слушает. srv list покажет running. Запусти: srv start <name> (например srv start default) и проверь порт")
        except Exception as e:
            print_error("JNO-019",f"Ошибка curl {url}: {e}","Проверь curl --help, URL формат. Пример: curl http://localhost:8080/ -v")

    def cmd_wget(self,args):
        # wget is alias to curl with output
        # wget <url> [-O file]
        # Convert to curl args
        if not args:
            print_error("JNO-009","wget без URL","Пример: wget http://localhost:8080/ -O /tmp/page.html")
            return
        # parse
        url=None
        out=None
        i=0
        while i < len(args):
            if args[i]=="-O" and i+1 < len(args):
                out=args[i+1]; i+=2; continue
            if not args[i].startswith("-") and not url:
                url=args[i]
            i+=1
        if not url:
            print_error("JNO-019","wget без URL","")
            return
        curl_args=[url]
        if out:
            curl_args.extend(["-o", out])
        else:
            # default file from URL basename
            parsed=urllib.parse.urlparse(url)
            fname=os.path.basename(parsed.path) or "index.html"
            curl_args.extend(["-o", f"/tmp/{fname}"])
        self.cmd_curl(curl_args)

    # Other commands (short versions with errors)
    def cmd_ls(self,args):
        path="."; show_all=False; long=False; filtered=[]
        for a in args:
            if a.startswith("-"):
                if "a" in a: show_all=True
                if "l" in a: long=True
            else: filtered.append(a)
        if filtered: path=filtered[0]
        abs_path=self.fs.norm(path)
        listing=self.fs.list_dir(abs_path)
        if listing is None:
            s=self.fs.stat(abs_path)
            if s and s["type"]=="file":
                print(os.path.basename(abs_path)); return
            print_error("JNO-002",f"Путь {path} -> {abs_path} не найден","Проверь ls /, pwd, find / -name <часть>")
            return
        dirs,files=listing
        if not show_all:
            dirs=[d for d in dirs if not d.startswith(".")]; files=[f for f in files if not f.startswith(".")]
        items=[f"{C_BLUE}{d}/{C_RESET}" for d in dirs] + files
        print("  ".join(items) if items else "(empty) use ls -a")

    def cmd_pwd(self,args): print(self.fs.cwd)
    def cmd_cd(self,args):
        if not args:
            self.fs.cwd="/home/user"; return
        target=args[0]
        if target=="..":
            if self.fs.cwd!="/": self.fs.cwd=os.path.dirname(self.fs.cwd.rstrip("/")) or "/"
            return
        new_path=self.fs.norm(target)
        if new_path in self.fs.dirs:
            self.fs.cwd=new_path
        elif new_path in self.fs.files:
            print_error("JNO-004",f"cd {target} -> {new_path} это файл, а не папка","Используй cat {target} для просмотра файла, cd только для папок")
        else:
            if any(f.startswith(new_path+"/") for f in self.fs.files) or any(d.startswith(new_path+"/") for d in self.fs.dirs):
                self.fs.ensure_dir(new_path); self.fs.cwd=new_path
            else:
                print_error("JNO-002",f"cd {target} -> {new_path} папка не найдена","Проверь ls, ls {os.path.dirname(new_path)}, mkdir {target} для создания")
    def cmd_cat(self,args):
        if not args:
            print_error("JNO-009","cat без аргументов","Пример: cat /readme.txt, cat /www/index.html")
            return
        for p in args:
            c=self.fs.read(p)
            if c is None:
                # check if dir
                ap=self.fs.norm(p)
                if ap in self.fs.dirs:
                    print_error("JNO-003",f"cat {p} -> {ap} это папка","Используй ls {p} чтобы увидеть файлы внутри, затем cat {p}/index.html")
                else:
                    print_error("JNO-001",f"cat {p} файл не найден","Проверь ls {os.path.dirname(ap) or '/'}, find / -name {os.path.basename(p)}")
            else:
                print(c)
    def cmd_mkdir(self,args):
        if not args:
            print_error("JNO-009","mkdir без аргументов","Пример: mkdir /www/mysite, mkdir /home/user/docs")
            return
        for p in args:
            ok,msg=self.fs.mkdir(p)
            if not ok:
                print_error("JNO-006",f"mkdir {p}: {msg}","Папка уже есть, проверь ls, или используй другое имя")
            else:
                print(f"mkdir {msg}")
    def cmd_rm(self,args):
        if not args:
            print_error("JNO-009","rm без аргументов","Пример: rm /tmp/file.txt, rm -r /www/oldsite")
            return
        rec=False; targets=[]
        for a in args:
            if a in ("-r","-rf","-R"): rec=True
            else: targets.append(a)
        for p in targets:
            ap=self.fs.norm(p)
            if ap=="/":
                print_error("JNO-005",f"Попытка удалить корень /","Нельзя удалять /. Это уничтожит всю FS. Используй rm -r /path для конкретной папки")
                continue
            if self.fs.is_file(ap):
                self.fs.rm(ap); print(f"Removed {ap}")
            elif self.fs.is_dir(ap):
                if rec:
                    to_del=[f for f in self.fs.files if f==ap or f.startswith(ap+"/")]
                    for f in to_del: del self.fs.files[f]
                    to_del_d=[d for d in self.fs.dirs if d==ap or d.startswith(ap+"/")]
                    for d in to_del_d:
                        if d in self.fs.dirs: self.fs.dirs.remove(d)
                    self.fs.dirs.add("/"); self.fs.save_persist(); print(f"Removed dir {ap} recursively ({len(to_del)} files)")
                else:
                    print_error("JNO-007",f"rm {p} это папка, не пустая или без -r","Используй rm -r {p} для рекурсивного удаления, или rmdir если пустая. Сначала ls {p}")
            else:
                print_error("JNO-001",f"rm {p} -> {ap} не найден","Проверь ls {os.path.dirname(ap) or '/'}, find / -name {os.path.basename(p)}")
    def cmd_echo(self,args,raw,redir_out,redir_append):
        import re
        m=re.search(r'echo\s+(.*)',raw,re.IGNORECASE); text=m.group(1) if m else " ".join(args)
        if redir_out: text=text.split(">")[0].strip().strip('"')
        if redir_out:
            path=self.fs.norm(redir_out)
            if path=="/":
                print_error("JNO-021",f"echo > / попытка записи в корень","Пиши в файл: echo hi > /tmp/hi.txt")
                return
            if redir_append: existing=self.fs.read(path) or ""; self.fs.write(path,existing+text+"\n")
            else: self.fs.write(path,text+"\n")
            print(f"-> {path}")
        else: print(text)
    def cmd_write(self,args):
        if not args:
            print_error("JNO-009","write/edit без файла","Пример: write /home/user/notes.txt, затем вводи строки, . для сохранения")
            return
        path=args[0]; print(f"Write to {path}, '.' or ':wq' to save, ':q!' abort")
        lines=[]
        try:
            while True:
                line=input(f"{len(lines)+1}> ")
                if line in (".",":wq"): break
                if line==":q!": print("Abort"); return
                lines.append(line)
        except EOFError: pass
        self.fs.write(path,"\n".join(lines)); print("Saved")
    def cmd_clear(self,args): os.system("clear||cls"); print("\033[2J\033[H",end="")
    def cmd_history(self,args):
        for i,h in enumerate(self.history[-100:],1): print(f"{i:4} {h}")
    def cmd_mem(self,args): print(f"32M total, files {len(self.fs.files)}")
    def cmd_ps(self,args):
        print("PID NAME STATUS PORT")
        for s in self.srv_manager.list_servers():
            print(f"{s.port} {s.name} {s.status} :{s.port}")
    def cmd_jdb(self,args):
        if not args:
            print_error("JNO-009","jdb без аргументов","Пример: jdb set mykey myvalue, jdb get mykey, jdb list")
            return
        if args[0]=="set" and len(args)>=3: self.jdb[args[1]]=" ".join(args[2:]); print(f"OK {args[1]}")
        elif args[0]=="get" and len(args)>=2:
            if args[1] not in self.jdb:
                print_error("JNO-022",f"Ключ {args[1]} не найден в JinoDB","jdb list покажет все ключи, jdb set {args[1]} value для создания")
            else:
                print(self.jdb.get(args[1]))
        elif args[0]=="list":
            for k,v in self.jdb.items(): print(f"{k}={v}")
        elif args[0]=="del" and len(args)>=2:
            if args[1] not in self.jdb:
                print_error("JNO-022",f"Ключ {args[1]} не найден для удаления","jdb list")
            else:
                self.jdb.pop(args[1],None); print("Del")
        else:
            print_error("JNO-009",f"jdb {args[0]} неверно","Использование: jdb set <k> <v> | get <k> | list | del <k>")
    def cmd_calc(self,args):
        if not args:
            print_error("JNO-009","calc без выражения","Пример: calc 2+2*2, calc sqrt(16)+sin(0.5)")
            return
        expr=" ".join(args).replace("^","**")
        try: print(eval(expr,{"__builtins__":{}},{"sin":math.sin,"cos":math.cos,"sqrt":math.sqrt,"pi":math.pi}))
        except Exception as e: print(f"calc error: {e}")
    def cmd_ver(self,args): print(f"Jino OS {VERSION} Build {BUILD} Files {len(self.fs.files)} Servers {len(self.srv_manager.servers)}")
    def cmd_date(self,args): print(datetime.datetime.now())
    def cmd_reboot(self,args): self.boot()
    def cmd_shutdown(self,args): print("Shutdown"); sys.exit(0)

    def dispatch(self,line):
        if not line.strip(): return
        self.history.append(line)
        parts,redir_out,redir_append=self.parse(line)
        if not parts: return
        cmd=parts[0].lower(); args=parts[1:]; raw=line
        try:
            if cmd in ("ls","dir","ll","la","l"): self.cmd_ls(args)
            elif cmd=="pwd": self.cmd_pwd(args)
            elif cmd=="cd": self.cmd_cd(args)
            elif cmd in ("cat","type"): self.cmd_cat(args)
            elif cmd in ("mkdir","md"): self.cmd_mkdir(args)
            elif cmd in ("rm","del","rmdir","rd"): self.cmd_rm(args)
            elif cmd=="echo": self.cmd_echo(args,raw,redir_out,redir_append); return
            elif cmd in ("write","edit","nano"): self.cmd_write(args)
            elif cmd in ("clear","cls"): self.cmd_clear(args)
            elif cmd=="history": self.cmd_history(args)
            elif cmd in ("mem","free"): self.cmd_mem(args)
            elif cmd=="ps": self.cmd_ps(args)
            elif cmd=="jdb": self.cmd_jdb(args)
            elif cmd in ("calc","bc"): self.cmd_calc(args)
            elif cmd in ("ver","version"): self.cmd_ver(args)
            elif cmd=="date": self.cmd_date(args)
            elif cmd in ("reboot","shutdown","exit","quit","poweroff"):
                if cmd=="reboot": self.cmd_reboot(args)
                else: self.cmd_shutdown(args)
            elif cmd=="help": self.cmd_help(args)
            elif cmd=="errors": self.cmd_errors(args)
            elif cmd=="error": self.cmd_errors(args)
            elif cmd=="cmds": self.cmd_cmds(args)
            elif cmd=="jpkg": self.cmd_jpkg(args)
            elif cmd in ("srv","server","service","systemctl"): self.cmd_srv(args)
            elif cmd in ("deploy","serve","web","install-server"): self.cmd_deploy(args)
            elif cmd=="curl": self.cmd_curl(args)
            elif cmd=="wget": self.cmd_wget(args)
            elif cmd in ("man","whatis"):
                if not args: print(f"man <cmd>. Пример: man curl, man jpkg")
                else:
                    c=args[0]
                    if c=="curl": self.cmd_curl(["--help"])
                    elif c in ERRORS: self.cmd_errors([c])
                    else: print(f"man {c}: пока нет страницы, попробуй {c} --help или help")
            else:
                print_error("JNO-008",f"Команда {cmd} не найдена","Напиши cmds для списка всех 100+ команд, help для справки, errors для ошибок")
        except Exception as e:
            import traceback
            print(f"{C_RED}[Kernel Panic] {e}{C_RESET}")
            traceback.print_exc()

    def run(self):
        self.boot()
        while True:
            try:
                prompt=f"{C_BOLD}{C_GREEN}{self.env['USER']}@{self.env['HOST']}{C_RESET}:{C_BLUE}{self.fs.cwd}{C_RESET}$ "
                line=input(prompt)
                self.dispatch(line)
            except KeyboardInterrupt: print("\nUse exit")
            except EOFError: break
            except SystemExit: break
            except Exception as e: import traceback; print(f"Panic {e}"); traceback.print_exc()

if __name__=="__main__":
    os.makedirs(RUNTIME_ROOT,exist_ok=True)
    JinoOS().run()
