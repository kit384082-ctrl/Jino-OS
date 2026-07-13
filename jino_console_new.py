#!/usr/bin/env python3
"""
Jino OS v2.1 CONSOLE EDITION - No GUI + Easy Server Installer + 100+ Commands
Merged: v1.0 commands + v2.0 server manager
"""
import os, sys, time, json, shlex, base64, re, random, math
import shutil, datetime, subprocess, socket, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION="2.1 Console Server Edition"
BUILD="2026-07-13 SERVER+100CMDS"
C_RESET="\033[0m"; C_GREEN="\033[92m"; C_YELLOW="\033[93m"; C_CYAN="\033[96m"; C_RED="\033[91m"; C_MAGENTA="\033[95m"; C_BLUE="\033[94m"; C_BOLD="\033[1m"; C_DIM="\033[2m"
REPO_PATH="/home/user/JinoOS/packages/repo.json"
RUNTIME_ROOT="/tmp/jino_runtime"
SERVERS_DB="/tmp/jino_servers_db.json"

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
        mkfile("/readme.txt","Jino OS v2.1 Console Server Edition\nNo GUI, 100+ commands, Easy Server Installer\n\nType 'help', 'cmds', 'jpkg list', 'srv list'\n")
        mkfile("/autoexec.jino","echo Jino OS 2.1 Booted\nver\nsrv list\n")
        mkfile("/www/index.html","<html><head><title>JinoServer</title></head><body><h1>JinoServer v2.1 Works!</h1><p>Default on :80</p><p><a href='/api/status'>/api/status</a></p></body></html>")
        mkfile("/etc/hosts","127.0.0.1 localhost\n127.0.0.1 jino.local\n")
        mkfile("/etc/config.sys","memory=32MB\nfs=JinoFS v2\nshell=JinoSH 2.1\nmode=console_server\n")
        mkfile("/apps/hello.japp",'print("Hello Jino!")\n')
        mkfile("/home/user/notes.txt","Notes\n"); mkfile("/system/motd.txt","Welcome to Jino OS Console Server Edition!\n")
        mkfile("/home/user/docs/todo.txt","- [x] Remove GUI\n- [x] Server installer\n- [ ] More servers\n")
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
        self.env={"USER":"jino","HOME":"/home/user","PATH":"/bin","SHELL":"/bin/jinosh","OS":"Jino OS 2.1","TERM":"jino-256color","PWD":self.fs.cwd,"HOST":"jino-pc","EDITOR":"nano"}
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

          CONSOLE SERVER EDITION v2.1 - 100+ CMDS + EASY INSTALL
"""+C_RESET)
        print(f"{C_CYAN}Jino OS {VERSION} | {BUILD} | 32MB | i386{C_RESET}")
        print(f"{C_GREEN}[OK] JinoFS v2 {len(self.fs.files)} files{C_RESET}")
        print(f"{C_GREEN}[OK] Server Manager {len(self.srv_manager.servers)} servers{C_RESET}")
        print(f"{C_GREEN}[OK] Repo {len(self.pkg_manager.repo.get('packages',[]))} packages{C_RESET}")
        print(f"{C_GREEN}[OK] Runtime {RUNTIME_ROOT}{C_RESET}")
        print(f"Type {C_BOLD}help{C_RESET}, {C_BOLD}jpkg list{C_RESET}, {C_BOLD}srv list{C_RESET}, {C_BOLD}srv new{C_RESET}")
        print()
    def parse(self,line):
        stripped=line.strip()
        if not stripped: return [],None,False
        first=stripped.split()[0]
        if first in self.aliases: line=self.aliases[first]+" "+" ".join(stripped.split()[1:])
        redirect_out=None; redirect_append=False
        if ">" in line:
            m=re.search(r'\s*(>>|>)\s*([^\s]+)\s*$', line)
            if m: op=m.group(1); target=m.group(2); redirect_out=target; redirect_append=(op==">>"); line=line[:m.start()].strip()
        try: parts=shlex.split(line)
        except: parts=line.split()
        return parts,redirect_out,redirect_append

    # HELP
    def cmd_help(self,args):
        print(f"""{C_BOLD}{C_GREEN}Jino OS v2.1 - Help{C_RESET}
{C_YELLOW}100+ команд + удобная установка серверов{C_RESET}

{Srv Installer:}
  jpkg list | jpkg search <term> | jpkg install <pkg> [--port P] [--name N] [--root /path]
  jpkg info <pkg> | jpkg uninstall <name>
  srv list | srv start <name> | srv stop <name> | srv restart <name> | srv status [name] | srv logs <name> | srv delete <name>
  srv new (wizard) | srv quick <pkg> (install+start) | srv create <name> --template static --port 8080 --root /www
  deploy <path> --port 8000 --name mysite | serve | web

{Srv Examples:}
  jpkg install nginx --port 8080
  srv start nginx
  curl http://localhost:8080/api/status

  jpkg install api-server --port 3000
  srv quick api-server

  srv new -> answer questions

  deploy . --port 9000 --name quicksite

{Base Commands:}
  FS: ls ll la pwd cd cat bat more less touch mkdir rmdir rm cp mv find tree du df stat
  TEXT: echo write edit head tail wc grep sort uniq cut hexdump base64 strings diff rev
  SYS: ver uname whoami hostname date time cal clear history env mem ps top uptime sleep reboot exit
  FUN: calc cowsay fortune banner figlet matrix snake tetris man tutorial cmds
""")
    def cmd_cmds(self,args):
        print(f"{C_BOLD}All Commands:{C_RESET}")
        print("SERVER: jpkg list/search/install/uninstall/info, srv list/create/start/stop/restart/status/logs/delete/new/quick/info, deploy/serve/web/install-server")
        print("FS: ls dir ll la pwd cd cat type bat more less touch mkdir md rmdir rd rm del cp copy mv move ren find tree du df stat chmod")
        print("TEXT: echo printf write edit nano head tail wc grep egrep sort uniq cut tr hexdump xxd base64 strings diff cmp rev tee truncate")
        print("SYS: ver version uname whoami hostname sysinfo date time cal clear cls history env set export unset alias mem free meminfo cpuinfo ps top uptime sleep reboot shutdown exit quit")
        print("NET: ping ifconfig curl wget server jdb (old) + jpkg srv (new)")
        print("FUN: calc bc cowsay fortune banner figlet matrix snake tetris hangman motd man tutorial")

    # JPKG
    def cmd_jpkg(self,args):
        if not args: print("Usage: jpkg list|search|install|uninstall|info"); return
        sub=args[0]
        if sub=="list":
            filt=args[1] if len(args)>1 else None
            pkgs=self.pkg_manager.list_packages(filt)
            print(f"{C_BOLD}Repo - {len(pkgs)} pkgs{C_RESET}")
            print(f"{'NAME':<20} {'VER':<10} {'PORT':<6} {'TYPE':<10} DESC")
            print("-"*90)
            for p in pkgs: print(f"{C_GREEN}{p['name']:<20}{C_RESET} {p.get('version',''):<10} {str(p.get('port','-')):<6} {p.get('type',''):<10} {p.get('description','')[:50]}")
            print(f"\nInstall: jpkg install <name> [--port PORT] [--name NAME]")
        elif sub=="search":
            term=args[1] if len(args)>1 else ""
            if not term: print("Usage: jpkg search <term>"); return
            res=self.pkg_manager.search(term)
            print(f"Search '{term}' {len(res)} found:")
            for p in res: print(f" {p['name']:<20} {p.get('description','')}")
        elif sub=="install":
            if len(args)<2: print("Usage: jpkg install <pkg> [--port PORT] [--name NAME] [--root /path]"); return
            pkg_name=args[1]; port=None; custom_name=None; root=None; i=2
            while i < len(args):
                if args[i]=="--port" and i+1<len(args): port=int(args[i+1]); i+=2; continue
                if args[i]=="--name" and i+1<len(args): custom_name=args[i+1]; i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            print(f"{C_YELLOW}Installing {pkg_name}...{C_RESET}")
            ok,msg=self.pkg_manager.install(pkg_name,port=port,custom_name=custom_name,root=root)
            print(f"{C_GREEN if ok else C_RED}{msg}{C_RESET}")
            if ok:
                srv_name=custom_name or pkg_name
                print(f"Now: srv start {srv_name}")
        elif sub in ("uninstall","remove"):
            if len(args)<2: print("Usage: jpkg uninstall <name>"); return
            ok,msg=self.srv_manager.delete(args[1]); print(msg)
        elif sub=="info":
            if len(args)<2: print("Usage: jpkg info <pkg>"); return
            pkg=self.pkg_manager.get_pkg(args[1])
            print(json.dumps(pkg,indent=2) if pkg else "Not found")
        else: print(f"Unknown {sub}")

    # SRV
    def cmd_srv(self,args):
        if not args: print("Usage: srv list|create|start|stop|restart|status|logs|delete|new|quick"); return
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
            if len(args)<2: print("Usage: srv create <name> --template static --port 8080 --root /www"); return
            name=args[1]; template="static"; port=8080; root=f"/www/{name}"; i=2
            while i < len(args):
                if args[i]=="--template" and i+1<len(args): template=args[i+1]; i+=2; continue
                if args[i]=="--port" and i+1<len(args): port=int(args[i+1]); i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            ok,res=self.srv_manager.create(name,template=template,port=port,root=root)
            print(f"{C_GREEN if ok else C_RED}{res}{C_RESET}")
        elif sub=="start":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.start_all(): print(f"{name}: {msg}")
                    return
                print("Usage: srv start <name> or --all"); return
            ok,msg=self.srv_manager.start(args[1]); print(f"{C_GREEN if ok else C_RED}{msg}{C_RESET}")
        elif sub=="stop":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.stop_all(): print(f"{name}: {msg}")
                    return
                print("Usage: srv stop <name> or --all"); return
            ok,msg=self.srv_manager.stop(args[1]); print(msg)
        elif sub=="restart":
            if len(args)<2: print("Usage: srv restart <name>"); return
            ok,msg=self.srv_manager.restart(args[1]); print(msg)
        elif sub=="status":
            name=args[1] if len(args)>1 else None
            if name:
                srv=self.srv_manager.get(name)
                if not srv: print("Not found")
                else: print(json.dumps(srv.get_status(),indent=2))
            else: self.cmd_srv(["list"])
        elif sub=="logs":
            if len(args)<2: print("Usage: srv logs <name>"); return
            srv=self.srv_manager.get(args[1])
            if not srv: print("Not found")
            else:
                print(f"Logs {srv.name}:")
                for l in srv.logs[-50:]: print(l)
        elif sub in ("delete","remove","rm","del"):
            if len(args)<2: print("Usage: srv delete <name>"); return
            ok,msg=self.srv_manager.delete(args[1]); print(msg)
        elif sub=="new":
            print(f"{C_BOLD}=== Server Wizard ==={C_RESET}")
            name=input("Name (myblog): ").strip()
            if not name: print("Cancelled"); return
            print("Templates: static, api-server, file-server, python-api, nodejs, wordpress, chat-server, mysql, redis")
            template=input("Template [static]: ").strip() or "static"
            port_str=input("Port [8080]: ").strip() or "8080"
            try: port=int(port_str)
            except: port=8080
            root_default=f"/www/{name}" if template in ("static","file-server","wordpress") else f"/apps/{name}"
            root=input(f"Root [{root_default}]: ").strip() or root_default
            ok,res=self.srv_manager.create(name,template=template,port=port,root=root)
            print(res if isinstance(res,str) else "Created")
            if ok and input("Start now? Y/n: ").lower()!="n":
                ok2,msg2=self.srv_manager.start(name); print(msg2)
        elif sub=="quick":
            if len(args)<2: print("Usage: srv quick <pkg> [--port PORT]"); return
            pkg=args[1]; port=None
            if "--port" in args:
                idx=args.index("--port")
                if idx+1<len(args): port=int(args[idx+1])
            print(f"Quick install {pkg}...")
            ok,msg=self.pkg_manager.install(pkg,port=port)
            print(msg)
            if ok:
                srv_name=pkg; ok2,msg2=self.srv_manager.start(srv_name); print(msg2)
        elif sub=="info":
            if len(args)<2: print("Usage: srv info <name>"); return
            srv=self.srv_manager.get(args[1])
            print(json.dumps(srv.config,indent=2) if srv else "Not found")
        else: print(f"Unknown {sub}")

    def cmd_deploy(self,args):
        path="."; port=8000; name=None; i=0
        while i < len(args):
            if args[i]=="--port" and i+1<len(args): port=int(args[i+1]); i+=2; continue
            if args[i]=="--name" and i+1<len(args): name=args[i+1]; i+=2; continue
            if not args[i].startswith("--"): path=args[i]
            i+=1
        abs_path=self.fs.norm(path)
        if not name:
            name=os.path.basename(abs_path) or f"deploy{port}"
            if name=="/": name=f"site{port}"
        root=abs_path
        if self.fs.is_file(root): root=os.path.dirname(root)
        print(f"Deploying {abs_path} as '{name}' :{port}...")
        ok,res=self.srv_manager.create(name,template="static",port=port,root=root)
        if not ok: print(f"{C_RED}{res}{C_RESET}"); return
        ok2,msg2=self.srv_manager.start(name); print(f"{C_GREEN}{msg2}{C_RESET}")

    # FS/TEXT/SYS COMMANDS (condensed but many)
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
            if s and s["type"]=="file": print(os.path.basename(abs_path)); return
            print(f"{C_RED}ls: {path}: No such{C_RESET}"); return
        dirs,files=listing
        if not show_all: dirs=[d for d in dirs if not d.startswith(".")]; files=[f for f in files if not f.startswith(".")]
        if long:
            for d in dirs: print(f"{C_BLUE}{d}/{C_RESET}")
            for f in files: st=self.fs.stat(abs_path.rstrip("/")+ "/"+f); print(f"{f} {st['size'] if st else 0}b")
        else:
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
        elif new_path in self.fs.files: print("Not dir")
        else:
            if any(f.startswith(new_path+"/") for f in self.fs.files): self.fs.ensure_dir(new_path); self.fs.cwd=new_path
            else: print("No such dir")
    def cmd_cat(self,args):
        if not args: print("Usage: cat <file>"); return
        for p in args:
            c=self.fs.read(p)
            print(c if c else f"cat: {p}: no file")
    def cmd_bat(self,args):
        if not args: print("Usage: bat <file>"); return
        c=self.fs.read(args[0])
        if not c: print("No file"); return
        for i,line in enumerate(c.splitlines(),1): print(f"{C_DIM}{i:4} |{C_RESET} {line}")
    def cmd_mkdir(self,args):
        for p in args: ok,msg=self.fs.mkdir(p); print(msg if ok else f"Err {msg}")
    def cmd_rm(self,args):
        rec=False; targets=[]
        for a in args:
            if a in ("-r","-rf","-R"): rec=True
            else: targets.append(a)
        for p in targets:
            ap=self.fs.norm(p)
            if self.fs.is_file(ap): self.fs.rm(ap); print(f"Removed {ap}")
            elif self.fs.is_dir(ap) and rec:
                to_del=[f for f in self.fs.files if f==ap or f.startswith(ap+"/")]
                for f in to_del: del self.fs.files[f]
                to_del_d=[d for d in self.fs.dirs if d==ap or d.startswith(ap+"/")]
                for d in to_del_d:
                    if d in self.fs.dirs: self.fs.dirs.remove(d)
                self.fs.dirs.add("/"); print(f"Removed dir {ap}")
            else: print(f"rm: {p}: no")
    def cmd_cp(self,args):
        if len(args)<2: print("Usage: cp src dst"); return
        ok,msg=self.fs.cp(args[0],args[1]); print(msg if ok else f"Err {msg}")
    def cmd_mv(self,args):
        if len(args)<2: print("Usage: mv src dst"); return
        ok,msg=self.fs.mv(args[0],args[1]); print(msg if ok else f"Err {msg}")
    def cmd_find(self,args):
        path="/"; name_pat=None; i=0
        while i < len(args):
            if args[i]=="-name" and i+1<len(args): name_pat=args[i+1]; i+=2; continue
            if not args[i].startswith("-"): path=args[i]
            i+=1
        path=self.fs.norm(path); res=[]
        for fpath in self.fs.files:
            if not fpath.startswith(path): continue
            if name_pat:
                pat=name_pat.replace(".","\\.").replace("*",".*")
                if not re.search(pat, os.path.basename(fpath)): continue
            res.append(fpath)
        for r in res: print(r)
        print(f"Found {len(res)}")
    def cmd_tree(self,args):
        path=self.fs.norm(args[0] if args else self.fs.cwd)
        def recurse(cur,pref=""):
            dirs,files=self.fs.list_dir(cur) or ([],[])
            items=[(d,True) for d in dirs]+[(f,False) for f in files]
            for idx,(name,is_dir) in enumerate(items):
                last=idx==len(items)-1; conn="└── " if last else "├── "
                print(pref+conn+(f"{C_BLUE}{name}/{C_RESET}" if is_dir else name))
                if is_dir:
                    recurse(cur.rstrip("/")+ "/"+name, pref+("    " if last else "│   "))
        print(path); recurse(path)
    def cmd_du(self,args):
        path=self.fs.norm(args[0] if args else self.fs.cwd); total=sum(len(d["content"]) for f,d in self.fs.files.items() if f.startswith(path))
        print(f"{total} bytes {path}")
    def cmd_df(self,args):
        total=32*1024*1024; used=sum(len(d["content"]) for d in self.fs.files.values()); print(f"JinoFS 32M Used {used//1024}K Free {(total-used)//1024}K Files {len(self.fs.files)}")
    def cmd_stat(self,args):
        if not args: print("Usage: stat <file>"); return
        s=self.fs.stat(args[0]); print(f"{s}" if s else "No such")
    def cmd_head(self,args):
        n=10; files=[]; i=0
        while i < len(args):
            if args[i]=="-n" and i+1<len(args): n=int(args[i+1]); i+=2; continue
            files.append(args[i]); i+=1
        for p in files:
            c=self.fs.read(p)
            if c: print("\n".join(c.splitlines()[:n]))
    def cmd_tail(self,args):
        n=10; files=[]; i=0
        while i < len(args):
            if args[i]=="-n" and i+1<len(args): n=int(args[i+1]); i+=2; continue
            files.append(args[i]); i+=1
        for p in files:
            c=self.fs.read(p)
            if c: print("\n".join(c.splitlines()[-n:]))
    def cmd_wc(self,args):
        for p in args:
            c=self.fs.read(p)
            if c: print(f"{len(c.splitlines())} {len(c.split())} {len(c)} {p}")
    def cmd_grep(self,args):
        if not args: print("Usage: grep pattern [file]"); return
        pat=args[0]; files=args[1:] or [self.fs.cwd]
        regex=re.compile(pat, re.IGNORECASE)
        for farg in files:
            ap=self.fs.norm(farg)
            if ap in self.fs.dirs:
                for fpath,fdata in self.fs.files.items():
                    if fpath.startswith(ap):
                        for line in fdata["content"].splitlines():
                            if regex.search(line): print(f"{fpath}:{line}")
            else:
                c=self.fs.read(ap)
                if c:
                    for line in c.splitlines():
                        if regex.search(line): print(line)
    def cmd_hexdump(self,args):
        if not args: print("Usage: hexdump <file>"); return
        c=self.fs.read(args[0])
        if not c: return
        data=c.encode()
        for off in range(0,len(data),16):
            chunk=data[off:off+16]; hx=" ".join(f"{b:02x}" for b in chunk); asc="".join(chr(b) if 32<=b<127 else "." for b in chunk)
            print(f"{off:08x} {hx:<48} |{asc}|")
    def cmd_base64(self,args):
        if not args: print("Usage: base64 [-d] <file|text>"); return
        decode=False; target=None
        for a in args:
            if a=="-d": decode=True
            else: target=a
        c=self.fs.read(target) if target else None
        if c is None: c=target
        if decode:
            try: print(base64.b64decode(c).decode())
            except Exception as e: print(f"err {e}")
        else: print(base64.b64encode(c.encode()).decode())
    def cmd_echo(self,args,raw,redir_out,redir_append):
        m=re.search(r'echo\s+(.*)',raw,re.IGNORECASE); text=m.group(1) if m else " ".join(args)
        if redir_out: text=text.split(">")[0].strip().strip('"')
        if redir_out:
            path=self.fs.norm(redir_out)
            if redir_append: existing=self.fs.read(path) or ""; self.fs.write(path,existing+text+"\n")
            else: self.fs.write(path,text+"\n")
            print(f"-> {path}")
        else: print(text)
    def cmd_write(self,args):
        if not args: print("Usage: write <file>"); return
        path=args[0]; print(f"Write to {path}, '.' to save")
        lines=[]
        try:
            while True:
                line=input(f"{len(lines)+1}> ")
                if line in (".",":wq"): break
                if line==":q!": return
                lines.append(line)
        except EOFError: pass
        self.fs.write(path,"\n".join(lines)); print("Saved")
    def cmd_clear(self,args): os.system("clear||cls"); print("\033[2J\033[H",end="")
    def cmd_history(self,args):
        for i,h in enumerate(self.history[-100:],1): print(f"{i:4} {h}")
    def cmd_mem(self,args): print(f"32M total, files {len(self.fs.files)}")
    def cmd_ps(self,args):
        print("PID NAME STATUS")
        for s in self.srv_manager.list_servers():
            print(f"{s.port} {s.name} {s.status} :{s.port}")
    def cmd_jdb(self,args):
        if not args: print("Usage: jdb set/get/list"); return
        if args[0]=="set" and len(args)>=3: self.jdb[args[1]]=" ".join(args[2:]); print(f"OK {args[1]}")
        elif args[0]=="get" and len(args)>=2: print(self.jdb.get(args[1],"(nil)"))
        elif args[0]=="list":
            for k,v in self.jdb.items(): print(f"{k}={v}")
        elif args[0]=="del" and len(args)>=2: self.jdb.pop(args[1],None); print("Del")
    def cmd_calc(self,args):
        if not args: print("Usage: calc expr"); return
        expr=" ".join(args).replace("^","**")
        try: print(eval(expr,{"__builtins__":{}},{"sin":math.sin,"cos":math.cos,"sqrt":math.sqrt,"pi":math.pi}))
        except Exception as e: print(e)
    def cmd_cowsay(self,args):
        t=" ".join(args) or "Jino"
        print(f"< {t} >\n \\   ^__^\n  \\  (oo)\\_______\n     (__)\\       )\\/\\\n         ||----w |\n         ||     ||")
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
        if cmd in ("ls","dir","ll","la","l"): self.cmd_ls(args)
        elif cmd=="pwd": self.cmd_pwd(args)
        elif cmd=="cd": self.cmd_cd(args)
        elif cmd in ("cat","type"): self.cmd_cat(args)
        elif cmd=="bat": self.cmd_bat(args)
        elif cmd in ("mkdir","md"): self.fs.mkdir(args[0]) if args else print("Usage mkdir <dir>"); print("OK" if args else "")
        elif cmd in ("rm","del","rmdir","rd"):
            rec="-r" in args or "-rf" in args
            targets=[a for a in args if not a.startswith("-")]
            for t in targets:
                ap=self.fs.norm(t)
                if self.fs.is_file(ap): self.fs.rm(ap); print(f"Removed {ap}")
                elif rec and self.fs.is_dir(ap):
                    to_del=[f for f in self.fs.files if f==ap or f.startswith(ap+"/")]
                    for f in to_del: del self.fs.files[f]
                    print(f"Removed dir {ap}")
        elif cmd in ("cp","copy"): self.cmd_cp(args)
        elif cmd in ("mv","move","ren"): self.cmd_mv(args)
        elif cmd=="find": self.cmd_find(args)
        elif cmd=="tree": self.cmd_tree(args)
        elif cmd=="du": self.cmd_du(args)
        elif cmd=="df": self.cmd_df(args)
        elif cmd=="stat": self.cmd_stat(args)
        elif cmd=="echo": self.cmd_echo(args,raw,redir_out,redir_append); return
        elif cmd in ("write","edit","nano"): self.cmd_write(args)
        elif cmd=="head": self.cmd_head(args)
        elif cmd=="tail": self.cmd_tail(args)
        elif cmd=="wc": self.cmd_wc(args)
        elif cmd=="grep": self.cmd_grep(args)
        elif cmd=="hexdump": self.cmd_hexdump(args)
        elif cmd=="base64": self.cmd_base64(args)
        elif cmd in ("clear","cls"): self.cmd_clear(args)
        elif cmd=="history": self.cmd_history(args)
        elif cmd in ("mem","free"): self.cmd_mem(args)
        elif cmd=="ps": self.cmd_ps(args)
        elif cmd=="jdb": self.cmd_jdb(args)
        elif cmd in ("calc","bc"): self.cmd_calc(args)
        elif cmd=="cowsay": self.cmd_cowsay(args)
        elif cmd in ("ver","version"): self.cmd_ver(args)
        elif cmd=="date": self.cmd_date(args)
        elif cmd in ("reboot","shutdown","exit","quit","poweroff"):
            if cmd=="reboot": self.cmd_reboot(args)
            else: self.cmd_shutdown(args)
        elif cmd=="help": self.cmd_help(args)
        elif cmd=="cmds": self.cmd_cmds(args)
        elif cmd=="jpkg": self.cmd_jpkg(args)
        elif cmd in ("srv","server","service","systemctl"): self.cmd_srv(args)
        elif cmd in ("deploy","serve","web","install-server"): self.cmd_deploy(args)
        else: print(f"Unknown {cmd}. Try help, jpkg list, srv list")

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
