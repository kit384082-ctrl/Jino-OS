#!/usr/bin/env python3
"""
Jino OS v2.0 CONSOLE EDITION - No GUI + Easy Server Installer
80+ base commands + jpkg + srv manager + real HTTP servers
Build: 2026-07-13 SERVER EDITION
"""
import os, sys, time, json, shlex, base64, re, random, math, hashlib
import shutil, textwrap, datetime, platform, subprocess, socket, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "2.0 Console Server Edition"
BUILD = "2026-07-13 SERVER"

C_RESET="\033[0m"; C_GREEN="\033[92m"; C_YELLOW="\033[93m"; C_CYAN="\033[96m"; C_RED="\033[91m"; C_MAGENTA="\033[95m"; C_BLUE="\033[94m"; C_BOLD="\033[1m"; C_DIM="\033[2m"

REPO_PATH = "/home/user/JinoOS/packages/repo.json"
RUNTIME_ROOT = "/tmp/jino_runtime"
SERVERS_DB = "/tmp/jino_servers_db.json"

# Helpers for repo
def load_repo():
    try:
        with open(REPO_PATH,'r') as f:
            return json.load(f)
    except:
        return {"packages":[]}

# JinoFS (simplified from previous but enriched)
class JinoFS:
    def __init__(self):
        self.files = {}
        self.dirs = set(["/"])
        self.cwd = "/"
        self._init_defaults()
        self.load_persist()
    def _init_defaults(self):
        now=time.time()
        def mkfile(p,c,perm="rw-r--r--"):
            self.files[self.norm(p)]={"content":c,"mtime":now,"perms":perm}
            self.ensure_dir(os.path.dirname(self.norm(p)))
        def mkdir(p): self.ensure_dir(self.norm(p))
        mkdir("/bin"); mkdir("/etc"); mkdir("/etc/servers"); mkdir("/etc/jpkg"); mkdir("/home"); mkdir("/home/user"); mkdir("/www"); mkdir("/var"); mkdir("/tmp"); mkdir("/apps"); mkdir("/db"); mkdir("/usr"); mkdir("/system"); mkdir("/servers"); mkdir("/templates")
        mkfile("/readme.txt","Jino OS v2.0 Console Server Edition\nNo GUI, Pure Console, 80+ commands + Easy Server Installer\n\nType 'help' or 'cmds' or 'jpkg list' or 'srv list'\n")
        mkfile("/autoexec.jino","echo Jino OS 2.0 Booted\nmem\nver\nsrv list\n")
        mkfile("/www/index.html","<html><head><title>JinoServer</title></head><body><h1>JinoServer v2.0 Works!</h1><p>Default server on :80</p><p><a href=\"/api/status\">/api/status</a></p></body></html>")
        mkfile("/etc/hosts","127.0.0.1 localhost\n127.0.0.1 jino.local\n")
        mkfile("/etc/config.sys","memory=32MB\nfs=JinoFS v2\nshell=JinoSH 2.0\nmode=console_server\nnetwork=enabled\n")
        mkfile("/apps/hello.japp",'print("Hello Jino!")\n')
        mkfile("/home/user/notes.txt","My notes\n")
        mkfile("/system/motd.txt","Welcome to Jino OS Console Server Edition! Install servers with jpkg.\n")
        mkfile("/templates/static/index.html","<html><body><h1>{{SERVER_NAME}} - Static</h1><p>Port {{PORT}} Root {{ROOT}}</p></body></html>")
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
        p=self.norm(path)
        return self.files[p]["content"] if p in self.files else None
    def stat(self,path):
        p=self.norm(path)
        if p in self.files: d=self.files[p]; return {"type":"file","size":len(d["content"]),"mtime":d["mtime"],"perms":d["perms"],"path":p}
        if p in self.dirs: return {"type":"dir","size":4096,"mtime":time.time(),"perms":"rwxr-xr-x","path":p}
        return None
    def write(self,path,content,perms=None):
        p=self.norm(path); dirn=os.path.dirname(p); self.ensure_dir(dirn); now=time.time()
        old_perms=self.files.get(p,{}).get("perms","rw-r--r--")
        self.files[p]={"content":content,"mtime":now,"perms":perms or old_perms}
        self.save_persist()
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

# Server Runtime
class ServerInstance:
    def __init__(self, config, fs_ref, jdb_ref):
        self.name=config.get("name")
        self.type=config.get("type","static")
        self.port=config.get("port",8080)
        self.root=config.get("root","/www")
        self.config=config
        self.fs=fs_ref
        self.jdb=jdb_ref
        self.status="stopped"
        self.thread=None
        self.httpd=None
        self.logs=[]
        self.start_time=None
        self.real_root=os.path.join(RUNTIME_ROOT, self.name)

    def log(self,msg):
        ts=time.strftime("%H:%M:%S")
        entry=f"[{ts}] {msg}"
        self.logs.append(entry)
        if len(self.logs)>200: self.logs=self.logs[-200:]
        print(f"{C_DIM}[{self.name}] {entry}{C_RESET}")

    def ensure_real_fs(self):
        os.makedirs(self.real_root, exist_ok=True)
        # copy files from virtual root to real
        # if root is /www, copy all files under /www to real_root
        root_norm=self.fs.norm(self.root)
        for fpath, fdata in self.fs.files.items():
            if fpath.startswith(root_norm):
                rel=fpath[len(root_norm):].lstrip("/")
                if not rel: rel="index.html"
                # if root_norm == file itself
                if fpath==root_norm and self.fs.stat(fpath)["type"]=="file":
                    rel=os.path.basename(fpath)
                real_path=os.path.join(self.real_root, rel)
                os.makedirs(os.path.dirname(real_path), exist_ok=True)
                try:
                    with open(real_path,'w', encoding='utf-8', errors='ignore') as out:
                        content=fdata["content"]
                        # template replace
                        content=content.replace("{{SERVER_NAME}}", self.name).replace("{{PORT}}", str(self.port)).replace("{{ROOT}}", self.root).replace("{{ID}}", self.name).replace("{{SERVER_TYPE}}", self.type)
                        out.write(content)
                except: pass
        # ensure index.html exists
        idx=os.path.join(self.real_root,"index.html")
        if not os.path.exists(idx):
            with open(idx,'w') as f:
                f.write(f"<html><body><h1>{self.name} - {self.type}</h1><p>Port {self.port} Root {self.root}</p><p><a href='/api/status'>/api/status</a> | <a href='/api/jdb'>/api/jdb</a></p></body></html>")

    def make_handler(self):
        fs_ref=self.fs
        jdb_ref=self.jdb
        server_name=self.name
        server_config=self.config
        real_root=self.real_root
        logs_ref=self.logs

        class JinoHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                msg=f"{self.client_address[0]} - {format%args}"
                logs_ref.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                if len(logs_ref)>200: logs_ref.pop(0)

            def do_GET(self):
                # API endpoints
                if self.path.startswith("/api/"):
                    self.handle_api()
                    return
                # static file serving
                path=self.path.split("?")[0]
                if path=="/": path="/index.html"
                # security
                path=path.lstrip("/")
                # prevent ..
                path=os.path.normpath(path).replace("..","")
                full=os.path.join(real_root, path)
                # if directory, look for index
                if os.path.isdir(full):
                    full=os.path.join(full,"index.html")
                if os.path.exists(full) and os.path.isfile(full):
                    try:
                        with open(full,'rb') as f:
                            data=f.read()
                        self.send_response(200)
                        # mime
                        if full.endswith(".html"): self.send_header("Content-Type","text/html")
                        elif full.endswith(".json"): self.send_header("Content-Type","application/json")
                        elif full.endswith(".js"): self.send_header("Content-Type","application/javascript")
                        elif full.endswith(".css"): self.send_header("Content-Type","text/css")
                        else: self.send_header("Content-Type","text/html")
                        self.send_header("Access-Control-Allow-Origin","*")
                        self.end_headers()
                        self.wfile.write(data)
                    except Exception as e:
                        self.send_error(500, str(e))
                else:
                    # if not found, try JinoFS virtual
                    vpath=server_config.get("root","/www").rstrip("/")+ "/"+path
                    vcontent=fs_ref.read(vpath)
                    if vcontent:
                        self.send_response(200)
                        self.send_header("Content-Type","text/html")
                        self.end_headers()
                        self.wfile.write(vcontent.encode())
                    else:
                        self.send_response(404)
                        self.send_header("Content-Type","text/html")
                        self.end_headers()
                        html=f"<h1>404 - {self.path} not found</h1><p>Server {server_name} root {real_root}</p><p>Available: <a href='/'>/</a> <a href='/api/status'>/api/status</a> <a href='/api/jdb'>/api/jdb</a></p>"
                        self.wfile.write(html.encode())

            def handle_api(self):
                if self.path in ("/api/status","/api/status/"):
                    info={
                        "server": server_name,
                        "type": server_config.get("type"),
                        "port": server_config.get("port"),
                        "root": server_config.get("root"),
                        "status": "running",
                        "uptime": time.time() - (server_config.get("start_time", time.time())),
                        "jino_version": VERSION,
                        "endpoints": ["/api/status","/api/jdb","/api/files","/api/echo?msg=hi"]
                    }
                    self.send_json(info)
                elif self.path.startswith("/api/jdb"):
                    self.send_json(jdb_ref)
                elif self.path.startswith("/api/files"):
                    files=list(fs_ref.files.keys())
                    self.send_json({"files": files[:100], "count": len(files)})
                elif self.path.startswith("/api/echo"):
                    msg=self.path.split("msg=")[-1] if "msg=" in self.path else "hello"
                    self.send_json({"echo": msg, "server": server_name})
                elif self.path.startswith("/api/config"):
                    self.send_json(server_config)
                else:
                    self.send_json({"error":"unknown api","path":self.path,"available":["/api/status","/api/jdb","/api/files","/api/echo"]})

            def do_POST(self):
                length=int(self.headers.get('Content-Length',0))
                data=self.rfile.read(length).decode() if length else ""
                # if /api/jdb set
                if self.path.startswith("/api/jdb"):
                    try:
                        obj=json.loads(data)
                        jdb_ref.update(obj)
                        self.send_json({"ok":True,"db":jdb_ref})
                    except:
                        # parse form
                        self.send_json({"ok":True,"received":data})
                else:
                    self.send_json({"ok":True,"received":data})

            def send_json(self,obj):
                self.send_response(200)
                self.send_header("Content-Type","application/json")
                self.send_header("Access-Control-Allow-Origin","*")
                self.end_headers()
                self.wfile.write(json.dumps(obj, indent=2).encode())

            def send_html(self,html):
                self.send_response(200)
                self.send_header("Content-Type","text/html")
                self.end_headers()
                self.wfile.write(html.encode())

        return JinoHandler

    def is_port_free(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) != 0

    def start(self):
        if self.status=="running":
            return False, "Already running"
        if not self.is_port_free(self.port):
            return False, f"Port {self.port} already in use"
        self.ensure_real_fs()
        handler=self.make_handler()
        try:
            self.httpd=ThreadingHTTPServer(("127.0.0.1", self.port), handler)
            self.thread=threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            self.status="running"
            self.start_time=time.time()
            self.config["start_time"]=self.start_time
            self.log(f"Started on :{self.port} root {self.root} -> {self.real_root}")
            return True, f"Started {self.name} on http://localhost:{self.port} (http://127.0.0.1:{self.port})"
        except Exception as e:
            return False, str(e)

    def stop(self):
        if self.status!="running":
            return False, "Not running"
        try:
            if self.httpd:
                self.httpd.shutdown()
                self.httpd.server_close()
            self.status="stopped"
            self.log(f"Stopped")
            return True, f"Stopped {self.name}"
        except Exception as e:
            return False, str(e)

    def restart(self):
        self.stop()
        time.sleep(0.5)
        return self.start()

    def get_status(self):
        uptime=0
        if self.start_time: uptime=int(time.time()-self.start_time)
        return {
            "name": self.name,
            "type": self.type,
            "port": self.port,
            "root": self.root,
            "status": self.status,
            "uptime": uptime,
            "real_root": self.real_root,
            "logs": self.logs[-20:]
        }

class ServerManager:
    def __init__(self, fs_ref, jdb_ref):
        self.fs=fs_ref
        self.jdb=jdb_ref
        self.servers={}
        self.load()

    def load(self):
        try:
            if os.path.exists(SERVERS_DB):
                with open(SERVERS_DB,'r') as f:
                    data=json.load(f)
                    for cfg in data.get("servers",[]):
                        self.servers[cfg["name"]]=ServerInstance(cfg, self.fs, self.jdb)
            # also load from FS /etc/servers/*.json
            for fpath, fdata in self.fs.files.items():
                if fpath.startswith("/etc/servers/") and fpath.endswith(".json"):
                    try:
                        cfg=json.loads(fdata["content"])
                        if cfg["name"] not in self.servers:
                            self.servers[cfg["name"]]=ServerInstance(cfg, self.fs, self.jdb)
                    except: pass
            # ensure default server
            if "default" not in self.servers:
                cfg={"name":"default","type":"static","port":80,"root":"/www","auto_start":False}
                self.servers["default"]=ServerInstance(cfg, self.fs, self.jdb)
                self.save()
        except Exception as e:
            print(f"Load servers error {e}")

    def save(self):
        try:
            data={"servers":[s.config for s in self.servers.values()]}
            with open(SERVERS_DB,'w') as f:
                json.dump(data,f, indent=2)
            # also save to FS
            for srv in self.servers.values():
                self.fs.write(f"/etc/servers/{srv.name}.json", json.dumps(srv.config, indent=2))
        except Exception as e:
            print(f"Save error {e}")

    def list_servers(self):
        return list(self.servers.values())

    def get(self,name):
        return self.servers.get(name)

    def create(self, name, template="static", port=8080, root="/www", extra=None):
        if name in self.servers:
            return False, f"Server {name} already exists"
        # check port
        # choose root if not exists, create
        if not self.fs.is_dir(root) and not self.fs.is_file(root):
            self.fs.ensure_dir(root)
            # create default index if needed
            if template=="static":
                html=f"<html><head><title>{name}</title></head><body><h1>{name} - {template}</h1><p>Port {port} Root {root}</p><p>Edit {root}/index.html</p></body></html>"
                self.fs.write(f"{root}/index.html", html)
            elif template=="api":
                self.fs.write(f"{root}/index.html", f"<h1>{name} API Server</h1><p>Endpoints: /api/status, /api/jdb, /api/echo</p>")
            elif template in ("wordpress","php"):
                self.fs.write(f"{root}/index.html", f"<h1>{name} - {template} ready</h1><p>Simulated PHP</p>")
        cfg={"name":name,"type":template,"port":int(port),"root":root,"created":time.time()}
        if extra: cfg.update(extra)
        self.servers[name]=ServerInstance(cfg, self.fs, self.jdb)
        self.save()
        return True, cfg

    def delete(self,name):
        srv=self.servers.get(name)
        if not srv: return False, "Not found"
        if srv.status=="running": srv.stop()
        del self.servers[name]
        self.save()
        # remove FS config
        if self.fs.is_file(f"/etc/servers/{name}.json"):
            self.fs.rm(f"/etc/servers/{name}.json")
        return True, f"Deleted {name}"

    def start(self,name):
        srv=self.get(name)
        if not srv: return False, "Not found"
        ok,msg=srv.start()
        return ok,msg

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
            ok,msg=self.start(name)
            res.append((name,ok,msg))
        return res

    def stop_all(self):
        res=[]
        for name in self.servers:
            ok,msg=self.stop(name)
            res.append((name,ok,msg))
        return res

class PackageManager:
    def __init__(self, fs_ref, srv_manager, jdb_ref):
        self.fs=fs_ref
        self.srv=srv_manager
        self.jdb=jdb_ref
        self.repo=load_repo()

    def list_packages(self, filter_type=None):
        pkgs=self.repo.get("packages",[])
        if filter_type:
            pkgs=[p for p in pkgs if p.get("type")==filter_type or p.get("category")==filter_type]
        return pkgs

    def search(self, term):
        term=term.lower()
        res=[]
        for p in self.repo.get("packages",[]):
            if term in p["name"].lower() or term in p.get("description","").lower() or term in p.get("category",""):
                res.append(p)
        return res

    def get_pkg(self,name):
        for p in self.repo.get("packages",[]):
            if p["name"]==name:
                return p
        return None

    def install(self, name, port=None, custom_name=None, root=None):
        pkg=self.get_pkg(name)
        if not pkg:
            return False, f"Package {name} not found in repo. Try jpkg search or jpkg list"
        # determine server name
        srv_name=custom_name or pkg["name"]
        srv_port=port or pkg.get("port",8080)
        srv_root=root or pkg.get("root", f"/www/{srv_name}")
        srv_type=pkg.get("type","static")
        if srv_type=="template":
            srv_type=name
        # handle dependencies
        for dep in pkg.get("dependencies",[]):
            dep_pkg=self.get_pkg(dep)
            if dep_pkg:
                # check if already installed
                if dep not in [s.name for s in self.srv.list_servers()]:
                    print(f"{C_YELLOW}Installing dependency {dep}...{C_RESET}")
                    self.install(dep)

        # create directories and files based on package type
        cat=pkg.get("category")
        # create root
        self.fs.ensure_dir(srv_root)
        # generate files per package
        if name in ("nginx","apache","jino-web","static","file-server"):
            html=f"""<html>
<head><title>{srv_name} - {name}</title>
<style>body{{background:#0a0a0a;color:#0f0;font-family:monospace;padding:20px}} h1{{color:#ff0}} .box{{border:1px solid #0f0;padding:12px;margin:12px 0}}</style>
</head>
<body>
<h1>🌀 {srv_name} ({name} v{pkg.get('version')})</h1>
<div class="box">Port: {srv_port} | Root: {srv_root} | Type: {srv_type}<br>Installed via jpkg at {time.ctime()}<br>Server: http://localhost:{srv_port}</div>
<div class="box"><h3>API</h3><ul><li><a href="/api/status" style="color:#0ff">/api/status</a></li><li><a href="/api/jdb" style="color:#0ff">/api/jdb</a></li><li><a href="/api/files" style="color:#0ff">/api/files</a></li></ul></div>
<div class="box"><h3>Quick Start</h3><code>edit {srv_root}/index.html</code><br><code>srv logs {srv_name}</code><br><code>curl http://localhost:{srv_port}/api/status</code></div>
</body>
</html>
"""
            self.fs.write(f"{srv_root}/index.html", html)
        elif name in ("api-server","python-api","nodejs","express","flask"):
            self.fs.write(f"{srv_root}/index.html", f"<h1>{srv_name} API Server</h1><p>Template {name}</p><p>Endpoints: /api/status, /api/jdb, /api/echo?msg=hi</p><p>Port {srv_port}</p>")
            # create app file
            self.fs.write(f"{srv_root}/app.py", f"# {name} app\n# Port {srv_port}\nprint('API server {srv_name} running')\n")
            self.fs.write(f"{srv_root}/app.js", f"// {name} Express-like\nconsole.log('Server {srv_name} on :{srv_port}');\n")
        elif name in ("wordpress","php-server"):
            self.fs.write(f"{srv_root}/index.html", f"<h1>{srv_name} - WordPress (simulated)</h1><p>{name} installed via Jino. Port {srv_port}</p><p>This is PHP simulation, edit files in {srv_root}</p>")
            self.fs.write(f"{srv_root}/wp-config.php", f"<?php // wp config for {srv_name} define('DB_NAME','jino'); ?>")
        elif name in ("mysql","postgres","redis"):
            self.fs.write(f"{srv_root}/README.txt", f"{name} database server simulated over JinoDB\nPort {srv_port}\nUse jdb commands to interact\n")
            self.fs.write(f"{srv_root}/data.json", json.dumps({"db": name, "tables": []}))
        elif name in ("chat-server",):
            self.fs.write(f"{srv_root}/index.html", """
<html><body><h1>Chat Server</h1><div id="chat" style="border:1px solid #0f0;height:200px;overflow:auto"></div><input id="msg" placeholder="Message"><button onclick="send()">Send</button><script>function send(){let m=document.getElementById('msg').value; let c=document.getElementById('chat'); c.innerHTML+='<div>'+m+'</div>'; document.getElementById('msg').value='';} setInterval(()=>{fetch('/api/jdb').then(r=>r.json()).then(d=>{/* simulate */})},2000)</script></body></html>
""")
        # create server instance
        ok, res = self.srv.create(srv_name, template=srv_type if srv_type!="server" else "static", port=srv_port, root=srv_root, extra={"pkg":name, "version": pkg.get("version")})
        if not ok:
            # if already exists, update port/root?
            return False, res
        return True, f"Package {name} installed as server '{srv_name}' on :{srv_port} root {srv_root}. Use 'srv start {srv_name}' to start."

# Main JinoOS

class JinoOS:
    def __init__(self):
        self.fs=JinoFS()
        self.jdb={"visits":"1","user":"jino","hostname":"jino-pc","boot_time":str(int(time.time())),"servers":"0"}
        self.history=[]
        self.aliases={"ll":"ls -l","la":"ls -a","dir":"ls","..":"cd ..","h":"history","?":"help","cls":"clear"}
        self.env={"USER":"jino","HOME":"/home/user","PATH":"/bin:/usr/bin:/apps","SHELL":"/bin/jinosh","OS":"Jino OS 2.0","TERM":"jino-256color","PWD":self.fs.cwd,"HOST":"jino-pc","EDITOR":"nano"}
        self.processes=[{"pid":1,"name":"jino_kernel","cpu":"0.1%","mem":"2MB"},{"pid":2,"name":"jino_fs","cpu":"0.0%","mem":"1MB"},{"pid":3,"name":"jinosh","cpu":"0.5%","mem":"1MB"}]
        self.srv_manager=ServerManager(self.fs, self.jdb)
        self.pkg_manager=PackageManager(self.fs, self.srv_manager, self.jdb)
        self.uptime_start=time.time()
        self.last_exit_code=0

    def boot(self):
        print(C_GREEN+C_BOLD+r"""
     ██╗██╗███╗   ██╗ ██████╗      ██████╗ ███████╗
     ██║██║████╗  ██║██═══██╗    ██╔═══██╗██╔════╝
     ██║██║██╔██╗ ██║██║   ██║    ██║   ██║███████╗
██   ██║██║██║╚██╗██║██║   ██║    ██║   ██║╚════██║
╚█████╔╝██║██║ ╚████║╚██████╔╝    ╚██████╔╝███████║
 ╚════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝      ╚═════╝ ╚══════╝

          CONSOLE SERVER EDITION v2.0 - EASY SERVER INSTALLER
"""+C_RESET)
        print(f"{C_CYAN}Jino OS {VERSION} | Build {BUILD} | 32MB | i386{C_RESET}")
        print(f"{C_DIM}Mode: CONSOLE ONLY + Server Installer | FS: JinoFS v2 | Shell: JinoSH 2.0{C_RESET}")
        print(f"{C_GREEN}[OK] Kernel 2.0 loaded{C_RESET}")
        print(f"{C_GREEN}[OK] JinoFS v2 mounted ({len(self.fs.files)} files, {len(self.fs.dirs)} dirs){C_RESET}")
        print(f"{C_GREEN}[OK] JinoDB ready{C_RESET}")
        print(f"{C_GREEN}[OK] Server Manager ready ({len(self.srv_manager.servers)} servers){C_RESET}")
        repo=self.pkg_manager.repo
        print(f"{C_GREEN}[OK] Package Repo: {len(repo.get('packages',[]))} packages{C_RESET}")
        print(f"{C_GREEN}[OK] Real HTTP runtime: {RUNTIME_ROOT}{C_RESET}")
        print()
        motd=self.fs.read("/system/motd.txt")
        if motd: print(f"{C_YELLOW}{motd}{C_RESET}")
        print(f"Type {C_BOLD}help{C_RESET} for help, {C_BOLD}jpkg list{C_RESET} for packages, {C_BOLD}srv list{C_RESET} for servers, {C_BOLD}srv new{C_RESET} for wizard")
        print()

    def parse(self,line):
        stripped=line.strip()
        if not stripped: return [],None,False
        first=stripped.split()[0]
        if first in self.aliases:
            line=self.aliases[first]+" "+" ".join(stripped.split()[1:])
        redirect_out=None; redirect_append=False
        if ">" in line:
            m=re.search(r'\s*(>>|>)\s*([^\s]+)\s*$', line)
            if m:
                op=m.group(1); target=m.group(2); redirect_out=target; redirect_append=(op==">>"); line=line[:m.start()].strip()
        try: parts=shlex.split(line)
        except: parts=line.split()
        return parts,redirect_out,redirect_append

    def output(self,text,redirect_out=None,append=False):
        if redirect_out:
            path=self.fs.norm(redirect_out)
            if append: existing=self.fs.read(path) or ""; self.fs.write(path, existing+text+ ("\n" if not text.endswith("\n") else ""))
            else: self.fs.write(path, text+ ("\n" if not text.endswith("\n") else ""))
            print(f"{C_DIM}-> wrote to {path}{C_RESET}")
        else: print(text)

    # HELP
    def cmd_help(self,args):
        print(f"""{C_BOLD}{C_GREEN}Jino OS v2.0 Console Server Edition - Help{C_RESET}
{C_YELLOW}Теперь с удобной установкой серверов!{C_RESET}

{BOLD}БЫСТРЫЙ СТАРТ СЕРВЕРОВ:{RESET}
  jpkg list                 - список всех доступных серверов/пакетов
  jpkg search nginx         - поиск пакета
  jpkg install nginx        - установить сервер (создает из шаблона)
  jpkg install nginx --port 8080 --name myweb
  srv list                  - список установленных серверов
  srv start myweb           - запустить сервер (реальный HTTP на порту)
  srv stop myweb
  srv restart myweb
  srv status [name]
  srv logs myweb
  srv delete myweb
  srv new                   - мастер создания сервера (вопросы)
  srv quick nginx           - установить + запустить за 1 команду
  deploy . --port 8000      - быстро задеплоить текущую папку как сервер

{BOLD}ОСНОВНЫЕ 80+ КОМАНД:{RESET}
  FS: ls ll la pwd cd cat bat more touch mkdir rmdir rm cp mv find tree du df
  TEXT: echo write edit head tail wc grep sort hexdump base64 diff
  SYS: ver uname whoami date clear history env mem ps top uptime reboot
  NET: ping ifconfig curl wget (старые) + новые jpkg srv
  FUN: calc cowsay fortune banner matrix snake

{BOLD}ПРИМЕРЫ УСТАНОВКИ СЕРВЕРОВ:{RESET}
  jpkg install static --name mysite --port 8080
  srv start mysite
  curl http://localhost:8080/

  jpkg install api-server --port 3000
  srv start api-server
  curl http://localhost:3000/api/status
  curl http://localhost:3000/api/jdb

  jpkg install wordpress --port 8083
  srv start wordpress

  srv new
  -> выбери тип, порт, имя -> готово

  deploy /www --port 9000 --name quicksite
  -> мгновенный сервер из папки

{BOLD}Где лежат файлы:{RESET}
  Виртуальная FS JinoFS: /www, /home/user, /servers, /etc/servers/*.json
  Реальная FS для HTTP: {RUNTIME_ROOT}/<server>/
  Конфиг серверов: /tmp/jino_servers_db.json и /etc/servers/
  Репо пакетов: {REPO_PATH}
""".replace("{BOLD}",C_BOLD).replace("{RESET}",C_RESET))

    def cmd_cmds(self,args):
        print(f"{C_BOLD}Все команды Jino v2.0{C_RESET}")
        print(f"{C_CYAN}SERVER INSTALLER (новые):{C_RESET} jpkg list, jpkg search, jpkg install, jpkg uninstall, jpkg info, jpkg update, srv list, srv create, srv start, srv stop, srv restart, srv status, srv logs, srv delete, srv new, srv quick, srv info, deploy, serve, web, install-server")
        print(f"{C_CYAN}FS:{C_RESET} ls dir ll la pwd cd cat type bat more less touch mkdir md rmdir rd rm del cp mv ren find tree du df stat chmod")
        print(f"{C_CYAN}TEXT:{C_RESET} echo printf write edit nano head tail wc grep sort uniq cut hexdump base64 strings diff rev tee truncate")
        print(f"{C_CYAN}SYS:{C_RESET} ver uname whoami hostname sysinfo date time cal clear history env set alias mem free cpuinfo ps top uptime sleep reboot shutdown exit")
        print(f"{C_CYAN}NET:{C_RESET} ping ifconfig curl wget server jdb")
        print(f"{C_CYAN}FUN:{C_RESET} run calc cowsay fortune banner figlet matrix snake tetris man help tutorial")

    # JPKG COMMANDS
    def cmd_jpkg(self,args):
        if not args:
            print(f"Usage: jpkg list|search|install|uninstall|info|update\nTry: jpkg list")
            return
        sub=args[0]
        if sub=="list":
            filt=args[1] if len(args)>1 else None
            pkgs=self.pkg_manager.list_packages(filt)
            print(f"{C_BOLD}Jino Package Repository - {len(pkgs)} packages{C_RESET}")
            print(f"{'NAME':<20} {'VERSION':<10} {'PORT':<6} {'TYPE':<10} DESCRIPTION")
            print("-"*90)
            for p in pkgs:
                print(f"{C_GREEN}{p['name']:<20}{C_RESET} {p.get('version',''):<10} {str(p.get('port','-')):<6} {p.get('type',''):<10} {p.get('description','')[:50]}")
            print(f"\n{C_DIM}Install: jpkg install <name> [--port PORT] [--name NAME]{C_RESET}")
        elif sub=="search":
            term=args[1] if len(args)>1 else ""
            if not term:
                print("Usage: jpkg search <term>")
                return
            res=self.pkg_manager.search(term)
            print(f"Search '{term}' - {len(res)} found:")
            for p in res:
                print(f" {p['name']:<20} {p.get('description','')}")
        elif sub=="install":
            if len(args)<2:
                print("Usage: jpkg install <package> [--port PORT] [--name NAME] [--root /path]")
                return
            pkg_name=args[1]
            port=None; custom_name=None; root=None
            i=2
            while i < len(args):
                if args[i]=="--port" and i+1<len(args): port=int(args[i+1]); i+=2; continue
                if args[i]=="--name" and i+1<len(args): custom_name=args[i+1]; i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            print(f"{C_YELLOW}Installing {pkg_name}...{C_RESET}")
            ok,msg=self.pkg_manager.install(pkg_name, port=port, custom_name=custom_name, root=root)
            if ok:
                print(f"{C_GREEN}[OK] {msg}{C_RESET}")
                # suggest start
                srv_name=custom_name or pkg_name
                print(f"{C_CYAN}Now run: srv start {srv_name}  or  srv quick {pkg_name}{C_RESET}")
            else:
                print(f"{C_RED}[FAIL] {msg}{C_RESET}")
        elif sub=="uninstall" or sub=="remove":
            if len(args)<2:
                print("Usage: jpkg uninstall <server-name>  (alias for srv delete)")
                return
            name=args[1]
            ok,msg=self.srv_manager.delete(name)
            print(f"{'OK' if ok else 'FAIL'} {msg}")
        elif sub=="info":
            if len(args)<2:
                print("Usage: jpkg info <package>")
                return
            pkg=self.pkg_manager.get_pkg(args[1])
            if not pkg:
                print(f"Package {args[1]} not found")
            else:
                print(json.dumps(pkg, indent=2))
        elif sub in ("update","upgrade"):
            self.pkg_manager.repo=load_repo()
            print(f"{C_GREEN}Repo updated, {len(self.pkg_manager.repo.get('packages',[]))} packages{C_RESET}")
        else:
            print(f"Unknown jpkg subcommand {sub}")

    # SRV COMMANDS
    def cmd_srv(self,args):
        if not args:
            print("Usage: srv list|create|start|stop|restart|status|logs|delete|new|quick|info")
            return
        sub=args[0]
        if sub in ("list","ls","l"):
            servers=self.srv_manager.list_servers()
            if not servers:
                print("(no servers installed) Try jpkg list, jpkg install nginx")
                return
            print(f"{C_BOLD}{'NAME':<15} {'TYPE':<12} {'PORT':<6} {'STATUS':<10} {'ROOT':<20} URL{C_RESET}")
            print("-"*90)
            for s in servers:
                st=s.get_status()
                status_color=C_GREEN if st["status"]=="running" else C_RED
                print(f"{st['name']:<15} {st['type']:<12} {str(st['port']):<6} {status_color}{st['status']:<10}{C_RESET} {st['root']:<20} http://localhost:{st['port']}")
            print(f"\n{C_DIM}Total {len(servers)} servers{C_RESET}")
        elif sub=="create":
            # srv create <name> --template static --port 8080 --root /www
            if len(args)<2:
                print("Usage: srv create <name> --template <static|api|file|wordpress|...> --port <port> --root <path>")
                return
            name=args[1]
            template="static"; port=8080; root=f"/www/{name}"
            i=2
            while i < len(args):
                if args[i]=="--template" and i+1<len(args): template=args[i+1]; i+=2; continue
                if args[i]=="--port" and i+1<len(args): port=int(args[i+1]); i+=2; continue
                if args[i]=="--root" and i+1<len(args): root=args[i+1]; i+=2; continue
                i+=1
            ok,res=self.srv_manager.create(name, template=template, port=port, root=root)
            if ok:
                print(f"{C_GREEN}Server {name} created: template={template} port={port} root={root}{C_RESET}")
            else:
                print(f"{C_RED}{res}{C_RESET}")
        elif sub=="start":
            if len(args)<2:
                # check --all
                if "--all" in args:
                    print("Starting all servers...")
                    for name,ok,msg in self.srv_manager.start_all():
                        print(f"{name}: {'OK' if ok else 'FAIL'} {msg}")
                    return
                print("Usage: srv start <name> or srv start --all")
                return
            name=args[1]
            ok,msg=self.srv_manager.start(name)
            print(f"{C_GREEN if ok else C_RED}{msg}{C_RESET}")
            if ok:
                print(f"{C_CYAN}Test: curl http://localhost:{self.srv_manager.get(name).port}/  or open in browser{C_RESET}")
        elif sub=="stop":
            if len(args)<2:
                if "--all" in args:
                    for name,ok,msg in self.srv_manager.stop_all():
                        print(f"{name}: {msg}")
                    return
                print("Usage: srv stop <name> or --all")
                return
            name=args[1]
            ok,msg=self.srv_manager.stop(name)
            print(msg)
        elif sub=="restart":
            if len(args)<2:
                print("Usage: srv restart <name>")
                return
            ok,msg=self.srv_manager.restart(args[1])
            print(msg)
        elif sub=="status":
            name=args[1] if len(args)>1 else None
            if name:
                srv=self.srv_manager.get(name)
                if not srv:
                    print(f"Server {name} not found")
                else:
                    st=srv.get_status()
                    print(json.dumps(st, indent=2))
                    print(f"\nURL: http://localhost:{st['port']}")
                    print(f"Real path: {st['real_root']}")
                    print(f"Logs tail:")
                    for l in st["logs"][-10:]:
                        print(f"  {l}")
            else:
                # all
                self.cmd_srv(["list"])
        elif sub=="logs":
            if len(args)<2:
                print("Usage: srv logs <name>")
                return
            srv=self.srv_manager.get(args[1])
            if not srv:
                print("Not found")
            else:
                print(f"Logs for {srv.name}:")
                for l in srv.logs[-50:]:
                    print(l)
        elif sub in ("delete","remove","rm","del"):
            if len(args)<2:
                print("Usage: srv delete <name>")
                return
            ok,msg=self.srv_manager.delete(args[1])
            print(msg)
        elif sub=="new":
            self.cmd_srv_new()
        elif sub=="quick":
            if len(args)<2:
                print("Usage: srv quick <package> [--port PORT]")
                return
            pkg=args[1]
            port=None
            if "--port" in args:
                idx=args.index("--port")
                if idx+1<len(args): port=int(args[idx+1])
            print(f"{C_YELLOW}Quick install {pkg}...{C_RESET}")
            ok,msg=self.pkg_manager.install(pkg, port=port)
            if not ok:
                print(f"{C_RED}{msg}{C_RESET}")
                # maybe try create if template
                if self.pkg_manager.get_pkg(pkg) is None:
                    # create as template
                    ok2,res2=self.srv_manager.create(pkg, template="static", port=port or 8080, root=f"/www/{pkg}")
                    if ok2:
                        print(f"Created template server {pkg}")
                        ok,msg=self.srv_manager.start(pkg)
                        print(msg)
                    else:
                        print(res2)
                return
            print(f"{C_GREEN}{msg}{C_RESET}")
            srv_name=pkg
            # auto start
            ok2,msg2=self.srv_manager.start(srv_name)
            print(f"{C_GREEN if ok2 else C_RED}{msg2}{C_RESET}")
        elif sub=="info":
            if len(args)<2:
                print("Usage: srv info <name>")
                return
            srv=self.srv_manager.get(args[1])
            if not srv:
                print("Not found")
            else:
                print(json.dumps(srv.config, indent=2))
                st=srv.get_status()
                print(f"\nStatus: {st['status']} Uptime: {st['uptime']}s Port: {st['port']}")
        else:
            print(f"Unknown srv command {sub}")

    def cmd_srv_new(self):
        print(f"{C_BOLD}{C_CYAN}=== Jino Server Creation Wizard ==={C_RESET}")
        print("This wizard will help you create a server easily.")
        name=input(f"{C_YELLOW}Server name (e.g. myblog, api, mysite): {C_RESET}").strip()
        if not name:
            print("Cancelled")
            return
        print("Templates: static, api-server, file-server, python-api, nodejs, php-server, wordpress, chat-server, game-server, mysql, redis")
        template=input(f"{C_YELLOW}Template [{C_DIM}static{C_RESET}{C_YELLOW}]: {C_RESET}").strip() or "static"
        port_str=input(f"{C_YELLOW}Port [{C_DIM}8080{C_RESET}{C_YELLOW}]: {C_RESET}").strip() or "8080"
        try: port=int(port_str)
        except: port=8080
        root_default=f"/www/{name}" if template in ("static","file-server","wordpress","php-server") else f"/apps/{name}"
        root=input(f"{C_YELLOW}Root path [{C_DIM}{root_default}{C_RESET}{C_YELLOW}]: {C_RESET}").strip() or root_default
        print(f"\nCreating server '{name}' template={template} port={port} root={root}...")
        ok,res=self.srv_manager.create(name, template=template, port=port, root=root)
        if not ok:
            print(f"{C_RED}Error: {res}{C_RESET}")
            return
        print(f"{C_GREEN}Created!{C_RESET}")
        auto=input(f"{C_YELLOW}Start now? (Y/n): {C_RESET}").strip().lower()
        if auto!="n":
            ok2,msg2=self.srv_manager.start(name)
            print(msg2)
            print(f"{C_CYAN}Open http://localhost:{port} in browser or curl it{C_RESET}")

    def cmd_deploy(self,args):
        # deploy <path> --port 8000 --name name
        path="."
        port=8000
        name=None
        i=0
        while i < len(args):
            if args[i]=="--port" and i+1<len(args): port=int(args[i+1]); i+=2; continue
            if args[i]=="--name" and i+1<len(args): name=args[i+1]; i+=2; continue
            if not args[i].startswith("--"): path=args[i]
            i+=1
        abs_path=self.fs.norm(path)
        if not name:
            name=os.path.basename(abs_path) or f"deploy{port}"
            if name=="/": name=f"site{port}"
        # if path is file, use its dir?
        # create server
        root=abs_path
        # if file, root is its dir
        if self.fs.is_file(root):
            root=os.path.dirname(root)
        print(f"{C_YELLOW}Deploying {abs_path} as server '{name}' on :{port}...{C_RESET}")
        ok,res=self.srv_manager.create(name, template="static", port=port, root=root)
        if not ok:
            print(f"{C_RED}{res}{C_RESET}")
            return
        ok2,msg2=self.srv_manager.start(name)
        print(f"{C_GREEN}{msg2}{C_RESET}")
        print(f"{C_CYAN}Deployed! http://localhost:{port}{C_RESET}")

    # Include all old commands (abbreviated but keep)

    def cmd_ver(self,args): print(f"{C_BOLD}Jino OS {VERSION}{C_RESET}\nKernel: JinoKernel 2.0 Server Edition\nBuild: {BUILD}\nFS: {len(self.fs.files)} files\nServers: {len(self.srv_manager.servers)}\nMode: CONSOLE + Easy Server Installer")

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
                if long: print(f"{s['perms']} {s['size']:>6} {time.strftime('%Y-%m-%d %H:%M', time.localtime(s['mtime']))} {os.path.basename(abs_path)}")
                else: print(os.path.basename(abs_path))
                return
            print(f"{C_RED}ls: {path}: No such{C_RESET}"); return
        dirs,files=listing
        if not show_all:
            dirs=[d for d in dirs if not d.startswith(".")]; files=[f for f in files if not f.startswith(".")]
        if long:
            print(f"total {len(dirs)+len(files)} in {abs_path}")
            for d in dirs: print(f"{C_BLUE}{d}/{C_RESET}")
            for f in files:
                st=self.fs.stat(abs_path.rstrip("/")+ "/"+f)
                print(f"- {st['perms'] if st else ''} {st['size'] if st else 0:>6} {f}")
        else:
            all_items=[f"{C_BLUE}{d}/{C_RESET}" for d in dirs] + files
            if all_items: print("  ".join(all_items))
            else: print("(empty)")

    def cmd_pwd(self,args): print(self.fs.cwd)
    def cmd_cd(self,args):
        if not args: self.fs.cwd="/home/user"; self.env["PWD"]=self.fs.cwd; return
        target=args[0]
        if target=="..":
            if self.fs.cwd!="/": self.fs.cwd=os.path.dirname(self.fs.cwd.rstrip("/")) or "/"
            self.env["PWD"]=self.fs.cwd; return
        new_path=self.fs.norm(target)
        if new_path in self.fs.dirs: self.fs.cwd=new_path
        elif new_path in self.fs.files: print(f"{C_RED}cd: not dir{C_RESET}")
        else:
            if any(f.startswith(new_path+"/") for f in self.fs.files) or any(d.startswith(new_path+"/") for d in self.fs.dirs):
                self.fs.ensure_dir(new_path); self.fs.cwd=new_path
            else: print(f"{C_RED}cd: no such{C_RESET}"); return
        self.env["PWD"]=self.fs.cwd
    def cmd_cat(self,args):
        if not args: print("Usage: cat <file>"); return
        for p in args:
            c=self.fs.read(p)
            if c is None: print(f"{C_RED}cat: {p}: no file{C_RESET}")
            else: print(c)
    def cmd_mkdir(self,args):
        for p in args:
            ok,msg=self.fs.mkdir(p); print(f"mkdir {msg}" if ok else f"Error {msg}")
    def cmd_rm(self,args):
        recursive=False; targets=[]
        for a in args:
            if a in ("-r","-rf","-R"): recursive=True
            else: targets.append(a)
        for p in targets:
            ap=self.fs.norm(p)
            if self.fs.is_file(ap): self.fs.rm(ap); print(f"Removed {ap}")
            elif self.fs.is_dir(ap) and recursive:
                to_del=[f for f in self.fs.files if f==ap or f.startswith(ap+"/")]; 
                for f in to_del: del self.fs.files[f]
                to_del_d=[d for d in self.fs.dirs if d==ap or d.startswith(ap+"/")]
                for d in to_del_d:
                    if d in self.fs.dirs: self.fs.dirs.remove(d)
                self.fs.dirs.add("/"); self.fs.save_persist(); print(f"Removed dir {ap}")
            else: print(f"rm: {p}: no")
    def cmd_echo(self,args,raw,redir_out,redir_append):
        import re
        m=re.search(r'echo\s+(.*)', raw, re.IGNORECASE)
        text=m.group(1) if m else " ".join(args)
        if ">" in raw and redir_out:
            text=text.split(">")[0].strip()
        # Remove quotes?
        if text.startswith('"') and text.endswith('"'): text=text[1:-1]
        if redir_out:
            path=self.fs.norm(redir_out)
            if redir_append:
                existing=self.fs.read(path) or ""
                self.fs.write(path, existing+text+"\n")
            else:
                self.fs.write(path, text+"\n")
            print(f"-> wrote to {path}")
        else:
            print(text)
    def cmd_write(self,args):
        if not args: print("Usage: write <file>"); return
        path=args[0]
        print(f"Writing to {path}. Enter lines, '.' or ':wq' to save:")
        lines=[]
        try:
            while True:
                line=input(f"{C_DIM}{len(lines)+1:3}> {C_RESET}")
                if line in (".",":wq",":x"): break
                if line==":q!": print("Abort"); return
                lines.append(line)
        except EOFError: pass
        content="\n".join(lines); self.fs.write(path, content); print(f"Saved {len(content)}b")
    def cmd_clear(self,args): os.system("clear||cls"); print("\033[2J\033[H",end="")
    def cmd_history(self,args):
        for i,h in enumerate(self.history[-100:],1): print(f"{i:4} {h}")
    def cmd_mem(self,args):
        total=32*1024*1024; used=sum(len(d["content"]) for d in self.fs.files.values())+2*1024*1024
        print(f"Total 32M Used {used//1024}K Free {(total-used)//1024}K")
    def cmd_ps(self,args):
        print(f"{'PID':<6} {'NAME':<15} {'STATUS'}")
        for p in [{"pid":1,"name":"jino_kernel"},{"pid":2,"name":"jino_fs"},{"pid":3,"name":"jinosh"}]:
            print(f"{p['pid']:<6} {p['name']:<15}")
        for s in self.srv_manager.list_servers():
            if s.status=="running":
                print(f"{s.port:<6} {s.name:<15} running :{s.port}")
    def cmd_jdb(self,args):
        if not args: print("Usage: jdb set/get/list"); return
        op=args[0]
        if op=="set" and len(args)>=3:
            k=args[1]; v=" ".join(args[2:]); self.jdb[k]=v; self.fs.write(f"/db/{k}.json", json.dumps({"key":k,"value":v})); print(f"OK {k}={v}")
        elif op=="get" and len(args)>=2: print(self.jdb.get(args[1],"(nil)"))
        elif op=="list":
            for k,v in self.jdb.items(): print(f"{k} = {v}")
        elif op=="del" and len(args)>=2:
            if args[1] in self.jdb: del self.jdb[args[1]]; print("Deleted")
        else: print("Usage: jdb set/get/list/del")
    def cmd_calc(self,args):
        if not args: print("Usage: calc expr"); return
        expr=" ".join(args).replace("^","**")
        allowed={"sin":math.sin,"cos":math.cos,"sqrt":math.sqrt,"pi":math.pi}
        try: print(eval(expr, {"__builtins__":{}}, allowed))
        except Exception as e: print(f"error {e}")
    def cmd_cowsay(self,args):
        text=" ".join(args) or "Jino Server Edition"
        print(f" _{'_'*len(text)}_\n< {text} >\n -{'-'*len(text)}-\n        \\   ^__^\n         \\  (oo)\\_______\n            (__)\\       )\\/\\\n                ||----w |\n                ||     ||")
    def cmd_sysinfo(self,args):
        print(f"Jino OS {VERSION}\nFS files {len(self.fs.files)}\nServers {len(self.srv_manager.servers)} running {len([s for s in self.srv_manager.servers.values() if s.status=='running'])}\nRepo pkgs {len(self.pkg_manager.repo.get('packages',[]))}\nUptime {int(time.time()-self.uptime_start)}s")
    def cmd_date(self,args): print(datetime.datetime.now())
    def cmd_reboot(self,args): print("Reboot..."); time.sleep(0.5); self.boot()
    def cmd_shutdown(self,args): print("Shutdown..."); sys.exit(0)

    # Dispatch
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
        elif cmd=="cowsay": self.cmd_cowsay(args)
        elif cmd in ("ver","version"): self.cmd_ver(args)
        elif cmd=="sysinfo": self.cmd_sysinfo(args)
        elif cmd=="date": self.cmd_date(args)
        elif cmd in ("reboot","shutdown","exit","quit","poweroff"):
            if cmd=="reboot": self.cmd_reboot(args)
            else: self.cmd_shutdown(args)
        elif cmd=="help": self.cmd_help(args)
        elif cmd=="cmds": self.cmd_cmds(args)
        elif cmd=="jpkg": self.cmd_jpkg(args)
        elif cmd in ("srv","server","service","systemctl","pm2"): self.cmd_srv(args)
        elif cmd in ("deploy","serve","web","install-server"): self.cmd_deploy(args)
        elif cmd=="tutorial":
            print("Tutorial: jpkg list, jpkg install nginx, srv start nginx, curl http://localhost:8080/")
        elif cmd=="man":
            print(f"man {args[0] if args else ''} - see help")
        else:
            print(f"{C_RED}Unknown {cmd}. Try help, cmds, jpkg list, srv list{C_RESET}")

    def run(self):
        self.boot()
        auto=self.fs.read("/autoexec.jino")
        if auto:
            for line in auto.splitlines():
                if line.strip():
                    print(f"{C_DIM}> {line}{C_RESET}")
                    self.dispatch(line)
        while True:
            try:
                prompt=f"{C_BOLD}{C_GREEN}{self.env['USER']}@{self.env['HOST']}{C_RESET}:{C_BLUE}{self.fs.cwd}{C_RESET}$ "
                line=input(prompt)
                self.dispatch(line)
            except KeyboardInterrupt:
                print("\nUse exit")
            except EOFError:
                break
            except SystemExit:
                break
            except Exception as e:
                import traceback
                print(f"{C_RED}Panic {e}{C_RESET}"); traceback.print_exc()

if __name__=="__main__":
    os.makedirs(RUNTIME_ROOT, exist_ok=True)
    osys=JinoOS()
    osys.run()
