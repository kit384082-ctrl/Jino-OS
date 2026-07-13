# Jino OS - GitHub .gitignore
# Build artifacts
build/
isodir/
*.iso
*.bin
*.img
*.elf
*.o
*.a
*.so

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
*.egg-info/
dist/
*.log

# Runtime
/tmp/jino_*
/tmp/jino_runtime/
jino_fs_persist.json
jino_servers_db.json
jino_config.json

# OS
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# IDE
.vscode/
.idea/
*.code-workspace

# Node (for future gui)
node_modules/
dist/
.next/

# Secrets
.env
.env.local
secrets.txt
