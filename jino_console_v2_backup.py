#!/usr/bin/env python3
"""
Jino OS v1.0 CONSOLE EDITION - No GUI, Pure Terminal, 80+ Commands
FullStack DOS-like OS written in Python
"""
import os, sys, time, json, shlex, base64, re, random, math, hashlib
import shutil, textwrap, datetime, platform, subprocess
from pathlib import Path
from collections import Counter

VERSION = "1.0 Console Edition"
BUILD = "2026-07-13 NO-GUI BUILD"

# Colors
C_RESET="\033[0m"
C_GREEN="\033[92m"
C_YELLOW="\033[93m"
C_CYAN="\033[96m"
C_RED="\033[91m"
C_MAGENTA="\033[95m"
C_BLUE="\033[94m"
C_BOLD="\033[1m"
C_DIM="\033[2m"

class JinoFS:
    def __init__(self):
        self.files = {} # path -> {content, mtime, perms, size}
        self.dirs = set(["/"])
        self.cwd = "/"
        self._init_defaults()
        self.load_persist()

    def _init_defaults(self):
        now = time.time()
        def mkfile(p,c, perm="rw-r--r--"):
            self.files[self.norm(p)] = {"content": c, "mtime": now, "perms": perm}
            d = os.path.dirname(self.norm(p))
            if d: self.ensure_dir(d)
        def mkdir(p):
            self.ensure_dir(self.norm(p))
        mkdir("/bin"); mkdir("/etc"); mkdir("/home"); mkdir("/home/user"); mkdir("/www"); mkdir("/var"); mkdir("/tmp"); mkdir("/apps"); mkdir("/db"); mkdir("/usr"); mkdir("/system")
        mkfile("/readme.txt", "Jino OS v1.0 Console Edition\n============================\nNo GUI, Pure Console, 80+ commands\nDOS-based FullStack OS\n\nType 'help' or 'cmds'\n")
        mkfile("/autoexec.jino", "echo Jino OS 1.0 Booted\nmem\nver\n")
        mkfile("/www/index.html", "<html><head><title>JinoServer</title></head><body><h1>JinoServer 1.0 Works!</h1><p>FullStack mode. Edit this file via 'edit /www/index.html'</p><p>JinoDB hits: {{hits}}</p></body></html>")
        mkfile("/etc/hosts", "127.0.0.1 localhost\n127.0.0.1 jino.local\n")
        mkfile("/etc/config.sys", "memory=32MB\nfs=JinoFS v2\nshell=JinoSH v1.0\nmode=console_only\nnetwork=enabled\n")
        mkfile("/apps/hello.japp", 'print("Hello Jino!")\nserver.route("/api/hello", () => "Hello from Jino!")\ndb.set("visits", db.get("visits")+1)\n')
        mkfile("/home/user/notes.txt", "My notes in Jino OS\n- buy milk\n- code OS\n")
        mkfile("/system/motd.txt", "Welcome to Jino OS Console! No graphics, only power.\n")
        mkfile("/bin/.keep", "")
        mkdir("/home/user/docs")
        mkfile("/home/user/docs/todo.txt", "- [ ] Add more commands\n- [ ] Build real kernel\n- [x] Remove GUI\n")

    def persist_file(self):
        return "/tmp/jino_fs_persist.json"

    def load_persist(self):
        try:
            pf = self.persist_file()
            if os.path.exists(pf):
                with open(pf,'r') as f:
                    data=json.load(f)
                    # merge
                    for k,v in data.get("files", {}).items():
                        if k not in self.files:
                            self.files[k]=v
                    for d in data.get("dirs", []):
                        self.dirs.add(d)
        except: pass

    def save_persist(self):
        try:
            with open(self.persist_file(),'w') as f:
                json.dump({"files": self.files, "dirs": list(self.dirs)}, f)
        except: pass

    def norm(self, p):
        if not p: return self.cwd
        p = str(p).strip()
        if not p.startswith("/"):
            p = os.path.join(self.cwd, p)
        p = os.path.normpath(p).replace("\\","/")
        if not p.startswith("/"): p="/"+p
        if len(p)>1 and p.endswith("/"): p=p[:-1]
        return p

    def ensure_dir(self, path):
        path=self.norm(path)
        parts=path.split("/")
        cur=""
        for part in parts:
            if not part: cur="/"; self.dirs.add(cur); continue
            cur = cur.rstrip("/") + "/" + part
            if cur=="" : cur="/"
            self.dirs.add(cur)

    def is_dir(self, path):
        return self.norm(path) in self.dirs

    def is_file(self, path):
        return self.norm(path) in self.files

    def list_dir(self, path=None):
        if path is None: path=self.cwd
        path=self.norm(path)
        if path not in self.dirs:
            # check if has children
            if not any(f.startswith(path+"/") for f in self.files) and path not in self.files:
                return None
        files=[]
        dirs=[]
        prefix = path if path=="/" else path+"/"
        for d in self.dirs:
            if d==path: continue
            if os.path.dirname(d)==path:
                dirs.append(os.path.basename(d))
        for fpath in self.files:
            if os.path.dirname(fpath)==path:
                # exclude dirs that are also files? no
                files.append(os.path.basename(fpath))
        # also nested check for dirs not registered but have files
        for fpath in self.files:
            if fpath.startswith(prefix):
                rel = fpath[len(prefix):].split("/")[0]
                if "/" in fpath[len(prefix):] and rel not in dirs:
                    dirs.append(rel)
        return sorted(dirs), sorted(files)

    def read(self, path):
        p=self.norm(path)
        if p in self.files:
            return self.files[p]["content"]
        return None

    def stat(self, path):
        p=self.norm(path)
        if p in self.files:
            d=self.files[p]
            return {"type":"file","size":len(d["content"]),"mtime":d["mtime"],"perms":d["perms"],"path":p}
        if p in self.dirs:
            return {"type":"dir","size":4096,"mtime":time.time(),"perms":"rwxr-xr-x","path":p}
        return None

    def write(self, path, content, perms=None):
        p=self.norm(path)
        dirn=os.path.dirname(p)
        self.ensure_dir(dirn)
        now=time.time()
        old_perms = self.files.get(p, {}).get("perms","rw-r--r--")
        self.files[p]={"content": content, "mtime": now, "perms": perms or old_perms}
        self.save_persist()

    def mkdir(self, path):
        p=self.norm(path)
        if p in self.files:
            return False, "File exists"
        if p in self.dirs:
            return False, "Exists"
        self.ensure_dir(p)
        self.save_persist()
        return True, p

    def rmdir(self, path):
        p=self.norm(path)
        if p=="/": return False, "Cannot remove /"
        if p not in self.dirs: return False, "No such dir"
        # check empty
        prefix=p if p=="/" else p+"/"
        for f in self.files:
            if f.startswith(prefix) or os.path.dirname(f)==p:
                return False, "Dir not empty"
        for d in self.dirs:
            if d!=p and d.startswith(prefix):
                return False, "Dir not empty"
        self.dirs.remove(p)
        self.save_persist()
        return True, "OK"

    def rm(self, path):
        p=self.norm(path)
        if p in self.files:
            del self.files[p]
            self.save_persist()
            return True
        return False

    def cp(self, src, dst):
        s=self.norm(src); d=self.norm(dst)
        if s not in self.files: return False, "src not found"
        if self.is_dir(d):
            d = d.rstrip("/") + "/" + os.path.basename(s)
        self.write(d, self.files[s]["content"])
        return True, d

    def mv(self, src, dst):
        s=self.norm(src); d=self.norm(dst)
        if s in self.files:
            if self.is_dir(d):
                d = d.rstrip("/") + "/" + os.path.basename(s)
            self.write(d, self.files[s]["content"])
            del self.files[s]
            self.save_persist()
            return True, d
        if s in self.dirs:
            # rename dir - complex, move all children
            if d in self.dirs: return False, "dst exists"
            new_dirs=set()
            for dirpath in self.dirs:
                if dirpath==s or dirpath.startswith(s+"/"):
                    new_dirs.add(d + dirpath[len(s):])
                else:
                    new_dirs.add(dirpath)
            new_files={}
            for fpath, fdata in self.files.items():
                if fpath==s or fpath.startswith(s+"/"):
                    new_files[d + fpath[len(s):]]=fdata
                else:
                    new_files[fpath]=fdata
            self.dirs=new_dirs
            self.files=new_files
            self.save_persist()
            return True, d
        return False, "not found"

class JinoOS:
    def __init__(self):
        self.fs = JinoFS()
        self.jdb = {"visits":"1","user":"jino","hostname":"jino-pc","boot_time":str(int(time.time()))}
        self.history = []
        self.aliases = {"ll":"ls -l", "la":"ls -a", "dir":"ls", "..":"cd ..", "h":"history", "?":"help"}
        self.env = {"USER":"jino","HOME":"/home/user","PATH":"/bin:/usr/bin:/apps","SHELL":"/bin/jinosh","OS":"Jino OS 1.0","TERM":"jino-256color","PWD":self.fs.cwd, "HOST":"jino-pc", "EDITOR":"nano"}
        self.processes = [{"pid":1,"name":"jino_kernel","cpu":"0.1%","mem":"2MB"},{"pid":2,"name":"jino_fs","cpu":"0.0%","mem":"1MB"},{"pid":3,"name":"jinosh","cpu":"0.5%","mem":"1MB"}]
        self.server_running=False
        self.server_port=80
        self.uptime_start=time.time()
        self.last_exit_code=0

    # BOOT
    def boot(self):
        print(C_GREEN + C_BOLD)
        print(r"""
     ██╗██╗███╗   ██╗ ██████╗      ██████╗ ███████╗
     ██║██║████╗  ██║██═══██╗    ██╔═══██╗██╔════╝
     ██║██║██╔██╗ ██║██║   ██║    ██║   ██║███████╗
██   ██║██║██║╚██╗██║██║   ██║    ██║   ██║╚════██║
╚█████╔╝██║██║ ╚████║╚██████╔╝    ╚██████╔╝███████║
 ╚════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝      ╚═════╝ ╚══════╝

          CONSOLE EDITION v1.0 - NO GUI, PURE POWER
""" + C_RESET)
        print(f"{C_CYAN}Jino OS {VERSION} | Build {BUILD} | 32MB RAM | CPU i386{C_RESET}")
        print(f"{C_DIM}Mode: CONSOLE ONLY | FS: JinoFS v2 | Shell: JinoSH 1.0{C_RESET}")
        print(f"{C_GREEN}[OK] JinoKernel 1.0 loaded at 0x100000 (128KB){C_RESET}")
        print(f"{C_GREEN}[OK] Memory Manager: 32 MB (buddy allocator){C_RESET}")
        print(f"{C_GREEN}[OK] JinoFS v2 mounted ({len(self.fs.files)} files, {len(self.fs.dirs)} dirs){C_RESET}")
        print(f"{C_GREEN}[OK] Drivers: VGA text 80x25, PS/2 keyboard, ATA, PIT 100Hz{C_RESET}")
        print(f"{C_GREEN}[OK] JinoDB engine ready ({len(self.jdb)} keys){C_RESET}")
        print(f"{C_GREEN}[OK] JinoServer :80 (console) ready{C_RESET}")
        print(f"{C_GREEN}[OK] 80+ commands loaded{C_RESET}")
        print()
        # motd
        motd=self.fs.read("/system/motd.txt")
        if motd: print(f"{C_YELLOW}{motd}{C_RESET}")
        print(f"Type {C_BOLD}help{C_RESET} for intro, {C_BOLD}cmds{C_RESET} for all commands, {C_BOLD}tutorial{C_RESET} for guide")
        print()

    # UTILS
    def parse(self, line):
        # handle aliases first word
        stripped=line.strip()
        if not stripped: return [], line
        first=stripped.split()[0]
        if first in self.aliases:
            line = self.aliases[first] + " " + " ".join(stripped.split()[1:])
        # split redirection
        # echo foo > file
        # We'll manually parse >, >>, |
        redirect_out = None
        redirect_append = False
        if ">" in line:
            # naive but handle quotes? Use simple
            # Find last > not in quotes? For simplicity split
            if line.count(">")>=1:
                # check >> append
                m = re.search(r'\s*(>>|>)\s*([^\s]+)\s*$', line)
                if m:
                    op=m.group(1)
                    target=m.group(2)
                    redirect_out=target
                    redirect_append = (op==">>")
                    line = line[:m.start()].strip()
        try:
            parts=shlex.split(line)
        except:
            parts=line.split()
        return parts, redirect_out, redirect_append

    def output(self, text, redirect_out=None, append=False):
        if redirect_out:
            path=self.fs.norm(redirect_out)
            if append:
                existing=self.fs.read(path) or ""
                self.fs.write(path, existing+text+ ("\n" if not text.endswith("\n") else ""))
            else:
                self.fs.write(path, text+ ("\n" if not text.endswith("\n") else ""))
            print(f"{C_DIM}-> wrote to {path}{C_RESET}")
        else:
            print(text)

    def print_color(self, text, color=C_RESET):
        print(f"{color}{text}{C_RESET}")

    # COMMANDS IMPLEMENTATION

    def cmd_help(self, args):
        print(f"""{C_BOLD}{C_GREEN}Jino OS v1.0 Console Edition - Help{C_RESET}
{C_YELLOW}Философия: No GUI, только консоль, максимум мощности как в DOS + Linux{C_RESET}

{BOLD}БЫСТРЫЙ СТАРТ:{RESET}
  help       - эта справка
  cmds       - список всех 80+ команд
  tutorial   - обучение
  man <cmd>  - справка по команде

{BOLD}Файловые:{RESET}
  ls, dir, ll, la, tree, pwd, cd, cat, type, bat, more, less
  touch, mkdir, rmdir, rm, cp, mv, ren, find, du, df, stat, chmod

{BOLD}Текстовые:{RESET}
  echo, printf, write, edit, nano, head, tail, wc, grep, sort, uniq, hexdump, base64, strings, diff

{BOLD}Система:{RESET}
  ver, uname, whoami, hostname, sysinfo, date, time, cal, clear, history, env, set, alias, mem, free, ps, top, uptime

{BOLD}FullStack:{RESET}
  server start/stop/status, jdb set/get/del/list, ping, ifconfig, curl, wget

{BOLD}Разработка/Фан:{RESET}
  run, calc, cowsay, fortune, matrix, snake, tetris, banner, figlet

Примеры:
  echo "hello" > /home/user/hi.txt
  cat /readme.txt
  jdb set name Jino
  server start
  find / -name *.txt
""".replace("{BOLD}", C_BOLD).replace("{RESET}", C_RESET).replace("{YELLOW}",C_YELLOW).replace("{GREEN}",C_GREEN))

    def cmd_cmds(self, args):
        # Full list
        all_cmds = {
            "FS": ["ls","dir","ll","la","l","pwd","cd","cat","type","bat","more","less","touch","mkdir","md","rmdir","rd","rm","del","erase","cp","copy","mv","move","ren","rename","find","locate","tree","du","df","stat","chmod","attrib","truncate","ln","link"],
            "TEXT": ["echo","printf","write","edit","nano","ed","vi","head","tail","wc","grep","egrep","sort","uniq","cut","tr","fmt","fold","nl","tac","rev","column","hexdump","xxd","base64","strings","diff","cmp","tee","xargs"],
            "SYS": ["ver","version","uname","whoami","id","hostname","sysinfo","info","date","time","cal","calendar","clear","cls","history","env","set","export","unset","alias","unalias","mem","free","meminfo","cpuinfo","ps","jobs","kill","top","htop","uptime","dmesg","lshw","lsmod","lspci","who","whoami","df","sync","sleep","reboot","shutdown","exit","quit","poweroff","halt","suspend"],
            "NET/FS": ["ping","ifconfig","ipconfig","netstat","ss","curl","wget","http","server","jdb","routes","route","nslookup","host"],
            "DEV/FUN": ["run","exec","eval","js","calc","bc","expr","python","py","cowsay","fortune","banner","figlet","lolcat","boxes","matrix","sl","starwars","snake","tetris","hangman","guess","2048","doom","man","whatis","apropos","tutorial","motd"]
        }
        for cat, cmds in all_cmds.items():
            print(f"{C_BOLD}{C_CYAN}{cat}:{C_RESET} {', '.join(cmds)}")
        print(f"\nTotal: {sum(len(v) for v in all_cmds.values())} commands")
        print(f"Type {C_YELLOW}man <command>{C_RESET} for help")

    def cmd_tutorial(self, args):
        steps=[
            ("1. Файлы", "ls, cd /home/user, cat notes.txt, mkdir test, echo hi > test/file.txt"),
            ("2. Текст", "cat test/file.txt, grep hi test/file.txt, wc test/file.txt"),
            ("3. База данных", "jdb set visits 100, jdb get visits, jdb list"),
            ("4. Сервер", "server start, edit /www/index.html, server status"),
            ("5. Система", "mem, ps, sysinfo, top, history"),
            ("6. Фан", "cowsay Jino OS, fortune, calc 2+2*10, banner JINO"),
        ]
        for title, cmd in steps:
            print(f"{C_BOLD}{title}{C_RESET}: {C_YELLOW}{cmd}{C_RESET}")
        print(f"\nСовет: Используй Tab (в реале) и стрелки для истории. У нас история работает: нажми вверх? Пока через команду history")

    def cmd_man(self, args):
        if not args:
            print("Usage: man <command>")
            return
        cmd=args[0]
        mans={
            "ls": "ls [path] [-l] [-a] - список файлов. Пример: ls /, ls -l /home",
            "cd": "cd [path] - сменить каталог. cd .. - назад, cd / - в корень, cd без аргументов в /home/user",
            "cat": "cat <file1> [file2...] - показать содержимое. Поддерживает несколько файлов",
            "echo": "echo <text> [> file] [>> file] - вывод. Поддержка редиректа > и >>",
            "grep": "grep <pattern> <file> - поиск. Пример: grep hello /readme.txt, grep -r hello /",
            "jdb": "jdb set <k> <v> | get <k> | del <k> | list | clear | incr <k> | info - встроенная база",
            "server": "server start|stop|status|restart|logs|reload - управление веб сервером FullStack на :80",
            "find": "find [path] [-name pattern] [-type f|d] [-grep text] - поиск файлов",
            "calc": "calc <expr> - калькулятор. Пример: calc 2+2*2, calc sin(0.5)+sqrt(16)",
            "edit": "edit <file> - простой построчный редактор. Пиши строки, '.' alone или Ctrl+D - сохранить, ':q!' - выйти без сохранения",
            "tree": "tree [path] - дерево каталогов",
        }
        print(mans.get(cmd, f"No manual for {cmd}. Try help or cmds"))

    # FS COMMANDS
    def cmd_ls(self, args):
        path="."
        show_all=False
        long=False
        # parse flags
        filtered=[]
        for a in args:
            if a.startswith("-"):
                if "a" in a: show_all=True
                if "l" in a: long=True
            else:
                filtered.append(a)
        if filtered: path=filtered[0]
        abs_path=self.fs.norm(path)
        listing=self.fs.list_dir(abs_path)
        if listing is None:
            # maybe file?
            s=self.fs.stat(abs_path)
            if s and s["type"]=="file":
                if long:
                    print(f"{s['perms']} {s['size']:>6} {time.strftime('%Y-%m-%d %H:%M', time.localtime(s['mtime']))} {os.path.basename(abs_path)}")
                else:
                    print(os.path.basename(abs_path))
                return
            print(f"{C_RED}ls: {path}: No such file or directory{C_RESET}")
            return
        dirs, files = listing
        if not show_all:
            dirs=[d for d in dirs if not d.startswith(".")]
            files=[f for f in files if not f.startswith(".")]
        if long:
            print(f"total {len(dirs)+len(files)} in {abs_path}")
            for d in dirs:
                st=self.fs.stat(abs_path.rstrip("/")+"/"+d)
                if st:
                    print(f"{C_BLUE}d{C_RESET} {st['perms']} {4096:>6} {time.strftime('%b %d %H:%M', time.localtime(st['mtime']))} {C_BLUE}{d}/{C_RESET}")
                else:
                    print(f"{C_BLUE}{d}/{C_RESET}")
            for f in files:
                fp=abs_path.rstrip("/")+"/"+f
                st=self.fs.stat(fp)
                if st:
                    print(f"- {st['perms']} {st['size']:>6} {time.strftime('%b %d %H:%M', time.localtime(st['mtime']))} {f}")
        else:
            # column view
            all_items=[f"{C_BLUE}{d}/{C_RESET}" for d in dirs] + files
            if all_items:
                # print in rows
                for item in all_items:
                    print(item + "  ", end="")
                print()
            else:
                if show_all or long:
                    print(f"(empty) {abs_path}")
                else:
                    print(f"(empty) use ls -a")

    def cmd_pwd(self, args):
        print(self.fs.cwd)

    def cmd_cd(self, args):
        if not args:
            self.fs.cwd="/home/user"
            self.env["PWD"]=self.fs.cwd
            return
        target=args[0]
        if target=="..":
            # up
            if self.fs.cwd!="/":
                self.fs.cwd=os.path.dirname(self.fs.cwd.rstrip("/")) or "/"
                if self.fs.cwd=="": self.fs.cwd="/"
            self.env["PWD"]=self.fs.cwd
            return
        if target=="-":
            # previous? stub
            print(self.fs.cwd)
            return
        new_path=self.fs.norm(target)
        # check exists: dir or has children
        if new_path in self.fs.dirs:
            self.fs.cwd=new_path
        elif new_path in self.fs.files:
            print(f"{C_RED}cd: {target}: Not a directory{C_RESET}")
            return
        else:
            # check if prefix has files
            if any(f.startswith(new_path+"/") for f in self.fs.files) or any(d.startswith(new_path+"/") for d in self.fs.dirs):
                self.fs.ensure_dir(new_path)
                self.fs.cwd=new_path
            else:
                # try relative?
                print(f"{C_RED}cd: {target}: No such file or directory{C_RESET}")
                return
        self.env["PWD"]=self.fs.cwd

    def cmd_cat(self, args):
        if not args:
            print("Usage: cat <file> [file...]")
            return
        out_lines=[]
        for p in args:
            content=self.fs.read(p)
            if content is None:
                # try wildcard?
                # if pattern contains * search
                if "*" in p:
                    pat=p.replace("*",".*")
                    regex=re.compile(pat)
                    found=False
                    for fpath in self.fs.files:
                        if regex.search(fpath):
                            out_lines.append(f"==> {fpath} <==")
                            out_lines.append(self.fs.files[fpath]["content"])
                            found=True
                    if not found:
                        print(f"{C_RED}cat: {p}: No such file{C_RESET}")
                else:
                    print(f"{C_RED}cat: {p}: No such file{C_RESET}")
            else:
                out_lines.append(content)
        if out_lines:
            print("\n".join(out_lines))

    def cmd_bat(self, args):
        if not args: print("Usage: bat <file>"); return
        for p in args:
            content=self.fs.read(p)
            if content is None:
                print(f"No such file {p}")
            else:
                lines=content.splitlines()
                for i, line in enumerate(lines,1):
                    print(f"{C_DIM}{i:4} |{C_RESET} {line}")

    def cmd_touch(self, args):
        if not args:
            print("Usage: touch <file>...")
            return
        for p in args:
            ap=self.fs.norm(p)
            if self.fs.is_file(ap):
                # update mtime
                self.fs.files[ap]["mtime"]=time.time()
                print(f"touched {p}")
            else:
                self.fs.write(ap, "")
                print(f"Created {p}")

    def cmd_mkdir(self, args):
        if not args:
            print("Usage: mkdir <dir>...")
            return
        for p in args:
            ok, msg=self.fs.mkdir(p)
            if ok:
                print(f"mkdir {msg}")
            else:
                print(f"{C_RED}mkdir: {msg}: {p}{C_RESET}")

    def cmd_rmdir(self, args):
        if not args:
            print("Usage: rmdir <dir>")
            return
        for p in args:
            ok, msg=self.fs.rmdir(p)
            if not ok:
                print(f"{C_RED}rmdir: {p}: {msg}{C_RESET}")
            else:
                print(f"Removed {p}")

    def cmd_rm(self, args):
        if not args:
            print("Usage: rm [-r] <file|dir>...")
            return
        recursive=False
        targets=[]
        for a in args:
            if a in ("-r","-rf","-f","-fr","-R"):
                recursive=True
            else:
                targets.append(a)
        for p in targets:
            ap=self.fs.norm(p)
            if self.fs.is_file(ap):
                self.fs.rm(ap)
                print(f"Removed {ap}")
            elif self.fs.is_dir(ap):
                if recursive:
                    # remove all
                    to_del_files=[f for f in self.fs.files if f==ap or f.startswith(ap+"/")]
                    for f in to_del_files: del self.fs.files[f]
                    to_del_dirs=[d for d in self.fs.dirs if d==ap or d.startswith(ap+"/")]
                    for d in to_del_dirs:
                        if d in self.fs.dirs: self.fs.dirs.remove(d)
                    self.fs.dirs.add("/") # ensure root
                    print(f"Removed dir {ap} recursively")
                    self.fs.save_persist()
                else:
                    print(f"{C_RED}rm: {p}: is directory (use rm -r){C_RESET}")
            else:
                print(f"{C_RED}rm: {p}: No such file{C_RESET}")

    def cmd_cp(self, args):
        if len(args)<2:
            print("Usage: cp <src> <dst>")
            return
        src=args[0]; dst=args[1]
        ok, msg=self.fs.cp(src,dst)
        if ok:
            print(f"Copied to {msg}")
        else:
            print(f"{C_RED}cp: {msg}{C_RESET}")

    def cmd_mv(self, args):
        if len(args)<2:
            print("Usage: mv <src> <dst>")
            return
        src=args[0]; dst=args[1]
        ok, msg=self.fs.mv(src,dst)
        if ok:
            print(f"Moved to {msg}")
        else:
            print(f"{C_RED}mv: {msg}{C_RESET}")

    def cmd_ren(self, args):
        self.cmd_mv(args)

    def cmd_find(self, args):
        # find [path] -name pattern -type f -grep text
        path="/"
        name_pat=None
        grep_pat=None
        type_filter=None
        i=0
        while i < len(args):
            a=args[i]
            if a=="-name" and i+1<len(args):
                name_pat=args[i+1]; i+=2; continue
            if a=="-grep" and i+1<len(args):
                grep_pat=args[i+1]; i+=2; continue
            if a=="-type" and i+1<len(args):
                type_filter=args[i+1]; i+=2; continue
            if not a.startswith("-"):
                path=a
            i+=1
        path=self.fs.norm(path)
        results=[]
        for fpath, fdata in self.fs.files.items():
            if not fpath.startswith(path): continue
            if name_pat:
                # Convert simple glob to regex
                pat=name_pat.replace(".","\\.").replace("*",".*")
                if not re.search(pat, os.path.basename(fpath)):
                    continue
            if type_filter=="d": continue
            if grep_pat and grep_pat not in fdata["content"]:
                continue
            results.append(fpath)
        if type_filter!="f":
            for d in self.fs.dirs:
                if not d.startswith(path): continue
                if name_pat:
                    pat=name_pat.replace(".","\\.").replace("*",".*")
                    if not re.search(pat, os.path.basename(d)):
                        continue
                results.append(d+"/")
        for r in sorted(results):
            print(r)
        print(f"{C_DIM}Found {len(results)} entries{C_RESET}")

    def cmd_tree(self, args):
        path=self.fs.norm(args[0] if args else self.fs.cwd)
        def print_tree(cur_path, prefix=""):
            dirs, files = self.fs.list_dir(cur_path) or ([],[])
            all_items = [(d, True) for d in dirs] + [(f, False) for f in files]
            for idx, (name, is_dir) in enumerate(all_items):
                last = idx==len(all_items)-1
                connector = "└── " if last else "├── "
                print(prefix + connector + (f"{C_BLUE}{name}/{C_RESET}" if is_dir else name))
                if is_dir:
                    new_path = cur_path.rstrip("/") + "/" + name
                    new_prefix = prefix + ("    " if last else "│   ")
                    print_tree(new_path, new_prefix)
        print(path)
        print_tree(path)

    def cmd_du(self, args):
        path=self.fs.norm(args[0] if args else self.fs.cwd)
        total=0
        for fpath, fdata in self.fs.files.items():
            if fpath.startswith(path):
                total+=len(fdata["content"])
        print(f"{total} bytes\t{path} ({total/1024:.1f} KB)")

    def cmd_df(self, args):
        total=32*1024*1024
        used=sum(len(d["content"]) for d in self.fs.files.values()) + len(self.fs.dirs)*4096
        free=total-used
        print(f"Filesystem  Size   Used  Free  Use% Mounted")
        print(f"JinoFS        32M  {used//1024}K  {free//1024}K  {used*100//total}%  /")
        print(f"Files: {len(self.fs.files)}  Dirs: {len(self.fs.dirs)}")

    def cmd_stat(self, args):
        if not args: print("Usage: stat <file>"); return
        for p in args:
            s=self.fs.stat(p)
            if not s:
                print(f"{C_RED}stat: {p}: No such{C_RESET}")
            else:
                print(f"File: {s['path']}\nSize: {s['size']}  Type: {s['type']}  Perms: {s['perms']}\nModify: {time.ctime(s['mtime'])}")

    def cmd_chmod(self, args):
        if len(args)<2: print("Usage: chmod <perms> <file>"); return
        perms=args[0]; fpath=self.fs.norm(args[1])
        if fpath in self.fs.files:
            self.fs.files[fpath]["perms"]=perms
            print(f"chmod {perms} {fpath}")
        else:
            print("Not found")

    # TEXT PROCESSING
    def cmd_echo(self, args, raw_line, redir_out, redir_append):
        # raw_line may have quotes, we already parsed? Use original raw_line after echo
        # Find after echo
        m=re.search(r'echo\s+(.*)', raw_line, re.IGNORECASE)
        text=m.group(1) if m else " ".join(args)
        # Strip redirection already done? parse removed
        # Handle > already handled via redir params?
        # If text contains $VAR expand
        for k,v in self.env.items():
            text=text.replace(f"${k}", v).replace(f"${{{k}}}", v)
        self.output(text, redir_out, redir_append)

    def cmd_printf(self, args):
        if not args: return
        fmt=args[0]
        # very simple %s substitution
        vals=args[1:]
        try:
            # replace \n
            fmt=fmt.encode().decode('unicode_escape')
            if vals:
                print(fmt % tuple(vals))
            else:
                print(fmt, end="")
        except Exception as e:
            print(fmt)

    def cmd_write(self, args):
        if not args:
            print("Usage: write <file>")
            return
        path=args[0]
        existing=self.fs.read(path)
        print(f"Writing to {path} (existing {len(existing) if existing else 0}b). Enter lines, '.' alone or ':wq' to save, ':q!' to abort, Ctrl+D also saves:")
        lines=[]
        try:
            while True:
                line=input(f"{C_DIM}{len(lines)+1:3}> {C_RESET}")
                if line=="." or line==":wq" or line==":x":
                    break
                if line==":q!":
                    print("Abort")
                    return
                lines.append(line)
        except EOFError:
            pass
        content="\n".join(lines)
        self.fs.write(path, content)
        print(f"{C_GREEN}Saved {len(content)} bytes to {path}{C_RESET}")

    def cmd_edit(self, args):
        self.cmd_write(args)

    def cmd_head(self, args):
        if not args: print("Usage: head [-n N] <file>"); return
        n=10
        files=[]
        i=0
        while i < len(args):
            if args[i]=="-n" and i+1<len(args):
                n=int(args[i+1]); i+=2; continue
            if args[i].startswith("-") and args[i][1:].isdigit():
                n=int(args[i][1:]); i+=1; continue
            files.append(args[i]); i+=1
        for p in files:
            content=self.fs.read(p)
            if content is None:
                print(f"No file {p}"); continue
            lines=content.splitlines()[:n]
            print("\n".join(lines))

    def cmd_tail(self, args):
        n=10
        files=[]
        i=0
        while i < len(args):
            if args[i]=="-n" and i+1<len(args):
                n=int(args[i+1]); i+=2; continue
            files.append(args[i]); i+=1
        for p in files:
            content=self.fs.read(p)
            if content is None: continue
            lines=content.splitlines()[-n:]
            print("\n".join(lines))

    def cmd_wc(self, args):
        total_l=total_w=total_c=0
        targets=args or []
        if not targets:
            print("Usage: wc <file>...")
            return
        for p in targets:
            content=self.fs.read(p)
            if content is None:
                print(f"{p}: no file"); continue
            l=len(content.splitlines()); w=len(content.split()); c=len(content)
            total_l+=l; total_w+=w; total_c+=c
            print(f"{l:4} {w:4} {c:6} {p}")
        if len(targets)>1:
            print(f"{total_l:4} {total_w:4} {total_c:6} total")

    def cmd_grep(self, args):
        if len(args)<1:
            print("Usage: grep [-r] [-i] <pattern> [file...]")
            return
        opts=[]
        pattern=None
        files=[]
        recursive=False
        ignore_case=False
        for a in args:
            if a.startswith("-"):
                if "r" in a: recursive=True
                if "i" in a: ignore_case=True
                continue
            if pattern is None:
                pattern=a
            else:
                files.append(a)
        if not pattern:
            print("No pattern"); return
        flags=re.IGNORECASE if ignore_case else 0
        try:
            regex=re.compile(pattern, flags)
        except:
            regex=re.compile(re.escape(pattern), flags)
        if not files:
            files=[self.fs.cwd]
        matched=0
        for fpath_arg in files:
            ap=self.fs.norm(fpath_arg)
            # if dir and recursive, search all
            if ap in self.fs.dirs or (recursive and self.fs.is_dir(ap)):
                for fpath, fdata in self.fs.files.items():
                    if fpath.startswith(ap):
                        for i, line in enumerate(fdata["content"].splitlines(),1):
                            if regex.search(line):
                                print(f"{C_GREEN}{fpath}:{i}:{C_RESET}{line}")
                                matched+=1
            else:
                content=self.fs.read(ap)
                if content is None:
                    print(f"grep: {fpath_arg}: no file")
                    continue
                for i, line in enumerate(content.splitlines(),1):
                    if regex.search(line):
                        if len(files)>1:
                            print(f"{ap}:{i}:{line}")
                        else:
                            print(line)
                        matched+=1
        print(f"{C_DIM}{matched} matches{C_RESET}")

    def cmd_sort(self, args):
        if not args:
            # read stdin simulation: ask input?
            print("Usage: sort <file>")
            return
        p=args[0]
        content=self.fs.read(p)
        if content is None:
            print("No file"); return
        lines=content.splitlines()
        lines_sorted=sorted(lines)
        print("\n".join(lines_sorted))

    def cmd_uniq(self, args):
        if not args:
            print("Usage: uniq <file>")
            return
        content=self.fs.read(args[0])
        if content is None: return
        lines=content.splitlines()
        uniq=[]
        prev=None
        for l in lines:
            if l!=prev:
                uniq.append(l)
            prev=l
        print("\n".join(uniq))

    def cmd_cut(self, args):
        # cut -d : -f 1 file
        delim="\t"
        field=1
        file=None
        i=0
        while i < len(args):
            if args[i]=="-d" and i+1<len(args):
                delim=args[i+1]; i+=2; continue
            if args[i]=="-f" and i+1<len(args):
                field=int(args[i+1]); i+=2; continue
            file=args[i]; i+=1
        if not file:
            print("Usage: cut -d <delim> -f <N> <file>")
            return
        content=self.fs.read(file)
        if content is None: return
        for line in content.splitlines():
            parts=line.split(delim)
            if 1<=field<=len(parts):
                print(parts[field-1])
            else:
                print(line)

    def cmd_hexdump(self, args):
        if not args:
            print("Usage: hexdump <file>")
            return
        content=self.fs.read(args[0])
        if content is None: return
        data=content.encode('utf-8', errors='ignore')
        for offset in range(0, len(data), 16):
            chunk=data[offset:offset+16]
            hexpart=" ".join(f"{b:02x}" for b in chunk)
            ascp="".join(chr(b) if 32<=b<127 else "." for b in chunk)
            print(f"{offset:08x}  {hexpart:<48} |{ascp}|")

    def cmd_base64(self, args):
        if not args:
            print("Usage: base64 [-d] <file> or base64 <text>")
            return
        decode=False
        target=None
        for a in args:
            if a=="-d" or a=="--decode":
                decode=True
            else:
                target=a
        if target is None:
            print("Need arg"); return
        # try file, else text
        content=self.fs.read(target)
        if content is None:
            content=target
        if decode:
            try:
                dec=base64.b64decode(content).decode()
                print(dec)
            except Exception as e:
                print(f"decode error {e}")
        else:
            enc=base64.b64encode(content.encode()).decode()
            print(enc)

    def cmd_strings(self, args):
        if not args: print("Usage: strings <file>"); return
        content=self.fs.read(args[0]) or ""
        # find printable strings >=4
        strs=re.findall(r'[ -~]{4,}', content)
        for s in strs:
            print(s)

    def cmd_diff(self, args):
        if len(args)<2:
            print("Usage: diff <file1> <file2>")
            return
        c1=self.fs.read(args[0]) or ""
        c2=self.fs.read(args[1]) or ""
        l1=c1.splitlines(); l2=c2.splitlines()
        max_len=max(len(l1),len(l2))
        for i in range(max_len):
            a=l1[i] if i < len(l1) else None
            b=l2[i] if i < len(l2) else None
            if a!=b:
                if a is None:
                    print(f"{C_GREEN}+ {b}{C_RESET}")
                elif b is None:
                    print(f"{C_RED}- {a}{C_RESET}")
                else:
                    print(f"{C_RED}- {a}{C_RESET}")
                    print(f"{C_GREEN}+ {b}{C_RESET}")

    # SYSTEM
    def cmd_ver(self, args):
        print(f"{C_BOLD}Jino OS {VERSION}{C_RESET}")
        print(f"Kernel: JinoKernel 1.0 Console (DOS-compat + Unix tools)")
        print(f"Build: {BUILD}")
        print(f"FS: JinoFS v2 (in-mem, {len(self.fs.files)} files)")
        print(f"Shell: JinoSH 1.0 with 80+ commands")
        print(f"Mode: NO GUI, Console Only")

    def cmd_uname(self, args):
        flags=args[0] if args else "-a"
        if flags=="-a":
            print(f"JinoOS jino-pc 1.0-CONSOLE i386 JinoKernel {BUILD} GNU/Jino")
        elif flags=="-r":
            print("1.0-CONSOLE")
        elif flags=="-m":
            print("i386")
        else:
            print("JinoOS")

    def cmd_whoami(self, args):
        print(self.env["USER"])

    def cmd_hostname(self, args):
        if args:
            self.env["HOST"]=args[0]
            self.jdb["hostname"]=args[0]
            print(f"Hostname set to {args[0]}")
        else:
            print(self.env["HOST"])

    def cmd_date(self, args):
        print(datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y - Jino Time"))

    def cmd_time(self, args):
        print(time.strftime("%H:%M:%S"))

    def cmd_cal(self, args):
        # simple calendar
        import calendar
        now=datetime.datetime.now()
        month=now.month; year=now.year
        if args:
            try:
                if len(args)>=1: month=int(args[0])
                if len(args)>=2: year=int(args[1])
            except: pass
        print(calendar.month(year, month))

    def cmd_clear(self, args):
        os.system("clear||cls")
        # also ANSI clear
        print("\033[2J\033[H", end="")

    def cmd_history(self, args):
        for i, h in enumerate(self.history[-100:],1):
            print(f"{i:4}  {h}")
        print(f"{C_DIM}Total {len(self.history)}{C_RESET}")

    def cmd_env(self, args):
        for k,v in self.env.items():
            print(f"{k}={v}")

    def cmd_set(self, args):
        if not args:
            self.cmd_env(args)
            return
        for a in args:
            if "=" in a:
                k,v=a.split("=",1)
                self.env[k]=v
                print(f"{k}={v}")
            else:
                print(f"{a}={self.env.get(a,'')}")

    def cmd_export(self, args):
        self.cmd_set(args)

    def cmd_unset(self, args):
        for k in args:
            if k in self.env:
                del self.env[k]
                print(f"Unset {k}")

    def cmd_alias(self, args):
        if not args:
            for k,v in self.aliases.items():
                print(f"alias {k}='{v}'")
            return
        # parse alias name='value'
        raw=" ".join(args)
        if "=" in raw:
            name, val = raw.split("=",1)
            name=name.strip()
            val=val.strip().strip("'\"")
            self.aliases[name]=val
            print(f"Alias {name}='{val}'")
        else:
            name=raw.strip()
            if name in self.aliases:
                print(f"{name}='{self.aliases[name]}'")
            else:
                print(f"No alias {name}")

    def cmd_mem(self, args):
        total=32*1024*1024
        used= sum(len(d["content"]) for d in self.fs.files.values()) + 2*1024*1024
        free=total-used
        print(f"MemTotal:       {total//1024} kB (32 MB)")
        print(f"MemUsed:        {used//1024} kB")
        print(f"MemFree:        {free//1024} kB")
        print(f"MemAvailable:   {free//1024} kB")
        print(f"Buffers:        128 kB")
        print(f"Cached:         256 kB")
        print(f"JinoFS files: {len(self.fs.files)} using {used//1024} kB")

    def cmd_ps(self, args):
        print(f"{'PID':<6} {'NAME':<15} {'CPU':<6} {'MEM':<6} {'TIME'}")
        for p in self.processes:
            up=int(time.time()-self.uptime_start)
            print(f"{p['pid']:<6} {p['name']:<15} {p['cpu']:<6} {p['mem']:<6} {up}s")

    def cmd_top(self, args):
        # snapshot
        print(f"top - {time.strftime('%H:%M:%S')} up {int((time.time()-self.uptime_start)//60)} min, 1 user, load avg: 0.12, 0.08, 0.05")
        print(f"Tasks: {len(self.processes)} total")
        print(f"%Cpu(s):  2.3 us,  1.1 sy,  96.6 id")
        print(f"MiB Mem : 32.000 total, {32 - len(self.fs.files)*0.01:.1f} free, 2.0 used")
        self.cmd_ps(args)

    def cmd_uptime(self, args):
        up=int(time.time()-self.uptime_start)
        h=up//3600; m=(up%3600)//60; s=up%60
        print(f" {time.strftime('%H:%M:%S')} up {h}:{m:02}:{s:02}, 1 user, load 0.12")

    def cmd_sysinfo(self, args):
        print(f"""{C_BOLD}System Info - Jino OS{C_RESET}
OS: Jino OS {VERSION}
Kernel: JinoKernel 1.0 (Console)
Arch: i386 32-bit
CPU: Genuine JinoCPU 100MHz (simulated) x1
Memory: 32 MB RAM, {len(self.fs.files)} files loaded
Disk: JinoFS v2 on / - {len(self.fs.dirs)} dirs
Uptime: {int(time.time()-self.uptime_start)} sec
Hostname: {self.env['HOST']}
User: {self.env['USER']}
Shell: JinoSH 1.0
Mode: CONSOLE ONLY (GUI removed per request)
Packages: FullStack (JinoServer + JinoDB)
""")

    def cmd_cpuinfo(self, args):
        print("""processor : 0
vendor_id : GenuineJino
cpu family : 5
model : Jino 586
model name : JinoCPU 100MHz Console Edition
cpu MHz : 100.000
cache size : 16 KB
bogomips : 50.00
flags : fpu vme de pse tsc msr mce cx8
""")

    def cmd_sleep(self, args):
        if not args: return
        try:
            t=float(args[0])
            print(f"Sleep {t}s...")
            time.sleep(t)
        except: pass

    # NETWORK / FULLSTACK
    def cmd_ping(self, args):
        if not args:
            print("Usage: ping <host>")
            return
        host=args[0]
        print(f"PING {host} (127.0.0.1) 56(84) bytes of data.")
        for i in range(4):
            print(f"64 bytes from {host}: icmp_seq={i+1} ttl=64 time={random.uniform(0.5, 20):.2f} ms")
            time.sleep(0.3)
        print(f"--- {host} ping statistics ---")
        print(f"4 packets transmitted, 4 received, 0% loss")

    def cmd_ifconfig(self, args):
        print(f"""lo: flags=73<UP,LOOPBACK,RUNNING> mtu 65536
        inet 127.0.0.1 netmask 255.0.0.0
        loop txqueuelen 1000

eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST> mtu 1500
        inet 192.168.1.100 netmask 255.255.255.0 broadcast 192.168.1.255
        ether 00:1A:2B:3C:4D:5E (JinoNIC)
        RX packets 1234 bytes 1.2 MB
        TX packets 567 bytes 800 KB
        JinoNet driver v1.0 console
""")

    def cmd_curl(self, args):
        if not args:
            print("Usage: curl <url>")
            return
        url=args[0]
        # if file in /www, serve
        if "localhost" in url or "jino" in url:
            path="/www/index.html"
            if "/" in url.split("//")[-1]:
                # extract path after host
                try:
                    p="/"+url.split("/",3)[-1]
                    if p and self.fs.read(p):
                        path=p
                    elif self.fs.read("/www/"+url.split("/")[-1]):
                        path="/www/"+url.split("/")[-1]
                except: pass
            content=self.fs.read(path)
            if content:
                print(content)
            else:
                print(f"<h1>JinoServer: 404 {url} not found</h1>")
        else:
            print(f"{C_DIM}Simulated curl to {url} - JinoNet fetch (offline mode):{C_RESET}")
            print(f"<html><body>Simulated response from {url}<br>Fetched by JinoOS curl 1.0</body></html>")

    def cmd_wget(self, args):
        if not args:
            print("Usage: wget <url> [-O file]")
            return
        url=args[0]
        out=None
        if "-O" in args:
            idx=args.index("-O")
            if idx+1 < len(args):
                out=args[idx+1]
        if not out:
            out="/tmp/"+url.split("/")[-1] or "index.html"
        # fetch via curl logic
        content=f"Downloaded from {url} at {time.ctime()}\nSimulated by Jino wget\n"
        # if local
        if "localhost" in url:
            local=self.fs.read("/www/index.html") or ""
            content=local
        self.fs.write(out, content)
        print(f"Saved to {out} ({len(content)} bytes)")

    def cmd_server(self, args):
        if not args:
            print("Usage: server start|stop|status|restart|logs|reload")
            return
        sub=args[0]
        if sub=="start":
            if self.server_running:
                print("Server already running on :80")
            else:
                self.server_running=True
                print(f"{C_GREEN}[JinoServer] Started on :{self.server_port} serving /www{C_RESET}")
                print(f"[JinoServer] Files: {', '.join([f for f in self.fs.files if f.startswith('/www/')])}")
                print(f"[JinoServer] http://localhost:{self.server_port}/ -> /www/index.html")
                print(f"[JinoServer] http://jino.local/api/jdb -> JinoDB")
        elif sub=="stop":
            self.server_running=False
            print("[JinoServer] Stopped")
        elif sub=="status":
            status="RUNNING" if self.server_running else "STOPPED"
            print(f"JinoServer :{self.server_port} - {status}")
            print(f"Root: /www, Files: {len([f for f in self.fs.files if f.startswith('/www/')])}")
            print(f"DB keys: {len(self.jdb)}")
        elif sub=="restart":
            self.server_running=False
            time.sleep(0.5)
            self.server_running=True
            print("[JinoServer] Restarted")
        elif sub=="logs":
            print(f"[LOG] {time.ctime()} GET / -> 200")
            print(f"[LOG] {time.ctime()} GET /api/jdb -> 200 (keys={len(self.jdb)})")
            print(f"[LOG] Server uptime {int(time.time()-self.uptime_start)}s")
        elif sub=="reload":
            print("[JinoServer] Reloaded /www")

    def cmd_jdb(self, args):
        if not args:
            print("Usage: jdb set <k> <v> | get <k> | del <k> | list | clear | incr <k> | decr <k> | info | export [file] | import <file> | keys")
            return
        op=args[0]
        if op=="set" and len(args)>=3:
            k=args[1]; v=" ".join(args[2:])
            self.jdb[k]=v
            # also persist in FS for fullstack
            self.fs.write(f"/db/{k}.json", json.dumps({"key":k,"value":v,"ts":time.time()}))
            print(f"OK {k} = {v}")
        elif op=="get" and len(args)>=2:
            k=args[1]
            print(self.jdb.get(k, f"(nil) key '{k}' not found"))
        elif op=="del" and len(args)>=2:
            k=args[1]
            if k in self.jdb:
                del self.jdb[k]
                if self.fs.is_file(f"/db/{k}.json"):
                    self.fs.rm(f"/db/{k}.json")
                print(f"Deleted {k}")
            else:
                print(f"No key {k}")
        elif op=="list":
            if not self.jdb:
                print("(empty)")
            for k,v in self.jdb.items():
                print(f"{C_CYAN}{k}{C_RESET} = {v}")
        elif op=="keys":
            print(", ".join(self.jdb.keys()))
        elif op=="clear":
            self.jdb.clear()
            print("DB cleared")
        elif op=="incr" and len(args)>=2:
            k=args[1]
            try:
                val=int(self.jdb.get(k,"0"))
                val+=1
                self.jdb[k]=str(val)
                print(val)
            except:
                print("Not int")
        elif op=="decr" and len(args)>=2:
            k=args[1]
            try:
                val=int(self.jdb.get(k,"0"))
                val-=1
                self.jdb[k]=str(val)
                print(val)
            except:
                print("Not int")
        elif op=="info":
            print(f"JinoDB: {len(self.jdb)} keys, in-mem + /db persisted")
            print(f"File: /db/*.json")
        elif op=="export":
            target=args[1] if len(args)>=2 else "/tmp/jdb_export.json"
            data=json.dumps(self.jdb, indent=2)
            self.fs.write(target, data)
            print(f"Exported {len(self.jdb)} keys to {target}")
        elif op=="import" and len(args)>=2:
            content=self.fs.read(args[1])
            if content:
                try:
                    obj=json.loads(content)
                    self.jdb.update(obj)
                    print(f"Imported {len(obj)} keys")
                except Exception as e:
                    print(f"Error {e}")
            else:
                print("File not found")
        else:
            print("Usage: jdb set/get/del/list/clear/incr/decr/info/export/import/keys")

    # DEV / FUN
    def cmd_calc(self, args):
        if not args:
            print("Usage: calc <expr> - e.g. calc 2+2*2, calc sqrt(16)+sin(0)")
            return
        expr=" ".join(args)
        # safe eval with math
        allowed={"sin":math.sin,"cos":math.cos,"tan":math.tan,"sqrt":math.sqrt,"log":math.log,"exp":math.exp,"pi":math.pi,"e":math.e,"pow":pow,"abs":abs,"ceil":math.ceil,"floor":math.floor}
        # replace ^ with **
        expr=expr.replace("^","**")
        try:
            result=eval(expr, {"__builtins__": {}}, allowed)
            print(f"{C_GREEN}{result}{C_RESET}")
            self.last_exit_code=0
            self.jdb["last_calc"]=str(result)
        except Exception as e:
            print(f"{C_RED}calc error: {e}{C_RESET}")

    def cmd_run(self, args):
        if not args:
            print("Usage: run <file.japp|.jino>")
            return
        path=args[0]
        content=self.fs.read(path)
        if content is None:
            print(f"run: {path}: No such file")
            return
        print(f"{C_CYAN}[JinoScript] Running {path}...{C_RESET}")
        # simple interpreter: lines
        lines=content.splitlines()
        for line in lines:
            l=line.strip()
            if not l or l.startswith("#") or l.startswith("//"):
                continue
            if l.startswith("print("):
                inner=l[6:-1].strip().strip("'\"")
                # expand vars
                for k,v in self.jdb.items():
                    inner=inner.replace(f"{{{k}}}", v)
                    inner=inner.replace(f"${k}", v)
                print(inner)
            elif "window.create" in l:
                # would be GUI, but now console: simulate
                m=re.search(r'window\.create\((.*?)\)', l)
                if m:
                    print(f"{C_YELLOW}[GUI-REMOVED] window.create ignored in console mode, args: {m.group(1)}{C_RESET}")
                    print(f"{C_DIM}Use echo or server instead{C_RESET}")
            elif l.startswith("server.route"):
                print(f"{C_GREEN}[SERVER] Route registered: {l}{C_RESET}")
            elif "db.set" in l or "db.get" in l:
                print(f"{C_MAGENTA}[DB] {l}{C_RESET}")
                # simulate simple
                if "db.set" in l:
                    mm=re.search(r'db\.set\(\s*["\'](.*?)["\']\s*,\s*(.*?)\)', l)
                    if mm:
                        kk=mm.group(1); vv=mm.group(2).strip().strip("\"'")
                        self.jdb[kk]=vv
                        print(f"  -> JinoDB {kk}={vv}")
            elif l.startswith("echo "):
                print(l[5:])
            else:
                print(f"{C_DIM}[exec] {l}{C_RESET}")
        print(f"{C_GREEN}[JinoScript] Done{C_RESET}")

    def cmd_cowsay(self, args):
        text=" ".join(args) if args else "Jino OS 1.0 Console - Moo!"
        bubble_len=len(text)+2
        print(f" {'_'*bubble_len}")
        print(f"< {text} >")
        print(f" {'-'*bubble_len}")
        print(r"""        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
        """)

    def cmd_fortune(self, args):
        fortunes=[
            "Jino OS - No GUI, no problem, only power.",
            "DOS is not dead, it lives in Jino.",
            "Console is the real GUI for hackers.",
            "In Jino we trust: Files, DB, Server - all in one.",
            "rm -rf / - just kidding, JinoFS is safe.",
            "Write code, not windows.",
            "Jino 1.0: 80+ commands, zero graphics, infinite possibilities.",
            "Jino OS spreading worldwide.",
        ]
        print(random.choice(fortunes))

    def cmd_banner(self, args):
        text=" ".join(args) if args else "JINO"
        # simple big ascii
        print(f"{C_CYAN}{C_BOLD}")
        print(f"  #   #  ###  #   #   ###     ###    ###")
        print(f"  #   #   #   ##  #  #   #   #   #  #")
        print(f"  #####   #   # # #  #   #   #   #   ##")
        print(f"  #   #   #   #  ##  #   #   #   #     #")
        print(f"  #   #  ###  #   #   ###     ###   ###")
        print(f"  {text}")
        print(C_RESET)

    def cmd_figlet(self, args):
        text=" ".join(args) if args else "Jino"
        # simple figlet simulation
        print(f"{C_GREEN}")
        for c in text.upper():
            print(f"[{c}] ", end="")
        print("\n" + C_RESET + text)

    def cmd_matrix(self, args):
        print(f"{C_GREEN}Entering Matrix... Ctrl+C to exit{C_RESET}")
        chars="01JINOS"
        try:
            for _ in range(30):
                line="".join(random.choice(chars) + " " for _ in range(40))
                print(f"{C_GREEN}{line}{C_RESET}")
                time.sleep(0.08)
        except KeyboardInterrupt:
            print(f"{C_RESET}Matrix stopped")

    def cmd_snake(self, args):
        print(f"{C_YELLOW}Jino Snake - Console Edition{C_RESET}")
        print("Use WASD to move, Q to quit. Eating @ . Simple version.")
        # very mini snake without curses - just grid board simulation with input per move
        w,h=12,8
        snake=[(5,4)]
        dir=(1,0)
        food=(random.randint(0,w-1), random.randint(0,h-1))
        score=0
        # we can't have realtime keyboard without curses, so turn-based
        while True:
            # draw
            print("\033[2J\033[H", end="")
            print(f"Score {score} - WASD move, Q quit - Snake len {len(snake)}")
            for y in range(h):
                row=""
                for x in range(w):
                    if (x,y) in snake:
                        row+="O"
                    elif (x,y)==food:
                        row+="@"
                    else:
                        row+="."
                print(row)
            move=input("Move (w/a/s/d/q): ").lower().strip()
            if move=="q": break
            if move=="w": dir=(0,-1)
            elif move=="s": dir=(0,1)
            elif move=="a": dir=(-1,0)
            elif move=="d": dir=(1,0)
            else: continue
            new_head=(snake[0][0]+dir[0], snake[0][1]+dir[1])
            if not (0<=new_head[0]<w and 0<=new_head[1]<h):
                print("Wall hit! Game over"); break
            if new_head in snake:
                print("Self hit! Game over"); break
            snake.insert(0,new_head)
            if new_head==food:
                score+=1
                food=(random.randint(0,w-1), random.randint(0,h-1))
                while food in snake:
                    food=(random.randint(0,w-1), random.randint(0,h-1))
            else:
                snake.pop()
        print(f"Final score {score}")

    def cmd_tetris(self, args):
        print(f"{C_CYAN}Tetris in Jino? Simulated!{C_RESET}")
        print("Blocks falling... (simulation)")
        board=[[0]*10 for _ in range(10)]
        for _ in range(5):
            # add random blocks
            for _ in range(3):
                x=random.randint(0,9); y=random.randint(0,9)
                board[y][x]=1
            for row in board:
                print("".join("■" if c else "." for c in row))
            print("-----")
            time.sleep(0.5)
        print("Game over - use real device for full Tetris, this is console demo")

    def cmd_motd(self, args):
        motd=self.fs.read("/system/motd.txt") or "No MOTD"
        print(motd)

    # ADDITIONAL SMALL COMMANDS
    def cmd_more(self, args):
        if not args: return
        content=self.fs.read(args[0])
        if not content: print("No file"); return
        lines=content.splitlines()
        per_page=20
        for i in range(0,len(lines),per_page):
            print("\n".join(lines[i:i+per_page]))
            if i+per_page < len(lines):
                inp=input(f"--More-- {i+per_page}/{len(lines)} (q to quit, Enter next)")
                if inp.lower()=="q":
                    break

    def cmd_rev(self, args):
        if not args: print("Usage: rev <file>"); return
        c=self.fs.read(args[0]) or ""
        for line in c.splitlines():
            print(line[::-1])

    def cmd_truncate(self, args):
        if len(args)<2: print("Usage: truncate -s <size> <file>"); return
        # simple: truncate size
        size=0
        file=args[-1]
        for i,a in enumerate(args):
            if a=="-s" and i+1 < len(args):
                size=int(args[i+1])
        content=self.fs.read(file) or ""
        if len(content)>size:
            content=content[:size]
        else:
            content=content.ljust(size, "\0")
        self.fs.write(file, content)
        print(f"Truncated {file} to {size}")

    def cmd_tee(self, args):
        # tee file - read from stdin? simulate input
        if not args: print("Usage: tee <file>"); return
        print("Enter lines, Ctrl+D to end:")
        lines=[]
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        content="\n".join(lines)
        for f in args:
            self.fs.write(f, content)
            print(f"Wrote {len(content)} to {f}")
        print(content)

    def cmd_reboot(self, args):
        print(f"{C_YELLOW}Rebooting Jino OS...{C_RESET}")
        time.sleep(0.8)
        self.boot()

    def cmd_shutdown(self, args):
        print("Shutting down Jino OS...")
        print("Syncing JinoFS...")
        self.fs.save_persist()
        print("Power off")
        sys.exit(0)

    # DISPATCHER
    def dispatch(self, line):
        if not line.strip():
            return
        self.history.append(line)
        if len(self.history)>500:
            self.history=self.history[-500:]

        # handle $?
        if line.strip()=="echo $?":
            print(self.last_exit_code)
            return

        parts, redir_out, redir_append = self.parse(line)
        if not parts:
            return
        cmd=parts[0].lower()
        args=parts[1:]
        raw=line

        # map aliases variations
        # FS
        if cmd in ("ls","dir","ll","la","l"):
            self.cmd_ls(args)
        elif cmd=="pwd":
            self.cmd_pwd(args)
        elif cmd=="cd":
            self.cmd_cd(args)
        elif cmd in ("cat","type"):
            self.cmd_cat(args)
        elif cmd=="bat":
            self.cmd_bat(args)
        elif cmd=="touch":
            self.cmd_touch(args)
        elif cmd in ("mkdir","md"):
            self.cmd_mkdir(args)
        elif cmd in ("rmdir","rd"):
            self.cmd_rmdir(args)
        elif cmd in ("rm","del","erase"):
            self.cmd_rm(args)
        elif cmd in ("cp","copy"):
            self.cmd_cp(args)
        elif cmd in ("mv","move","ren","rename"):
            self.cmd_mv(args)
        elif cmd in ("find","locate"):
            self.cmd_find(args)
        elif cmd=="tree":
            self.cmd_tree(args)
        elif cmd=="du":
            self.cmd_du(args)
        elif cmd=="df":
            self.cmd_df(args)
        elif cmd=="stat":
            self.cmd_stat(args)
        elif cmd in ("chmod","attrib"):
            self.cmd_chmod(args)
        # text
        elif cmd=="echo":
            self.cmd_echo(args, raw, redir_out, redir_append)
            return
        elif cmd=="printf":
            self.cmd_printf(args)
        elif cmd in ("write","edit","nano","ed","vi","vim"):
            self.cmd_write(args)
        elif cmd in ("more","less"):
            self.cmd_more(args)
        elif cmd=="head":
            self.cmd_head(args)
        elif cmd=="tail":
            self.cmd_tail(args)
        elif cmd=="wc":
            self.cmd_wc(args)
        elif cmd in ("grep","egrep"):
            self.cmd_grep(args)
        elif cmd=="sort":
            self.cmd_sort(args)
        elif cmd=="uniq":
            self.cmd_uniq(args)
        elif cmd=="cut":
            self.cmd_cut(args)
        elif cmd in ("hexdump","xxd"):
            self.cmd_hexdump(args)
        elif cmd=="base64":
            self.cmd_base64(args)
        elif cmd=="strings":
            self.cmd_strings(args)
        elif cmd in ("diff","cmp"):
            self.cmd_diff(args)
        elif cmd=="rev":
            self.cmd_rev(args)
        elif cmd=="tee":
            self.cmd_tee(args)
        elif cmd=="truncate":
            self.cmd_truncate(args)
        # system
        elif cmd in ("ver","version"):
            self.cmd_ver(args)
        elif cmd=="uname":
            self.cmd_uname(args)
        elif cmd=="whoami":
            self.cmd_whoami(args)
        elif cmd=="hostname":
            self.cmd_hostname(args)
        elif cmd in ("sysinfo","info"):
            self.cmd_sysinfo(args)
        elif cmd=="date":
            self.cmd_date(args)
        elif cmd=="time":
            self.cmd_time(args)
        elif cmd in ("cal","calendar"):
            self.cmd_cal(args)
        elif cmd in ("clear","cls"):
            self.cmd_clear(args)
        elif cmd in ("history","h"):
            self.cmd_history(args)
        elif cmd=="env":
            self.cmd_env(args)
        elif cmd in ("set","export"):
            self.cmd_set(args)
        elif cmd=="unset":
            self.cmd_unset(args)
        elif cmd=="alias":
            self.cmd_alias(args)
        elif cmd in ("mem","free","meminfo"):
            self.cmd_mem(args)
        elif cmd=="cpuinfo":
            self.cmd_cpuinfo(args)
        elif cmd=="ps":
            self.cmd_ps(args)
        elif cmd in ("top","htop"):
            self.cmd_top(args)
        elif cmd=="uptime":
            self.cmd_uptime(args)
        elif cmd=="sleep":
            self.cmd_sleep(args)
        elif cmd in ("reboot","poweroff","halt","shutdown","exit","quit"):
            if cmd in ("reboot",):
                self.cmd_reboot(args)
            else:
                self.cmd_shutdown(args)
        # network
        elif cmd=="ping":
            self.cmd_ping(args)
        elif cmd in ("ifconfig","ipconfig"):
            self.cmd_ifconfig(args)
        elif cmd in ("curl","http"):
            self.cmd_curl(args)
        elif cmd=="wget":
            self.cmd_wget(args)
        elif cmd=="server":
            self.cmd_server(args)
        elif cmd=="jdb":
            self.cmd_jdb(args)
        # dev/fun
        elif cmd in ("run","exec","eval","js"):
            self.cmd_run(args)
        elif cmd in ("calc","bc","expr"):
            self.cmd_calc(args)
        elif cmd=="cowsay":
            self.cmd_cowsay(args)
        elif cmd=="fortune":
            self.cmd_fortune(args)
        elif cmd=="banner":
            self.cmd_banner(args)
        elif cmd=="figlet":
            self.cmd_figlet(args)
        elif cmd=="matrix":
            self.cmd_matrix(args)
        elif cmd=="snake":
            self.cmd_snake(args)
        elif cmd=="tetris":
            self.cmd_tetris(args)
        elif cmd=="motd":
            self.cmd_motd(args)
        elif cmd=="help":
            self.cmd_help(args)
        elif cmd=="cmds":
            self.cmd_cmds(args)
        elif cmd=="tutorial":
            self.cmd_tutorial(args)
        elif cmd in ("man","whatis","apropos"):
            self.cmd_man(args)
        else:
            # try to run as file?
            if self.fs.is_file(cmd) or self.fs.is_file(self.fs.norm(cmd)):
                self.cmd_run([cmd]+args)
            else:
                print(f"{C_RED}jino: {cmd}: command not found. Type 'cmds' for list{C_RESET}")
                self.last_exit_code=127

    def run(self):
        self.boot()
        # autoexec ?
        auto=self.fs.read("/autoexec.jino")
        if auto:
            print(f"{C_DIM}[autoexec.jino]{C_RESET}")
            for line in auto.splitlines():
                if line.strip():
                    print(f"{C_DIM}> {line}{C_RESET}")
                    self.dispatch(line)
            print()

        while True:
            try:
                prompt=f"{C_BOLD}{C_GREEN}{self.env['USER']}@{self.env['HOST']}{C_RESET}:{C_BOLD}{C_BLUE}{self.fs.cwd}{C_RESET}$ "
                # colored Jino:/> for DOS style alternative
                # prompt = f"{C_YELLOW}Jino:{self.fs.cwd}> {C_RESET}"
                line=input(prompt)
                self.dispatch(line)
            except KeyboardInterrupt:
                print(f"\n{C_DIM}Use 'exit' to quit, Ctrl+D to save{C_RESET}")
            except EOFError:
                print("\nShutdown")
                break
            except SystemExit:
                break
            except Exception as e:
                import traceback
                print(f"{C_RED}[Kernel Panic] {e}{C_RESET}")
                traceback.print_exc()
                self.last_exit_code=1

if __name__=="__main__":
    osys=JinoOS()
    osys.run()
