# Production Deployment Guide

This guide walks through deploying the FastAPI template into a hardened, production-ready environment. It assumes familiarity with Linux server administration and access to the infrastructure that will host the API.

## 1. Reference Architecture

- **Application server**: FastAPI served by `uvicorn` (or gunicorn with `uvicorn.workers.UvicornWorker`) inside a Python virtual environment.
- **Data layer**: SQLite file stored on fast local disk. (If you outgrow SQLite, migrate to a managed relational database and adapt `lib/sqlite.py`.)
- **Reverse proxy**: Nginx terminating TLS and forwarding to the app over `localhost:<FASTFASTAPI_PORT>`.
- **Secrets**: Environment file owned by the service account with `chmod 600`.
- **Observability**: `journalctl` for systemd logs + external monitoring hitting `/api/v1/healthcheck`.

## 2. Pre‑Deployment Checklist

- Chosen hostname + DNS pointing to the server.
- TLS certificate strategy (ACME via certbot, custom cert, or secret manager).
- API credentials for Banxa and Ramp (both sandbox and production variants).
- Hardened firewall rules (allow 80/443 inbound, limit SSH, allow egress to Banxa/Ramp).
- Backup/retention plan for the SQLite file.
- Optional: container registry credentials if you will wrap the app in `docker compose`.

## 3. Provision and Harden the Host

Run the following as root (replace packages to match your distribution):

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip sqlite3 nginx certbot
adduser --system --group fastapi
mkdir -p /opt/fast_api_template && chown fastapi:fastapi /opt/fast_api_template
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

Disable password SSH logins, enable automatic security updates, and configure fail2ban per your security baseline.

## 4. Deploy the Application Code

```bash
sudo -u fastapi bash -lc "
  cd /opt/fast_api_template && \
  git clone https://github.com/<org>/fast_api_template.git . && \
  python3 -m venv .venv && \
  source .venv/bin/activate && \
  pip install --upgrade pip && \
  pip install -r requirements.txt
"
```

### Environment configuration

Create `/opt/fast_api_template/.env` with:

```
HOST=0.0.0.0
FASTFASTAPI_PORT=8088
SUBDOMAIN=api.example.com
USE_MIDDLEWARE=True
CORS_ORIGINS=https://app.example.com https://admin.example.com
SQLITEDB_PATH=/opt/fast_api_template/data/app.db
FAUCET_COINS=KMD VRSC
KOMODEFI_IP=127.0.0.1
KOMODEFI_PORT=7783
KOMODEFI_USERPASS=RpcUserP@assw0rd
BANXA_APIKEY=<sandbox-key>
BANXA_SECRET=<sandbox-secret>
BANXA_BASEURL=https://banxa-sandbox.example.com
BANXA_PROD_APIKEY=<prod-key>
BANXA_PROD_SECRET=<prod-secret>
BANXA_PROD_BASEURL=https://banxa.example.com
RAMP_APIKEY=<sandbox-key>
RAMP_BASEURL=https://api-sandbox.ramp.network
RAMP_PROD_APIKEY=<prod-key>
RAMP_PROD_BASEURL=https://api.ramp.network
SSL_CERT=/etc/ssl/certs/api.example.com.crt
SSL_KEY=/etc/ssl/private/api.example.com.key
```

- Use descriptive names for any additional upstream APIs; the loader infers keys based on the `_APIKEY`, `_SECRET`, and `_BASEURL` suffixes.
- Store `.env` with `chmod 600` and ensure only the `fastapi` user can read it.

Create the SQLite directory and assign permissions:

```bash
sudo -u fastapi mkdir -p /opt/fast_api_template/data
sudo -u fastapi touch /opt/fast_api_template/data/app.db
```

Update `config/table_config.json` before first boot if you need custom tables; the app auto-creates them on startup.

## 5. Smoke Test Locally

```bash
sudo -u fastapi bash -lc "
  cd /opt/fast_api_template && \
  source .venv/bin/activate && \
  python main.py --help  # confirm dependencies load
"
curl -k https://127.0.0.1:8088/api/v1/healthcheck
```

Disable debug prints before production (e.g., remove stray `print` statements or guard them behind log levels).

## 6. Systemd Service

`/etc/systemd/system/fastapi.service`:

```
[Unit]
Description=FastAPI Template
After=network.target

[Service]
Type=simple
User=fastapi
Group=fastapi
WorkingDirectory=/opt/fast_api_template
EnvironmentFile=/opt/fast_api_template/.env
ExecStart=/opt/fast_api_template/.venv/bin/python /opt/fast_api_template/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
systemctl daemon-reload
systemctl enable --now fastapi
systemctl status fastapi
journalctl -u fastapi -f
```

## 7. Reverse Proxy + TLS

Issue/renew certificates (e.g., `certbot certonly --nginx -d api.example.com`). Minimal Nginx site:

```
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location / {
        proxy_pass https://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$host$request_uri;
}
```

Reload Nginx: `nginx -t && systemctl reload nginx`.

## 8. Observability and Operations

- **Health**: monitor `/api/v1/healthcheck` from an external probe.
- **Logs**: forward `journalctl -u fastapi` to your SIEM via `systemd-journald` or `fluent-bit`.
- **Metrics**: integrate with node exporter, and consider adding FastAPI instrumentation (e.g., Prometheus middleware) for latency metrics.
- **Alerts**: alert on 5xx spikes, SSL expiry, and CPU/memory thresholds.

## 9. Upgrades and Rollbacks

1. `sudo systemctl stop fastapi`
2. `sudo -u fastapi git fetch --all && git checkout <version>`
3. `sudo -u fastapi bash -lc "cd /opt/fast_api_template && source .venv/bin/activate && pip install -r requirements.txt"`
4. `sudo systemctl start fastapi`

For zero-downtime, deploy onto a staging host or run a blue/green pair behind a load balancer. Keep backups of `/opt/fast_api_template/data/app.db` before any schema change.

## 10. Optional Containerization

If your organization standardizes on containers, create a lightweight image and manage it via `docker compose`. Ensure secrets stay in an external vault or compose override file, and run the container behind the same reverse proxy + TLS setup.

---

Following this checklist yields a reproducible, auditable deployment that meets common production-readiness expectations (least privilege, repeatable builds, monitoring, and encrypted transport).

