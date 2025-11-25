## Production Deployment

This guide shows a production-ready deployment using `docker compose`. It runs:
- The FastAPI app (this repo)
- Memcached for caching
- Optional reverse proxy (Caddy/Nginx) for TLS and public exposure

SQLite is used for persistence; the database file is bind-mounted to the host for durability.

---

## 1) Prerequisites
- Docker with Compose v2 (`docker compose`)
- A domain name and TLS certs (if terminating TLS at the app, otherwise terminate at the proxy)

---

## 2) Directory layout
Recommended structure:
```
fast_api_docker/
  .env
  docker-compose.yml          # existing (memcached)
  docker-compose.prod.yml     # app + overrides (you create this)
  docs/
  electrum_status.db          # created by app (or bind to ./data/electrum_status.db)
  requirements.txt
  main.py
  ...
```

---

## 3) Environment
Create `.env` alongside `main.py`:
```
# Optional TLS directly in app (you can also terminate TLS at a proxy)
SSL_KEY=/path/to/key.pem
SSL_CERT=/path/to/cert.pem

# App port inside the container
API_PORT=8999
```

---

## 4) Compose (app + memcached)
Create `docker-compose.prod.yml` in the project root:

```yaml
services:
  app:
    image: python:3.11-slim
    container_name: electrum-status-api
    working_dir: /app
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - ./.env
    volumes:
      # Mount the application code (read-only) and persist the SQLite DB on host
      - ./:/app:ro
      # Persist the DB file (bind-mount a host file path)
      - ./data/electrum_status.db:/app/electrum_status.db
    command: >
      sh -c "
        pip install --no-cache-dir -r requirements.txt &&
        python3 main.py
      "
    depends_on:
      - memcached
    restart: unless-stopped
    ports:
      # Expose only if not behind a reverse proxy
      - "8999:8999"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:${API_PORT:-8999}/api/v1/coins_status || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 5

  memcached:
    # The base compose already defines memcached. If you prefer to override, keep this in one file only.
    image: memcached:latest
    ports:
      - "127.0.0.1:11211:11211"
    restart: always
    command: ["memcached", "-I", "40m", "-m", "100m"]
    ulimits:
      nproc: 65535
      nofile:
        soft: 65535
        hard: 65535
```

Run:
```bash
docker compose -f docker-compose.prod.yml up -d
```

Notes:
- The SQLite DB file is bind-mounted at `./data/electrum_status.db`. Create the `data/` directory before running:
  ```bash
  mkdir -p data
  ```
- If you prefer building an immutable image, add a `Dockerfile` and switch the `app` service to `build: .`. Example `Dockerfile`:
  ```Dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 8999
  CMD ["python3", "main.py"]
  ```
  Then update compose:
  ```yaml
  services:
    app:
      build: .
      # remove the pip install from command and the code bind-mount
      volumes:
        - ./data/electrum_status.db:/app/electrum_status.db
      command: ["python3", "main.py"]
  ```

---

## 5) Reverse proxy (optional but recommended)
Terminate TLS, add rate-limits, and restrict origins at the proxy. Below are minimal examples.

### Caddyfile
```
example.com {
  reverse_proxy 127.0.0.1:8999
}
```

### Nginx
```
server {
  listen 443 ssl http2;
  server_name example.com;

  ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:8999;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

---

## 6) Operations
- Purge: rows older than 7 days are automatically removed at the start of each `update_db()` run.
- Backups: back up `./data/electrum_status.db` regularly (hot copy is sufficient for SQLite for most cases, but prefer `sqlite3 .backup` for consistency during high write rates).
  ```bash
  docker compose exec app sqlite3 /app/electrum_status.db ".backup '/app/electrum_status-$(date +%F).db'"
  ```
- Logs: app logs to stdout/stderr; use:
  ```bash
  docker compose logs -f app
  ```
- Updating:
  ```bash
  git pull
  docker compose up -d --build
  ```

---

## 7) Security and hardening
- Expose the app only behind a reverse proxy; bind the container port to `127.0.0.1` if proxying:
  ```yaml
  ports:
    - "127.0.0.1:8999:8999"
  ```
- Keep Memcached bound to localhost (already configured).
- Regularly rotate TLS certs if terminating TLS at the app.
- Keep `coins_config.json` updated (the app refreshes it hourly).


