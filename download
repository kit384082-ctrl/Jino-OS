#!/usr/bin/env python3
"""
Jino OS v3.0 Hybrid Edition
- Language selection before install (EN/RU)
- Full English translation (default EN)
- Console + GUI hybrid (console remains, GUI optional)
- Easy Server Installer + Full Errors + Real curl
Build: 2026-07-13 HYBRID
"""
import os, sys, time, json, shlex, base64, re, random, math
import shutil, datetime, socket, threading, urllib.request, urllib.parse, urllib.error
import http.client, ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION="3.0 Hybrid EN+GUI+Console"
BUILD="2026-07-13 HYBRID"
C_RESET="\033[0m"; C_GREEN="\033[92m"; C_YELLOW="\033[93m"; C_CYAN="\033[96m"; C_RED="\033[91m"; C_MAGENTA="\033[95m"; C_BLUE="\033[94m"; C_BOLD="\033[1m"; C_DIM="\033[2m"
REPO_PATH="/home/user/JinoOS/packages/repo.json"
RUNTIME_ROOT="/tmp/jino_runtime"
SERVERS_DB="/tmp/jino_servers_db.json"
LANG_DIR="/home/user/JinoOS/lang"
CONFIG_PATH="/tmp/jino_config.json"

# Load languages
def load_lang(code):
    try:
        path=os.path.join(LANG_DIR, f"{code}.json")
        with open(path,'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

LANG_EN=load_lang("en")
LANG_RU=load_lang("ru")
CURRENT_LANG="en"
LANG_DATA=LANG_EN

def t(path, default=""):
    # path like "boot.title"
    parts=path.split(".")
    cur=LANG_DATA
    try:
        for p in parts:
            cur=cur[p]
        return cur
    except:
        # fallback to default or path
        return default or path

def set_language(code):
    global CURRENT_LANG, LANG_DATA
    code=code.lower()
    if code in ("ru","russian","2","русский"):
        CURRENT_LANG="ru"
        LANG_DATA=LANG_RU
    else:
        CURRENT_LANG="en"
        LANG_DATA=LANG_EN
    # save config
    try:
        with open(CONFIG_PATH,'w') as f:
            json.dump({"lang":CURRENT_LANG}, f)
    except: pass

def load_config_lang():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH,'r') as f:
                data=json.load(f)
                return data.get("lang","en")
    except: pass
    return None

# ERRORS - now English primary with translations
ERRORS_EN = {
    "JNO-001": {"title": "File not found", "msg": "Specified file does not exist in JinoFS", "cause": "Wrong path, file deleted, typo, wrong directory", "fix": "Check ls, find, pwd. Example: ls /www, find / -name *.txt", "example": "cat /nope.txt -> JNO-001. Correct: ls /, then cat /readme.txt"},
    "JNO-002": {"title": "Directory not found", "msg": "Specified directory does not exist", "cause": "Wrong path, dir not created, cd to non-existing", "fix": "Use mkdir to create, ls to check. cd /home/user", "example": "cd /nosuch -> JNO-002. Do: mkdir /nosuch, then cd"},
    "JNO-003": {"title": "Is a directory", "msg": "Attempt to read directory as file", "cause": "cat /www instead of cat /www/index.html", "fix": "Use ls /www to see files inside, then cat /www/index.html", "example": "cat /www -> JNO-003. Correct: ls /www, cat /www/index.html"},
    "JNO-004": {"title": "Not a directory", "msg": "Attempt to cd into file", "cause": "cd /readme.txt - readme.txt is file", "fix": "Use cat for files, cd only for dirs. Check stat <path>", "example": "cd /readme.txt -> JNO-004. Correct: cat /readme.txt"},
    "JNO-005": {"title": "Permission denied", "msg": "No permission for operation (simulated)", "cause": "Trying to delete / , modify system file", "fix": "Check chmod, don't touch /etc unless sure. For / use -r", "example": "rmdir / -> JNO-005. Cannot delete root."},
    "JNO-006": {"title": "File exists", "msg": "File or dir already exists", "cause": "mkdir existing, cp to existing without overwrite, jpkg install existing server", "fix": "Use ls to check, rm to delete old, or different name --name", "example": "mkdir /www -> JNO-006. /www already exists. Use mkdir /www/newsite"},
    "JNO-007": {"title": "Directory not empty", "msg": "Cannot delete non-empty dir without -r", "cause": "rmdir /home/user when files inside", "fix": "Use rm -r for recursive, or delete files inside: ls /home/user, rm /home/user/*", "example": "rmdir /www -> JNO-007. Do rm -r /www"},
    "JNO-008": {"title": "Command not found", "msg": "Unknown command", "cause": "Typo, command from other OS, GUI command in console", "fix": "Type cmds for list, help for help, man <cmd>", "example": "sl -> JNO-008. Try ls, cowsay"},
    "JNO-009": {"title": "Invalid arguments", "msg": "Wrong usage of command", "cause": "Missing args, wrong flags", "fix": "Use man <cmd> or <cmd> without args for hint", "example": "cp /readme.txt -> JNO-009. Need: cp src dst"},
    "JNO-010": {"title": "Port already in use", "msg": "Port already used by another server", "cause": "Two servers on same port, system port (80,3000), server not stopped", "fix": "srv list shows used ports. Use srv stop <name> or different port: --port 8081", "example": "srv start nginx (8080 busy) -> JNO-010. Do srv list, srv stop old, or jpkg install nginx --port 8081"},
    "JNO-011": {"title": "Server not found", "msg": "Server with such name not installed", "cause": "Typo, server not installed via jpkg, deleted", "fix": "srv list shows installed. jpkg list - all available. jpkg install <pkg>", "example": "srv start myblog -> JNO-011 if not exists. Do srv list, then jpkg install nginx --name myblog"},
    "JNO-012": {"title": "Package not found", "msg": "Package not found in Jino repo", "cause": "Typo, package doesn't exist, outdated repo", "fix": "jpkg list shows 18 packages, jpkg search <term>, jpkg update", "example": "jpkg install ngnix -> JNO-012 typo. Correct: jpkg install nginx"},
    "JNO-013": {"title": "Server already running", "msg": "Attempt to start already running server", "cause": "srv start twice", "fix": "srv status <name> checks, srv restart for restart", "example": "srv start nginx when running -> JNO-013. Do srv restart nginx"},
    "JNO-014": {"title": "Server not running", "msg": "Attempt to stop not running server", "cause": "srv stop on stopped", "fix": "srv status <name> shows status, srv list shows running/stopped", "example": "srv stop nginx when stopped -> JNO-014"},
    "JNO-015": {"title": "Invalid port", "msg": "Port must be number 1-65535", "cause": "Letters instead of number, port 0, >65535", "fix": "Use 8000-9000 for tests, 3000,5000,8080-8089. Example: --port 8080", "example": "srv create my --port abc -> JNO-015. Correct: --port 8080"},
    "JNO-016": {"title": "Invalid path", "msg": "Path contains invalid chars or empty", "cause": "Empty path, invalid chars", "fix": "Use absolute paths: /www, /home/user/docs", "example": "cd '' -> JNO-016. Correct: cd /home/user"},
    "JNO-017": {"title": "Connection refused", "msg": "curl cannot connect - port not listening", "cause": "Server not started (srv start), wrong port, firewall", "fix": "srv list shows running. srv start <name>. Check port: curl http://localhost:PORT/", "example": "curl http://localhost:8080/ when stopped -> JNO-017. Do srv start myserver"},
    "JNO-018": {"title": "Timeout", "msg": "Server did not answer in time", "cause": "Slow server, network, hang, big file", "fix": "Try again, increase timeout: curl --connect-timeout 10 <url>. Check srv logs, srv restart", "example": "curl http://slow.site/ -> JNO-018. Try curl --connect-timeout 10"},
    "JNO-019": {"title": "Invalid URL", "msg": "URL has invalid format", "cause": "No http://, typo, spaces, unsupported protocol", "fix": "Use full URL: http://localhost:8080/, https://example.com/api. For files use file:///www/index.html or cat /www/index.html", "example": "curl localhost:8080 -> JNO-019? Better curl http://localhost:8080/"},
    "JNO-020": {"title": "HTTP error", "msg": "Server returned 4xx or 5xx", "cause": "404 - not found, 403 - forbidden, 500 - server error", "fix": "Check path: /api/status exists, /nope not. srv logs shows logs. For 500 - restart", "example": "curl http://localhost:8080/nope -> HTTP 404 JNO-020. Try curl http://localhost:8080/api/status"},
    "JNO-021": {"title": "Write error", "msg": "Failed to write file", "cause": "Disk full (sim), wrong path, no permission", "fix": "Check df, path. Try other path: /tmp/", "example": "echo hi > / -> JNO-021. Cannot write to / directly. Write to /tmp/hi.txt"},
    "JNO-022": {"title": "JDB key not found", "msg": "Key does not exist in JinoDB", "cause": "jdb get non-existing key", "fix": "jdb list shows all keys, jdb set <k> <v> to create", "example": "jdb get nokey -> JNO-022. Do jdb list, then jdb set nokey value"},
    "JNO-023": {"title": "Invalid method", "msg": "curl -X with unsupported method", "cause": "Methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS. Typo", "fix": "Use: curl -X GET http://..., curl -X POST -d data ...", "example": "curl -X FOOBAR -> JNO-023. Correct: -X POST"}
}

ERRORS_RU = {
    "JNO-001": {"title": "Файл не найден", "msg": "Указанный файл не существует в JinoFS", "cause": "Путь неверный, файл удален, опечатка, не в той папке", "fix": "Проверь ls, find, pwd. Пример: ls /www, find / -name *.txt", "example": "cat /nope.txt -> JNO-001. Правильно: ls /, затем cat /readme.txt"},
    "JNO-002": {"title": "Папка не найдена", "msg": "Указанная директория не существует", "cause": "Неверный путь, папка не создана, cd в несуществующую", "fix": "Используй mkdir, ls. cd /home/user", "example": "cd /nosuch -> JNO-002. Сделай mkdir /nosuch"},
    # For brevity, other errors will fallback to EN if not translated, but we have all EN
}

def get_error(code):
    code=code.upper()
    if not code.startswith("JNO-"):
        code="JNO-"+code.zfill(3) if code.isdigit() else "JNO-"+code
        # fix if code like "001" -> JNO-001
        if code.startswith("JNO--"): code=code.replace("JNO--","JNO-")
        if len(code)==6 and code[4:].isdigit(): # JNO-1 -> JNO-001
            num=code.split("-")[1]
            code=f"JNO-{int(num):03d}"
    # choose lang
    if CURRENT_LANG=="ru":
        return ERRORS_RU.get(code) or ERRORS_EN.get(code)
    else:
        return ERRORS_EN.get(code)

def print_error(code, context="", extra=""):
    err=get_error(code)
    if not err:
        print(f"{C_RED}[{code}] Unknown error: {context}{C_RESET}")
        return
    # English version primary
    print(f"{C_RED}{C_BOLD}┌─ ERROR {code}: {err['title']}{C_RESET}")
    print(f"{C_RED}│ Message: {err['msg']}{C_RESET}")
    if context:
        print(f"{C_RED}│ Context: {context}{C_RESET}")
    print(f"{C_YELLOW}│ Cause: {err['cause']}{C_RESET}")
    print(f"{C_GREEN}│ Fix: {err['fix']}{C_RESET}")
    print(f"{C_DIM}│ Example: {err['example']}{C_RESET}")
    if extra:
        print(f"{C_CYAN}│ Extra: {extra}{C_RESET}")
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
        mkfile("/readme.txt","Jino OS v3.0 Hybrid Edition\nConsole + GUI + Easy Server Installer\n\nType 'help', 'gui', 'jpkg list', 'srv list', 'curl --help'\nLanguage: EN/RU selectable at boot with 'lang' command\n")
        mkfile("/autoexec.jino","echo Jino OS 3.0 Hybrid Booted\nver\nsrv list\n")
        mkfile("/www/index.html","<html><head><title>JinoServer</title></head><body><h1>JinoServer v3.0 Hybrid Works!</h1><p>Default :80</p><p>Console: terminal app | <a href='/api/status'>/api/status</a></p></body></html>")
        mkfile("/etc/hosts","127.0.0.1 localhost\n127.0.0.1 jino.local\n")
        mkfile("/etc/config.sys","memory=32MB\nfs=JinoFS v3\nshell=JinoSH 3.0 Hybrid\nmode=console+gui\n")
        mkfile("/apps/hello.japp",'print("Hello Jino Hybrid!")\n')
        mkfile("/home/user/notes.txt","Notes hybrid\n")
        mkfile("/system/motd.txt","Welcome to Jino OS v3.0 Hybrid! Console is primary, GUI optional. Type 'gui' to launch GUI.\n")
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
    def rm(self,path):
        p=self.norm(path)
        if p in self.files: del self.files[p]; self.save_persist(); return True
        return False

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
                        content=fdata["content"].replace("{{SERVER_NAME}}",self.name).replace("{{PORT}}",str(self.port)).replace("{{ROOT}}",self.root)
                        out.write(content)
                except: pass
        idx=os.path.join(self.real_root,"index.html")
        if not os.path.exists(idx):
            with open(idx,'w') as f: f.write(f"<html><body><h1>{self.name} - {self.type}</h1><p>Port {self.port} Root {self.root}</p><p>Console: <a href='/api/status'>/api/status</a></p></body></html>")
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
                        html=f"<h1>404 - {self.path}</h1><p>Server {server_name}</p>"
                        self.wfile.write(html.encode())
            def handle_api(self):
                if self.path.startswith("/api/status"):
                    info={"server":server_name,"type":server_config.get("type"),"port":server_config.get("port"),"root":server_config.get("root"),"status":"running","uptime":time.time()-(server_config.get("start_time",time.time())),"jino_version":VERSION,"lang":CURRENT_LANG,"mode":"hybrid console+gui"}
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
            html=f"<html><head><title>{srv_name}</title></head><body><h1>{srv_name} ({name})</h1><p>Port {srv_port} Root {srv_root}</p><p><a href='/api/status'>/api/status</a></p></body></html>"
            self.fs.write(f"{srv_root}/index.html",html)
        ok,res=self.srv.create(srv_name,template=srv_type if srv_type!="server" else "static",port=srv_port,root=srv_root,extra={"pkg":name,"version":pkg.get("version")})
        if not ok: return False,res
        return True,f"Installed {name} as '{srv_name}' on :{srv_port} root {srv_root}. Run 'srv start {srv_name}'"

class GUIManager:
    def __init__(self, fs_ref, jdb_ref, srv_manager):
        self.fs=fs_ref; self.jdb=jdb_ref; self.srv=srv_manager
        self.running=False

    def launch_console_gui(self):
        # ASCII art GUI simulation in console
        print(C_CYAN+C_BOLD)
        print("┌─────────────────────────────────────────────────────────┐")
        print("│  JinoWM - Window Manager v3.0 Hybrid                    │")
        print("│  Console remains active underneath                      │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│  [Desktop]                                              │")
        print("│   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │")
        print("│   │ File Manager│  │ Terminal    │  │ Browser      │   │")
        print("│   │ 📁 JinoFS   │  │ 💻 JinoSH   │  │ 🌐 Server    │   │")
        print("│   │ /www/       │  │ console=ON  │  │ :80          │   │")
        print("│   └─────────────┘  └─────────────┘  └──────────────┘   │")
        print("│   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │")
        print("│   │ Editor      │  │ JinoDB      │  │ Settings     │   │")
        print("│   │ 📝 Edit     │  │ 🗄️  DB      │  │ ⚙️ Lang EN/RU│   │")
        print("│   └─────────────┘  └─────────────┘  └──────────────┘   │")
        print("│                                                         │")
        print("│   [Start: Jino]  [Terminal] [Files] [Browser]   [EN]   │")
        print("└─────────────────────────────────────────────────────────┘")
        print(C_RESET)
        print(f"{C_GREEN}GUI simulation started. In real hardware, VGA 320x200 mode would activate.{C_RESET}")
        print(f"{C_YELLOW}For full graphical browser GUI, open: emulator/index.html{C_RESET}")
        print(f"{C_DIM}Console is still running in background. Type 'exit-gui' to return, or keep using commands.{C_RESET}")
        print("")
        # Simulate GUI loop with commands
        while True:
            try:
                cmd=input(f"{C_BOLD}[GUI] jino@desktop > {C_RESET}").strip()
                if cmd in ("exit","exit-gui","console","q"):
                    print(f"{C_YELLOW}Exiting GUI, returning to console...{C_RESET}")
                    break
                elif cmd=="terminal":
                    print("Opening Terminal... (console stays)")
                    # simulate terminal launch
                    print(f"{C_GREEN}Terminal: console is still active, same JinoFS{C_RESET}")
                elif cmd=="files":
                    print("File Manager: /www, /home/user etc. Use ls in console or GUI file list")
                elif cmd.startswith("lang"):
                    parts=cmd.split()
                    if len(parts)>1:
                        set_language(parts[1])
                        print(f"Language switched to {CURRENT_LANG}")
                    else:
                        print(f"Current lang: {CURRENT_LANG}. Usage: lang en|ru")
                elif cmd=="help":
                    print("GUI Help: terminal, files, browser, editor, exit-gui, lang en|ru")
                elif cmd=="browser":
                    print("Browser would open http://localhost:80/ - use curl in console")
                else:
                    print(f"GUI app '{cmd}' would launch. Console commands still work. Try 'terminal', 'files', 'exit-gui'")
            except KeyboardInterrupt:
                break
        self.running=False

class JinoOS:
    def __init__(self):
        self.fs=JinoFS()
        self.jdb={"visits":"1","user":"jino","hostname":"jino-pc","boot_time":str(int(time.time())),"lang":CURRENT_LANG}
        self.history=[]; self.aliases={"ll":"ls -l","la":"ls -a","dir":"ls","..":"cd ..","h":"history","?":"help","cls":"clear","startx":"gui","jindowm":"gui"}
        self.env={"USER":"jino","HOME":"/home/user","PATH":"/bin","SHELL":"/bin/jinosh","OS":"Jino OS 3.0 Hybrid","TERM":"jino-256color","PWD":self.fs.cwd,"HOST":"jino-pc","EDITOR":"nano","LANG":CURRENT_LANG}
        self.srv_manager=ServerManager(self.fs,self.jdb)
        self.pkg_manager=PackageManager(self.fs,self.srv_manager,self.jdb)
        self.gui_manager=GUIManager(self.fs,self.jdb,self.srv_manager)
        self.uptime_start=time.time(); self.last_exit_code=0

    def select_language(self):
        # Check if config exists
        saved=load_config_lang()
        if saved:
            set_language(saved)
            return
        print(C_BOLD+C_CYAN)
        print("="*60)
        print(f"  {t('boot.title','Jino OS v3.0 Hybrid Edition')}")
        print(f"  {t('boot.subtitle','Console + GUI + Easy Server Installer')}")
        print("="*60)
        print(C_RESET)
        print(f"{C_YELLOW}{t('boot.select_language','Select system language')} {C_RESET}")
        print(f"  {t('boot.options','1) English (EN)  2) Русский (RU)')}")
        try:
            choice=input(t('boot.prompt','Choose [1-2, default EN]: ')).strip()
            if choice=="2" or choice.lower() in ("ru","russian","русский"):
                set_language("ru")
                print(f"{C_GREEN}{t('boot.chosen','Language set to English')}{C_RESET}")
            else:
                set_language("en")
                print(f"{C_GREEN}Language set to English. System will boot in English.{C_RESET}")
        except:
            set_language("en")
        print()

    def boot(self):
        print(C_GREEN+C_BOLD+r"""
     ██╗██╗███╗   ██╗ ██████╗      ██████╗ ███████╗
     ██║██║████╗  ██║██═══██╗    ██╔═══██╗██╔════╝
     ██║██║██╔██╗ ██║██║   ██║    ██║   ██║███████╗
██   ██║██║██║╚██╗██║██║   ██║    ██║   ██║╚════██║
╚█████╔╝██║██║ ╚████║╚██████╔╝    ╚██████╔╝███████║
 ╚════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝      ╚═════╝ ╚══════╝

          HYBRID EDITION v3.0 - CONSOLE + GUI + SERVERS
"""+C_RESET)
        print(f"{C_CYAN}Jino OS {VERSION} | {BUILD} | Lang={CURRENT_LANG.upper()} | 32MB | i386{C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_kernel','Loading JinoKernel 3.0...')}{C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_mem','Memory Manager: 32 MB')}{C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_fs','JinoFS v3 mounted')} ({len(self.fs.files)} files){C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_gui','JinoGUI Window Manager ready')}{C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_servers','Server Manager ready')} ({len(self.srv_manager.servers)} servers){C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_repo','Repo')} {len(self.pkg_manager.repo.get('packages',[]))} packages{C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_errors','Error system loaded')} 23 codes{C_RESET}")
        print(f"{C_GREEN}[OK] {t('boot.loading_curl','curl loaded')}{C_RESET}")
        motd_tag=t('motd','Welcome')
        print(f"{C_YELLOW}{motd_tag}{C_RESET}")
        print(f"Type {C_BOLD}help{C_RESET}, {C_BOLD}gui{C_RESET} for GUI, {C_BOLD}jpkg list{C_RESET}, {C_BOLD}lang en|ru{C_RESET} to switch language")
        print()

    def parse(self,line):
        stripped=line.strip()
        if not stripped: return [],None,False
        first=stripped.split()[0]
        if first in self.aliases: line=self.aliases[first]+" "+" ".join(stripped.split()[1:])
        redirect_out=None; redirect_append=False
        if ">" in line and "curl" not in line.split()[0]:
            m=re.search(r'\s*(>>|>)\s*([^\s]+)\s*$', line)
            if m and not m.group(2).startswith("http"):
                op=m.group(1); target=m.group(2); redirect_out=target; redirect_append=(op==">>"); line=line[:m.start()].strip()
        try: parts=shlex.split(line)
        except: parts=line.split()
        return parts,redirect_out,redirect_append

    # Commands
    def cmd_help(self,args):
        print(f"{C_BOLD}{C_GREEN}{t('help.title','Jino OS v3.0 Hybrid Help')}{C_RESET}")
        print(t('help.intro','Hybrid Edition: Console main, GUI optional'))
        print("")
        print(f"{C_BOLD}{t('help.quick','QUICK START:')}{C_RESET}")
        for item in t('help.quick_items',[]):
            if isinstance(item,str): print(f"  {item}")
        print("")
        print(f"{C_BOLD}{t('help.gui','GRAPHICAL INTERFACE:')}{C_RESET}")
        for item in t('help.gui_items',[]):
            if isinstance(item,str): print(f"  {item}")
        print("")
        print(f"{C_BOLD}BASE COMMANDS:{C_RESET}")
        print("  FS: ls ll pwd cd cat bat mkdir rmdir rm cp mv find tree du df")
        print("  TEXT: echo write edit head tail wc grep hexdump base64")
        print("  SYS: ver sysinfo date clear history mem ps errors lang")
        print("  NET: curl <url> [-o file] [-X POST] [-d data] [-i] [-v], wget, jpkg, srv, deploy")
        print("  GUI: gui, startx, jindowm, exit-gui")

    def cmd_lang(self,args):
        if not args:
            print(f"Current language: {CURRENT_LANG} ({LANG_DATA.get('lang_name','')})")
            print("Available: en (English), ru (Русский)")
            print("Usage: lang en | lang ru | lang --list")
            return
        if args[0]=="--list":
            print("Available languages:")
            print("  en - English (default)")
            print("  ru - Русский")
            return
        code=args[0].lower()
        if code in ("en","english","1"):
            set_language("en")
            print(f"{C_GREEN}Language switched to English. Type 'help' for English help.{C_RESET}")
        elif code in ("ru","russian","2","русский"):
            set_language("ru")
            print(f"{C_GREEN}Язык переключен на Русский. Введи 'help' для справки на русском.{C_RESET}")
        else:
            print_error("JNO-009",f"Unknown language {code}",f"Available: en, ru. Usage: lang en")

    def cmd_gui(self,args):
        if args and args[0]=="--browser":
            print(f"{C_YELLOW}{t('gui.browser_hint','Open emulator/index.html in browser')}{C_RESET}")
            # try open browser if possible
            try:
                import webbrowser
                path=os.path.join("/home/user/JinoOS/emulator/index.html")
                if os.path.exists(path):
                    webbrowser.open(f"file://{path}")
                    print(f"{C_GREEN}Browser opened {path}{C_RESET}")
                else:
                    print(f"{C_RED}File not found {path}{C_RESET}")
            except Exception as e:
                print(f"{C_RED}Cannot open browser: {e}{C_RESET}")
                print(f"Manually open emulator/index.html")
            return
        print(f"{C_CYAN}{t('gui.starting','Starting JinoGUI...')}{C_RESET}")
        self.gui_manager.launch_console_gui()

    def cmd_errors(self,args):
        if args and args[0].upper().startswith("JNO-"):
            code=args[0].upper()
            err=get_error(code)
            if err:
                print(f"{C_BOLD}{code}: {err['title']}{C_RESET}")
                print(f"Message: {err['msg']}")
                print(f"Cause: {err['cause']}")
                print(f"Fix: {err['fix']}")
                print(f"Example: {err['example']}")
            else:
                print(f"Unknown {code}")
            return
        if args and args[0].isdigit():
            code=f"JNO-{int(args[0]):03d}"
            err=get_error(code)
            if err:
                print(f"{C_BOLD}{code}: {err['title']}{C_RESET}")
                print(f"Message: {err['msg']}")
                print(f"Cause: {err['cause']}")
                print(f"Fix: {err['fix']}")
                print(f"Example: {err['example']}")
            return
        print(f"{C_BOLD}Full error list ({len(ERRORS_EN)} codes):{C_RESET}")
        for code,err in ERRORS_EN.items():
            print(f"{C_RED}{code}{C_RESET}: {err['title']}")
        print(f"\nFor details: errors JNO-001 or errors 001")

    # Include previous commands (short versions)
    def cmd_jpkg(self,args):
        if not args:
            print_error("JNO-009","jpkg without args","Usage: jpkg list, jpkg install <pkg>")
            return
        sub=args[0]
        if sub=="list":
            filt=args[1] if len(args)>1 else None
            pkgs=self.pkg_manager.list_packages(filt)
            print(f"{C_BOLD}Repo - {len(pkgs)} pkgs{C_RESET}")
            for p in pkgs: print(f"{C_GREEN}{p['name']:<20}{C_RESET} {p.get('version',''):<10} {str(p.get('port','-')):<6} {p.get('description','')[:50]}")
        elif sub=="search":
            term=args[1] if len(args)>1 else ""
            if not term:
                print_error("JNO-009","jpkg search without term","Example: jpkg search nginx")
                return
            res=self.pkg_manager.search(term)
            if not res: print_error("JNO-012",f"search '{term}' nothing found","Try: jpkg list")
            else:
                for p in res: print(f" {p['name']:<20} {p.get('description','')}")
        elif sub=="install":
            if len(args)<2:
                print_error("JNO-009","jpkg install without package","Example: jpkg install nginx --port 8080 --name myweb")
                return
            pkg_name=args[1]; port=None; custom_name=None; root=None; i=2
            while i < len(args):
                if args[i]=="--port" and i+1<len(args):
                    try: port=int(args[i+1])
                    except: print_error("JNO-015",f"Port {args[i+1]} not number","Example: --port 8080"); return
                    i+=2; continue
                if args[i]=="--name" and i+1<len(args): custom_name=args[i+1]; i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            ok,msg=self.pkg_manager.install(pkg_name,port=port,custom_name=custom_name,root=root)
            print(f"{C_GREEN if ok else C_RED}{msg}{C_RESET}")
        elif sub in ("uninstall","remove"):
            if len(args)<2: print_error("JNO-009","jpkg uninstall without name","Example: jpkg uninstall myweb"); return
            ok,msg=self.srv_manager.delete(args[1]); print(msg)
        elif sub=="info":
            if len(args)<2: print_error("JNO-009","jpkg info without name","Example: jpkg info nginx"); return
            pkg=self.pkg_manager.get_pkg(args[1])
            print(json.dumps(pkg,indent=2) if pkg else "Not found")
        else: print_error("JNO-008",f"jpkg {sub} unknown","Available: list, search, install, uninstall, info")

    def cmd_srv(self,args):
        if not args:
            print_error("JNO-009","srv without args","Usage: srv list, srv start <name>, srv new")
            return
        sub=args[0]
        if sub in ("list","ls"):
            servers=self.srv_manager.list_servers()
            if not servers: print("(no servers) jpkg list"); return
            print(f"{'NAME':<15} {'TYPE':<12} {'PORT':<6} {'STATUS':<10} URL")
            for s in servers:
                st=s.get_status(); col=C_GREEN if st["status"]=="running" else C_RED
                print(f"{st['name']:<15} {st['type']:<12} {str(st['port']):<6} {col}{st['status']:<10}{C_RESET} http://localhost:{st['port']}")
        elif sub=="create":
            if len(args)<2: print_error("JNO-009","srv create without name","Example: srv create myblog --template static --port 8080 --root /www/myblog"); return
            name=args[1]; template="static"; port=8080; root=f"/www/{name}"; i=2
            while i < len(args):
                if args[i]=="--template" and i+1<len(args): template=args[i+1]; i+=2; continue
                if args[i]=="--port" and i+1<len(args):
                    try: port=int(args[i+1])
                    except: print_error("JNO-015",f"Port {args[i+1]} not number",""); return
                    i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            ok,res=self.srv_manager.create(name,template=template,port=port,root=root)
            print(f"{C_GREEN if ok else C_RED}{res}{C_RESET}")
        elif sub=="start":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.start_all(): print(f"{name}: {msg}")
                    return
                print_error("JNO-009","srv start without name","Example: srv start myblog or srv start --all"); return
            ok,msg=self.srv_manager.start(args[1])
            if not ok:
                if "in use" in msg.lower(): print_error("JNO-010",msg,"srv list shows used ports. Try srv stop <other> or different port")
                elif "Not found" in msg: print_error("JNO-011",msg,"srv list shows installed")
                elif "Already running" in msg: print_error("JNO-013",msg,"srv status <name>, srv restart <name>")
                else: print(msg)
            else: print(f"{C_GREEN}{msg}{C_RESET}")
        elif sub=="stop":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.stop_all(): print(f"{name}: {msg}")
                    return
                print_error("JNO-009","srv stop without name","Example: srv stop myblog or srv stop --all"); return
            ok,msg=self.srv_manager.stop(args[1]); print(msg)
        elif sub=="restart":
            if len(args)<2: print_error("JNO-009","srv restart without name","Example: srv restart myblog"); return
            ok,msg=self.srv_manager.restart(args[1]); print(msg)
        elif sub=="status":
            name=args[1] if len(args)>1 else None
            if name:
                srv=self.srv_manager.get(name)
                if not srv: print_error("JNO-011",f"Server {name} not found","srv list")
                else: print(json.dumps(srv.get_status(),indent=2))
            else: self.cmd_srv(["list"])
        elif sub=="logs":
            if len(args)<2: print_error("JNO-009","srv logs without name","Example: srv logs myblog"); return
            srv=self.srv_manager.get(args[1])
            if not srv: print_error("JNO-011",f"Server {args[1]} not found","srv list")
            else:
                for l in srv.logs[-50:]: print(l)
        elif sub in ("delete","remove","rm","del"):
            if len(args)<2: print_error("JNO-009","srv delete without name","Example: srv delete myblog"); return
            ok,msg=self.srv_manager.delete(args[1]); print(msg)
        elif sub=="new":
            print(f"{C_BOLD}=== Server Wizard ==={C_RESET}")
            name=input("Name (myblog): ").strip()
            if not name: print_error("JNO-016","Empty server name","Enter name: myblog, mysite"); return
            print("Templates: static, api-server, file-server, nodejs, wordpress, chat-server, mysql, redis")
            template=input("Template [static]: ").strip() or "static"
            port_str=input("Port [8080]: ").strip() or "8080"
            try: port=int(port_str)
            except: print_error("JNO-015",f"Port '{port_str}' not number","Enter number: 8080"); return
            root_default=f"/www/{name}"
            root=input(f"Root [{root_default}]: ").strip() or root_default
            ok,res=self.srv_manager.create(name,template=template,port=port,root=root)
            print(res if isinstance(res,str) else "Created")
            if ok and input("Start now? Y/n: ").lower()!="n":
                ok2,msg2=self.srv_manager.start(name); print(msg2)
        elif sub=="quick":
            if len(args)<2: print_error("JNO-009","srv quick without package","Example: srv quick nginx --port 8080"); return
            pkg=args[1]; port=None
            if "--port" in args:
                idx=args.index("--port")
                if idx+1 < len(args):
                    try: port=int(args[idx+1])
                    except: print_error("JNO-015",f"Port {args[idx+1]} not number",""); return
            print(f"Quick install {pkg}...")
            ok,msg=self.pkg_manager.install(pkg,port=port)
            print(msg)
            if ok:
                srv_name=pkg; ok2,msg2=self.srv_manager.start(srv_name); print(msg2)
        elif sub=="info":
            if len(args)<2: print_error("JNO-009","srv info without name","Example: srv info myblog"); return
            srv=self.srv_manager.get(args[1])
            print(json.dumps(srv.config,indent=2) if srv else "Not found")
        else: print_error("JNO-008",f"srv {sub} unknown","Available: list, create, start, stop, restart, status, logs, delete, new, quick, info")

    def cmd_curl(self,args):
        if not args or "--help" in args or "-h" in args:
            print(f"{C_BOLD}{C_GREEN}curl - Jino OS Full Implementation v3.0{C_RESET}")
            print("Usage: curl [options] <url>")
            print("  -X METHOD -H \"Header: val\" -d DATA -o FILE -i -v -L --connect-timeout SEC -u user:pass")
            print("Examples:")
            print("  curl http://localhost:8080/")
            print("  curl http://localhost:8080/api/status -i -v")
            print("  curl -X POST http://localhost:3000/api/jdb -d '{\"k\":\"v\"}' -H \"Content-Type: application/json\"")
            print("  curl file:///www/index.html")
            print("  curl /www/index.html -o /tmp/copy.html")
            return
        # Simplified curl parsing (full version from v2.2)
        # Reuse previous implementation - shortened for brevity, but functional
        url=None; method="GET"; headers={}; data=None; output_file=None; include_headers=False; verbose=False; timeout=5; auth=None
        i=0
        while i < len(args):
            a=args[i]
            if a in ("-X","--request") and i+1 < len(args): method=args[i+1].upper(); i+=2; continue
            elif a in ("-H","--header") and i+1 < len(args):
                hv=args[i+1]
                if ":" in hv: k,v=hv.split(":",1); headers[k.strip()]=v.strip()
                i+=2; continue
            elif a in ("-d","--data") and i+1 < len(args):
                data=args[i+1]
                if data.startswith("@"):
                    fcontent=self.fs.read(data[1:])
                    if fcontent: data=fcontent
                if method=="GET": method="POST"
                i+=2; continue
            elif a in ("-o","--output") and i+1 < len(args): output_file=args[i+1]; i+=2; continue
            elif a in ("-i","--include"): include_headers=True; i+=1; continue
            elif a in ("-v","--verbose"): verbose=True; i+=1; continue
            elif a in ("-L","--location"): i+=1; continue
            elif a=="--connect-timeout" and i+1 < len(args):
                try: timeout=int(args[i+1])
                except: pass
                i+=2; continue
            elif a in ("-u","--user") and i+1 < len(args): auth=args[i+1]; i+=2; continue
            elif not a.startswith("-") and not url: url=a; i+=1; continue
            else: i+=1
        if not url:
            print_error("JNO-019","URL not specified","Example: curl http://localhost:8080/")
            return
        if url.startswith("/"):
            if self.fs.is_file(url) or self.fs.is_dir(url): url="file://"+url
            else: url="http://localhost:80"+url if url.startswith("/api/") else "file://"+url
        if url.startswith("file://"):
            fpath=url[7:]; content=self.fs.read(fpath)
            if content is None:
                listing=self.fs.list_dir(fpath)
                if listing:
                    dirs,files=listing
                    content=f"Directory {fpath}:\n"
                    for d in dirs: content+=f"[DIR] {d}/\n"
                    for f in files: content+=f"[FILE] {f}\n"
                else:
                    print_error("JNO-001",f"File {fpath} not found","Check ls")
                    return
            if verbose: print(f"> GET {url}\n> Host: JinoFS\n<\n< HTTP/1.1 200 OK\n< Content-Length: {len(content)}\n")
            if include_headers: print(f"HTTP/1.1 200 OK\nContent-Length: {len(content)}\n")
            if output_file: self.fs.write(output_file, content); print(f"Saved to {output_file}")
            else: print(content)
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url="http://"+url
        try:
            parsed=urllib.parse.urlparse(url)
            req_data=data.encode() if isinstance(data,str) and data else None
            req=urllib.request.Request(url, data=req_data, method=method)
            for k,v in headers.items(): req.add_header(k,v)
            if auth:
                import base64 as b64; enc=b64.b64encode(auth.encode()).decode(); req.add_header("Authorization", f"Basic {enc}")
            if req_data and "Content-Type" not in headers:
                req.add_header("Content-Type","application/json" if (data and str(data).strip().startswith("{")) else "application/x-www-form-urlencoded")
            if verbose: print(f"* Trying {parsed.hostname}:{parsed.port or 80}...\n* Connected\n> {method} {parsed.path} HTTP/1.1\n> Host: {parsed.hostname}")
            ctx=None
            if parsed.scheme=="https":
                ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
            response=urllib.request.urlopen(req, timeout=timeout, context=ctx)
            body=response.read().decode(errors='replace')
            if verbose: print(f"< HTTP/1.1 {response.status} {response.reason}\n<")
            if include_headers:
                print(f"HTTP/1.1 {response.status} {response.reason}")
                for hk,hv in response.headers.items(): print(f"{hk}: {hv}")
                print("")
            if response.status>=400:
                print_error("JNO-020",f"HTTP {response.status} {response.reason} for {url}","Check path, srv logs")
            if output_file: self.fs.write(output_file, body); print(f"Saved {len(body)} bytes to {output_file}")
            else: print(body)
        except urllib.error.HTTPError as e:
            try: body=e.read().decode()
            except: body=str(e)
            print_error("JNO-020",f"HTTP {e.code} {e.reason} for {url}: {body[:200]}","Check URL, srv logs")
        except Exception as e:
            reason=str(e)
            if "Connection refused" in reason or "refused" in reason.lower():
                print_error("JNO-017",f"Connection refused to {url}: {reason}","Server not started. srv list, srv start <name>")
            elif "timed out" in reason.lower() or "timeout" in reason.lower():
                print_error("JNO-018",f"Timeout to {url}: {reason}","Try --connect-timeout 10")
            else:
                print_error("JNO-019",f"Error curl {url}: {reason}","Check curl --help")

    def cmd_wget(self,args):
        if not args:
            print_error("JNO-009","wget without URL","Example: wget http://localhost:8080/ -O /tmp/page.html")
            return
        url=None; out=None; i=0
        while i < len(args):
            if args[i]=="-O" and i+1<len(args): out=args[i+1]; i+=2; continue
            if not args[i].startswith("-") and not url: url=args[i]
            i+=1
        if not url: print_error("JNO-019","wget without URL",""); return
        cargs=[url]
        if out: cargs.extend(["-o", out])
        else: cargs.extend(["-o", f"/tmp/{os.path.basename(urllib.parse.urlparse(url).path) or 'index.html'}"])
        self.cmd_curl(cargs)

    def cmd_ls(self,args):
        path="."; show_all=False; filtered=[]
        for a in args:
            if a.startswith("-"):
                if "a" in a: show_all=True
            else: filtered.append(a)
        if filtered: path=filtered[0]
        abs_path=self.fs.norm(path)
        listing=self.fs.list_dir(abs_path)
        if listing is None:
            s=self.fs.stat(abs_path)
            if s and s["type"]=="file": print(os.path.basename(abs_path)); return
            print_error("JNO-002",f"Path {path} -> {abs_path} not found","Check ls /, pwd, find / -name")
            return
        dirs,files=listing
        if not show_all: dirs=[d for d in dirs if not d.startswith(".")]; files=[f for f in files if not f.startswith(".")]
        items=[f"{C_BLUE}{d}/{C_RESET}" for d in dirs] + files
        print("  ".join(items) if items else "(empty)")

    def cmd_pwd(self,args): print(self.fs.cwd)
    def cmd_cd(self,args):
        if not args: self.fs.cwd="/home/user"; return
        target=args[0]
        if target=="..":
            if self.fs.cwd!="/": self.fs.cwd=os.path.dirname(self.fs.cwd.rstrip("/")) or "/"
            return
        new_path=self.fs.norm(target)
        if new_path in self.fs.dirs: self.fs.cwd=new_path
        elif new_path in self.fs.files: print_error("JNO-004",f"cd {target} -> {new_path} is file, not dir","Use cat for files, cd only for dirs")
        else:
            if any(f.startswith(new_path+"/") for f in self.fs.files): self.fs.ensure_dir(new_path); self.fs.cwd=new_path
            else: print_error("JNO-002",f"cd {target} -> {new_path} not found","Check ls, mkdir")
    def cmd_cat(self,args):
        if not args: print_error("JNO-009","cat without args","Example: cat /readme.txt"); return
        for p in args:
            c=self.fs.read(p)
            if c is None:
                ap=self.fs.norm(p)
                if ap in self.fs.dirs: print_error("JNO-003",f"cat {p} -> {ap} is directory","Use ls {p} then cat {p}/index.html")
                else: print_error("JNO-001",f"cat {p} file not found","Check ls")
            else: print(c)
    def cmd_mkdir(self,args):
        if not args: print_error("JNO-009","mkdir without args","Example: mkdir /www/mysite"); return
        for p in args:
            ok,msg=self.fs.mkdir(p)
            if not ok: print_error("JNO-006",f"mkdir {p}: {msg}","Folder already exists, check ls")
            else: print(f"mkdir {msg}")
    def cmd_rm(self,args):
        if not args: print_error("JNO-009","rm without args","Example: rm /tmp/file.txt, rm -r /www/old"); return
        rec=False; targets=[]
        for a in args:
            if a in ("-r","-rf","-R"): rec=True
            else: targets.append(a)
        for p in targets:
            ap=self.fs.norm(p)
            if ap=="/": print_error("JNO-005","Attempt to delete root /","Cannot delete /. Use rm -r /path for specific folder"); continue
            if self.fs.is_file(ap): self.fs.rm(ap); print(f"Removed {ap}")
            elif self.fs.is_dir(ap) and rec:
                to_del=[f for f in self.fs.files if f==ap or f.startswith(ap+"/")]
                for f in to_del: del self.fs.files[f]
                print(f"Removed dir {ap} ({len(to_del)} files)")
            elif self.fs.is_dir(ap): print_error("JNO-007",f"rm {p} is dir without -r","Use rm -r {p} for recursive")
            else: print_error("JNO-001",f"rm {p} not found","Check ls")
    def cmd_echo(self,args,raw,redir_out,redir_append):
        import re
        m=re.search(r'echo\s+(.*)',raw,re.IGNORECASE); text=m.group(1) if m else " ".join(args)
        if redir_out: text=text.split(">")[0].strip().strip('"')
        if redir_out:
            path=self.fs.norm(redir_out)
            if path=="/": print_error("JNO-021","echo > / attempt to write to root","Write to file: echo hi > /tmp/hi.txt"); return
            if redir_append: existing=self.fs.read(path) or ""; self.fs.write(path,existing+text+"\n")
            else: self.fs.write(path,text+"\n")
            print(f"-> {path}")
        else: print(text)
    def cmd_ver(self,args): print(f"Jino OS {VERSION} Build {BUILD} Lang={CURRENT_LANG} Files {len(self.fs.files)} Servers {len(self.srv_manager.servers)}")
    def cmd_date(self,args): print(datetime.datetime.now())

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
            elif cmd=="ver" or cmd=="version": self.cmd_ver(args)
            elif cmd=="date": self.cmd_date(args)
            elif cmd in ("reboot","shutdown","exit","quit","poweroff"):
                if cmd=="reboot": print("Reboot..."); self.boot()
                else: print("Shutdown"); sys.exit(0)
            elif cmd=="help": self.cmd_help(args)
            elif cmd=="cmds": print("Commands: ls cd cat mkdir rm echo ver date help gui lang jpkg srv curl wget errors man deploy")
            elif cmd=="errors" or cmd=="error": self.cmd_errors(args)
            elif cmd=="jpkg": self.cmd_jpkg(args)
            elif cmd in ("srv","server","service","systemctl"): self.cmd_srv(args)
            elif cmd in ("deploy","serve","web","install-server"):
                # simple deploy
                path=args[0] if args and not args[0].startswith("--") else "."
                port=8000; name=None
                if "--port" in args:
                    idx=args.index("--port")
                    if idx+1<len(args):
                        try: port=int(args[idx+1])
                        except: pass
                if "--name" in args:
                    idx=args.index("--name")
                    if idx+1<len(args): name=args[idx+1]
                abs_path=self.fs.norm(path)
                if not name: name=os.path.basename(abs_path) or f"deploy{port}"
                if name=="/": name=f"site{port}"
                ok,res=self.srv_manager.create(name,template="static",port=port,root=abs_path if self.fs.is_dir(abs_path) else os.path.dirname(abs_path))
                if not ok: print_error("JNO-006",res,"")
                else:
                    ok2,msg2=self.srv_manager.start(name); print(f"{C_GREEN}{msg2}{C_RESET}" if ok2 else msg2)
            elif cmd=="curl": self.cmd_curl(args)
            elif cmd=="wget": self.cmd_wget(args)
            elif cmd in ("gui","startx","jindowm"):
                self.cmd_gui(args)
            elif cmd in ("exit-gui","console"):
                print("Already in console (GUI closed)")
            elif cmd=="lang":
                # lang switch
                if not args:
                    print(f"Current: {CURRENT_LANG}. Available: en, ru. Usage: lang en")
                else:
                    if args[0].lower() in ("en","ru","english","russian","1","2"):
                        set_language(args[0])
                        # reload lang data for help? t() will use new lang
                        print(f"Language switched to {CURRENT_LANG}")
                        # update jdb
                        self.jdb["lang"]=CURRENT_LANG
                        self.env["LANG"]=CURRENT_LANG
                    else:
                        print_error("JNO-009",f"Unknown lang {args[0]}","Available: en, ru")
            elif cmd=="man":
                if not args: print("man <cmd>. Example: man curl, man gui")
                else:
                    if args[0]=="gui": print("GUI: gui launches graphical desktop, console remains. gui --browser opens browser hybrid. exit-gui to return. Terminal app in GUI still console.")
                    elif args[0]=="curl": self.cmd_curl(["--help"])
                    else: print(f"man {args[0]}: no page, try {args[0]} --help")
            else:
                print_error("JNO-008",f"Command {cmd} not found","Type cmds for list, help for help")
        except Exception as e:
            import traceback
            print(f"{C_RED}[Kernel Panic] {e}{C_RESET}"); traceback.print_exc()

    def run(self):
        # Language selection at very start if config not exists
        if not load_config_lang():
            self.select_language()
        else:
            set_language(load_config_lang())
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
