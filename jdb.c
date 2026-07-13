{
  "repo": "Jino Official Repository",
  "version": "1.0",
  "packages": [
    {
      "name": "nginx",
      "version": "1.25.2",
      "description": "High performance static web server (Jino port)",
      "type": "server",
      "category": "web",
      "port": 8080,
      "root": "/www",
      "dependencies": [],
      "size": "2.1MB",
      "install_cmd": "srv create nginx --template static --port 8080 --root /www && echo 'Nginx installed! srv start nginx'",
      "config_template": {"worker_processes": 1, "gzip": true, "access_log": true}
    },
    {
      "name": "apache",
      "version": "2.4.58",
      "description": "Apache HTTPD compatible server for Jino",
      "type": "server",
      "category": "web",
      "port": 8081,
      "root": "/www",
      "dependencies": [],
      "size": "3.4MB"
    },
    {
      "name": "jino-web",
      "version": "1.0.0",
      "description": "Built-in JinoServer enhanced with API",
      "type": "server",
      "category": "web",
      "port": 80,
      "root": "/www",
      "dependencies": [],
      "size": "128KB"
    },
    {
      "name": "file-server",
      "version": "1.0.0",
      "description": "Simple file sharing server like python -m http.server",
      "type": "server",
      "category": "file",
      "port": 8000,
      "root": "/home/user",
      "dependencies": []
    },
    {
      "name": "api-server",
      "version": "2.0.0",
      "description": "REST API server with JinoDB integration",
      "type": "server",
      "category": "api",
      "port": 3000,
      "root": "/api",
      "endpoints": ["/api/status", "/api/jdb", "/api/files", "/api/echo"]
    },
    {
      "name": "python-api",
      "version": "3.11-sim",
      "description": "Python Flask-like API server",
      "type": "server",
      "category": "api",
      "port": 5000,
      "root": "/apps/python"
    },
    {
      "name": "nodejs",
      "version": "20.8-sim",
      "description": "Node.js Express compatible server",
      "type": "runtime",
      "category": "runtime",
      "port": 3001,
      "root": "/apps/node"
    },
    {
      "name": "php-server",
      "version": "8.2-sim",
      "description": "PHP 8.2 server with WordPress support",
      "type": "server",
      "category": "web",
      "port": 8082,
      "root": "/www/php"
    },
    {
      "name": "wordpress",
      "version": "6.4",
      "description": "Full WordPress CMS on Jino",
      "type": "app",
      "category": "cms",
      "port": 8083,
      "root": "/www/wordpress",
      "dependencies": ["php-server", "mysql"]
    },
    {
      "name": "mysql",
      "version": "8.0-sim",
      "description": "MySQL compatible DB over JinoDB",
      "type": "database",
      "category": "db",
      "port": 3306,
      "root": "/db/mysql"
    },
    {
      "name": "postgres",
      "version": "16-sim",
      "description": "PostgreSQL compatible server",
      "type": "database",
      "category": "db",
      "port": 5432,
      "root": "/db/pg"
    },
    {
      "name": "redis",
      "version": "7.2-sim",
      "description": "Redis in-memory store - ultra fast over JinoDB",
      "type": "database",
      "category": "db",
      "port": 6379
    },
    {
      "name": "chat-server",
      "version": "1.0",
      "description": "WebSocket chat server",
      "type": "server",
      "category": "chat",
      "port": 9000,
      "root": "/apps/chat"
    },
    {
      "name": "game-server",
      "version": "1.0",
      "description": "Multiplayer game server for Jino games",
      "type": "server",
      "category": "game",
      "port": 7777
    },
    {
      "name": "minecraft-server",
      "version": "1.20-sim",
      "description": "Minecraft server (simulated, for fun)",
      "type": "game",
      "category": "game",
      "port": 25565
    },
    {
      "name": "static",
      "version": "1.0",
      "description": "Template: static website",
      "type": "template",
      "category": "template",
      "port": 8080
    },
    {
      "name": "express",
      "version": "4.18",
      "description": "Template: Express.js app",
      "type": "template",
      "category": "template",
      "port": 3000
    },
    {
      "name": "flask",
      "version": "2.3",
      "description": "Template: Flask app",
      "type": "template",
      "category": "template",
      "port": 5000
    }
  ]
}
