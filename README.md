## FastAPI Electrum/EVM/Tendermint Scanner

FastAPI service that scans Electrum, EVM, and Tendermint endpoints on a schedule, caches recent results in Memcached, and persists status to SQLite. The API exposes aggregated status for use by dashboards and tools.

### Features
- Periodic scans:
  - Servers status every 300s
  - Database update every 60s (writes cached results)
  - Coins config refresh every 3600s
- Automatic purge of rows older than 7 days at the start of each `update_db()` cycle
- SQLite persistence (`electrum_status.db`) in repo directory
- Memcached for short-lived caches

---

## Requirements
- Python 3.10+ (tested with 3.11)
- pip
- Docker with Compose v2 (`docker compose`)

## Setup
1) Install Python deps
```bash
python3 -m pip install -r requirements.txt
```

2) Start Memcached (required)
```bash
docker compose up -d memcached
```

3) Optional: configure TLS/port via `.env`
Create a `.env` file (same directory as `main.py`) with:
```
SSL_KEY=/path/to/key.pem   # optional
SSL_CERT=/path/to/cert.pem # optional
API_PORT=8999              # default 8999
# Optional overrides
# MEMCACHE_HOST=127.0.0.1
# MEMCACHE_PORT=11211
```

## Run
```bash
python3 main.py
```
The service will start on `0.0.0.0:<API_PORT>` (HTTP by default, HTTPS if `SSL_KEY` and `SSL_CERT` are provided).

Memcached must be running (see Compose step above).

## Docker Compose
The included `docker-compose.yml` builds a slim image with dependencies baked in.

```bash
mkdir -p data
touch data/electrum_status.db   # host file that will be bind-mounted
docker compose up -d --build
```

The compose file injects `MEMCACHE_HOST=memcached` so the app reaches the bundled Memcached service; override via `.env` if you are pointing at an external cache.

Restart without rebuilding once the image exists:

```bash
docker compose up -d
```

## API Endpoints
- `GET /api/v1/electrums_status?coin=<symbol>`: raw records per server/protocol
- `GET /api/v1/coins_status?coin=<symbol>`: aggregated coin status (TCP/SSL/WSS, best blockheight)

## Data
- Database file: `electrum_status.db` (SQLite) in the project root
- Rows with `last_connection` older than 7 days are purged automatically at the start of `update_db()`

## Production
See `docs/production.md` for a production-ready `docker compose` deployment, reverse proxy, backups, and operational guidance.

