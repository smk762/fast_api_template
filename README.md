# FastAPI Template

This repository exposes a hardened FastAPI façade in front of third-party providers such as Banxa and Ramp. It centralizes API authentication, rate-limiting logic, and request logging while providing a predictable interface for internal consumers.

## Key Features

- 🚀 **FastAPI + Uvicorn** stack with optional CORS middleware and SSL termination.
- 🔐 **Credential fan-out** via environment-driven configuration (`BANXA_*`, `RAMP_*`, etc.).
- 🗃️ **SQLite bootstrapper** that auto-creates tables based on `config/table_config.json`.
- 🧱 **Extensible architecture**: drop new upstream providers into `lib/` and expose them through `/api/v1/{provider}` routes.
- 🩺 Built-in `/api/v1/healthcheck` endpoint for monitoring and load-balancers.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py` | FastAPI application entry point and route definitions. |
| `lib/config.py` | Loads `.env` settings, API metadata, and SQLite config. |
| `lib/banxa.py`, `lib/ramp.py` | Provider-specific proxy logic and signing. |
| `lib/sqlite.py` | Helper for ensuring configured tables exist. |
| `config/table_config.json` | Declarative schema for tables to auto-create at startup. |
| `docs/production-deployment.md` | Step-by-step production rollout guide. |

## Requirements

- Python 3.10+ (tested with CPython)
- `sqlite3` CLI (optional but useful for inspecting the DB)
- Access credentials for Banxa and Ramp (sandbox and production)
- OpenSSL if you plan to generate self-signed certificates locally

## Quick Start (local development)

```bash
git clone https://github.com/<org>/fast_api_template.git
cd fast_api_template
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env  # create your env file (see below)
uvicorn main:app --reload --host 0.0.0.0 --port 8088
```

Visit `http://127.0.0.1:8088/docs` for the interactive OpenAPI UI.

> **Tip:** `python main.py` also works; it reads SSL settings from `.env` and falls back to plain HTTP if no certs are configured.

## Environment Variables

The application relies entirely on `.env`. The loader automatically derives API keys/secrets/URLs by trimming the suffixes `_APIKEY`, `_SECRET`, and `_BASEURL`, so matching names are important.

| Variable | Description | Default |
| --- | --- | --- |
| `HOST` | Interface FastAPI binds to when launched via `python main.py`. | `127.0.0.1` |
| `FASTFASTAPI_PORT` | Port FastAPI listens on (typo kept for backward compatibility). | `8088` |
| `SUBDOMAIN` | Used to build `FASTAPI_URL` metadata. | _None_ |
| `USE_MIDDLEWARE` | Set to `True` to enable permissive CORS (override origins via `CORS_ORIGINS`). | `False` |
| `CORS_ORIGINS` | Space-separated origins when middleware is enabled. | `*` |
| `SQLITEDB_PATH` | Absolute path to the SQLite file; defaults to `lib/db`. | `lib/db` |
| `FAUCET_COINS` | Space-separated coin symbols for faucet endpoints. | _Empty_ |
| `SSL_KEY` / `SSL_CERT` | Paths to TLS key/cert; when set, the server starts in HTTPS mode. | _None_ |
| `KOMODEFI_IP`, `KOMODEFI_PORT`, `KOMODEFI_USERPASS` | Connection info for Komodefi services. | `127.0.0.1`, `7783`, `RpcUserP@assw0rd` |
| `<PROVIDER>_APIKEY` | API key for sandbox endpoints (e.g., `BANXA_APIKEY`). | _Required_ |
| `<PROVIDER>_SECRET` | Corresponding secret (Banxa) or HMAC seed. | _Required_ |
| `<PROVIDER>_BASEURL` | Base URL for the sandbox endpoint (no trailing slash). | _Required_ |
| `<PROVIDER>_PROD_APIKEY` | API key for production endpoints. | _Required_ |
| `<PROVIDER>_PROD_SECRET` | Production secret. | _Required_ |
| `<PROVIDER>_PROD_BASEURL` | Production base URL. | _Required_ |

Example snippet:

```
HOST=0.0.0.0
FASTFASTAPI_PORT=8088
USE_MIDDLEWARE=True
CORS_ORIGINS=https://myapp.example.com
BANXA_APIKEY=<sandbox-key>
BANXA_SECRET=<sandbox-secret>
BANXA_BASEURL=https://banxa-sandbox.example.com
BANXA_PROD_APIKEY=<prod-key>
BANXA_PROD_SECRET=<prod-secret>
BANXA_PROD_BASEURL=https://banxa.example.com
RAMP_APIKEY=<sandbox-host-api-key>
RAMP_BASEURL=https://api-sandbox.ramp.network
RAMP_PROD_APIKEY=<prod-host-api-key>
RAMP_PROD_BASEURL=https://api.ramp.network
```

## Running the API

- **Health check:** `GET /api/v1/healthcheck`
- **Generic proxy (Banxa/Ramp):**
  - `GET /api/v1/banxa?endpoint=/api/orders&order_id=123`
  - `POST /api/v1/ramp?endpoint=/hostTransactions` with JSON payload
- Append `is_test_mode=true` to target sandbox credentials.

Sample `curl`:

```bash
curl -G "http://localhost:8088/api/v1/banxa" \
  --data-urlencode "endpoint=/api/orders" \
  --data-urlencode "order_id=123" \
  --data-urlencode "is_test_mode=true"
```

## SQLite Table Bootstrap

`lib/sqlite.py` inspects `config/table_config.json` at startup and auto-creates any missing tables defined there. Update the JSON before the first boot or when adding tables; the helper is intentionally conservative and will not drop or modify existing schemas.

## Testing

- Ad-hoc Banxa signature validation can be performed with `python test_banxa.py` (make sure to plug in valid credentials).
- Add FastAPI route tests via `pytest` or `httpx.AsyncClient` for more coverage.

## Deployment

For a complete production rollout covering system hardening, TLS, reverse proxying, and monitoring, follow the [Production deployment guide](docs/production-deployment.md).

High-level steps:

1. Create a dedicated system user.
2. Install dependencies (`python3`, `python3-venv`, `sqlite3`, `nginx`).
3. Populate `.env` with the required secrets.
4. Run the app via `uvicorn` or a `systemd` service.
5. Terminate TLS at Nginx (or your edge proxy) and forward to the app.

## Troubleshooting

- **`KeyError: 'BANXA_PROD'`** – ensure the matching `_APIKEY`, `_SECRET`, and `_BASEURL` variables exist for both sandbox and prod.
- **CORS blocked in browsers** – set `USE_MIDDLEWARE=True` and configure explicit origins via `CORS_ORIGINS`.
- **SQLite file missing** – set `SQLITEDB_PATH` to a writable location; the app only creates the directory if it already exists.
- **TLS not activating** – double-check the `SSL_CERT`/`SSL_KEY` values and file permissions; on failure the server silently falls back to HTTP.

Need more details? Open an issue or reach out to the maintainers.