# curl в Jino OS v2.2 - Полная документация

## Что такое curl в Jino?

Это полноценная реализация curl как в Linux, но внутри Jino OS. Поддерживает реальные HTTP/HTTPS запросы к локальным Jino серверам и внешним сайтам, а также file:// для JinoFS.

## Синтаксис

```
curl [options] <url>
```

## URL форматы

- `http://localhost:8080/` - локальный сервер Jino (после srv start)
- `http://localhost:3000/api/status` - API endpoint
- `https://example.com/api` - внешний сайт
- `file:///www/index.html` - файл из JinoFS
- `/www/index.html` - сокращение для file://
- `localhost:8080/` - автоматом добавится http://

## Опции

| Флаг | Описание | Пример |
|------|----------|--------|
| `-X, --request` | HTTP метод | `-X POST`, `-X PUT`, `-X DELETE` |
| `-H, --header` | Заголовок | `-H "Content-Type: application/json"` |
| `-d, --data` | Данные для POST | `-d '{"key":"val"}'`, `-d @/home/user/data.json` |
| `-o, --output` | Сохранить в файл | `-o /tmp/page.html` |
| `-O, --remote-name` | Сохранить с именем из URL | `-O` (сохранит как index.html) |
| `-i, --include` | Показать заголовки ответа | `-i` |
| `-v, --verbose` | Подробный вывод запроса+ответа | `-v` |
| `-s, --silent` | Тихий режим | `-s` |
| `-L, --location` | Следовать редиректам | `-L` |
| `--connect-timeout` | Таймаут | `--connect-timeout 10` |
| `-u, --user` | Basic Auth | `-u user:pass` |
| `--help, -h` | Справка | `--help` |

## Примеры

### Базовые

```bash
# Локальный файл JinoFS
curl file:///www/index.html
curl /www/index.html

# Локальный сервер
jpkg install nginx --port 8080 --name myweb
srv start myweb
curl http://localhost:8080/
curl http://localhost:8080/api/status
curl http://localhost:8080/api/jdb

# Внешний
curl https://api.github.com/users/github
curl https://example.com
```

### Сохранение

```bash
curl http://localhost:8080/ -o /tmp/page.html
cat /tmp/page.html

curl http://localhost:8080/index.html -O
# сохранит как index.html в текущей папке

curl file:///www/index.html -o /tmp/copy.html
```

### Заголовки

```bash
curl http://localhost:8080/ -i
# покажет HTTP/1.1 200 OK + заголовки + тело

curl http://localhost:8080/ -v
# подробный: * Trying, * Connected, > GET, < HTTP/1.1, etc
```

### POST/PUT с данными

```bash
# JSON POST
curl -X POST http://localhost:3000/api/jdb -d '{"newkey":"newval"}' -H "Content-Type: application/json"

# Form POST
curl -X POST http://localhost:8080/api/echo -d "msg=hello"

# Данные из файла JinoFS
echo '{"test":123}' > /tmp/data.json
curl -X POST http://localhost:3000/api/jdb -d @/tmp/data.json
curl -X POST http://localhost:3000/api/jdb -d @/home/user/test.json -H "Content-Type: application/json"

# PUT
curl -X PUT http://localhost:8080/api/files -d '{"file":"test"}'

# DELETE
curl -X DELETE http://localhost:8080/api/files/test
```

### Таймауты и редиректы

```bash
curl http://localhost:8080/ --connect-timeout 10
curl http://localhost:8080/old -L  # следовать редиректу
```

### Auth

```bash
curl http://localhost:8080/secure -u admin:password
```

### Комбинированные

```bash
curl -X POST http://localhost:3000/api/jdb \
  -d '{"user":"Jino"}' \
  -H "Content-Type: application/json" \
  -i -v \
  -o /tmp/response.json
```

## Ошибки curl в Jino

### JNO-017 Connection refused

```
curl http://localhost:8080/
┌─ ОШИБКА JNO-017: Connection refused
│ Сообщение: curl не может подключиться
│ Контекст: Connection refused к localhost:8080
│ Причина: Сервер не запущен
│ Решение: srv list, srv start <name>
```

Почему:
- Сервер не запущен (`srv list` покажет stopped)
- Неверный порт
- Сервер упал

Решение:
```bash
srv list
srv start myweb
curl http://localhost:8080/ -v  # с verbose для деталей
```

### JNO-018 Timeout

```
curl http://slow.site/ -> timeout
```

Решение:
```bash
curl http://slow.site/ --connect-timeout 10
srv logs myweb
srv restart myweb
```

### JNO-019 Invalid URL

```
curl not_a_url -> JNO-019
```

Решение:
```bash
curl http://localhost:8080/     # с http://
curl file:///www/index.html    # для файлов
curl /www/index.html           # сокращение
```

### JNO-020 HTTP error

```
curl http://localhost:8080/nope
-> HTTP 404

curl http://localhost:8080/ -i  # увидишь заголовки
srv logs myweb                  # логи сервера
```

## curl vs wget

`wget` в Jino - алиас для curl с -o:

```bash
wget http://localhost:8080/ -O /tmp/page.html
# то же что
curl http://localhost:8080/ -o /tmp/page.html

wget http://localhost:8080/
# сохранит как /tmp/index.html (basename)
```

## Интеграция с JinoFS и серверами

- `curl file:///www/index.html` читает из виртуальной FS
- `curl http://localhost:8080/` читает из реального HTTP сервера (который сам берет файлы из /tmp/jino_runtime/ скопированных из JinoFS)
- `curl -o /tmp/out.html` сохраняет в JinoFS, потом `cat /tmp/out.html`
- Можно `echo '{"a":1}' > /tmp/data.json` затем `curl -d @/tmp/data.json`

## Тест curl

```bash
# Подними сервер
jpkg install nginx --port 18080 --name test
srv start test

# Тесты
curl http://localhost:18080/ -i
curl http://localhost:18080/api/status
curl http://localhost:18080/api/jdb
curl http://localhost:18080/ -v
curl http://localhost:18080/ -o /tmp/test.html
cat /tmp/test.html
curl -X POST http://localhost:18080/api/jdb -d '{"curltest":"ok"}' -H "Content-Type: application/json"
curl http://localhost:18080/api/jdb  # увидишь curltest

# Ошибки
curl http://localhost:19999/  # JNO-017 Connection refused
curl noturl                   # JNO-019 Invalid URL

# Очистка
srv stop test
srv delete test
```
