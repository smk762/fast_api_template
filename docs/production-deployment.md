# Production Deployment Guide

This document describes the recommended procedure for deploying the FastAPI Moralis Proxy on a production Ubuntu host. It assumes you control DNS for the target subdomain and have sudo privileges on the machine.

## 1. Pre-Deployment Checklist
- **Server baseline**: Ubuntu 20.04+ with latest security updates (`sudo apt-get update && sudo apt-get upgrade -y`).
- **DNS**: `SUBDOMAIN` must resolve to the server’s public IP before running `certbot`.
- **Firewall**: Allow inbound ports 22 (SSH), 80 (HTTP, for ACME challenges), and 443 (HTTPS):
  ```bash
  sudo ufw allow OpenSSH
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable
  ```
- **Time sync**: Ensure NTP is enabled (`timedatectl status`) so TLS certificates remain valid.

## 2. Clone the Repository
```bash
git clone https://github.com/<org>/fast_api_docker.git /opt/fast_api_docker
cd /opt/fast_api_docker
```
Keeping the project under `/opt` (or another root-owned directory) simplifies permission management for systemd.

## 3. Populate the Environment File
Run the helper to scaffold `.env` and review the generated values:
```bash
python3 config/configure.py env_vars
```
Key items to verify:
- `SUBDOMAIN`: must match the DNS record used for TLS.
- `FASTAPI_PORT`: default is `8077`; change if the port is already occupied.
- `CORS_ORIGINS`: add production front-end URLs.
- `MORALIS_API_KEY`: supply your live key.

Re-run the helper any time you add new variables—existing entries remain untouched.

## 4. Execute the Installer
```bash
chmod +x install.sh
./install.sh faucet   # replace "faucet" with your service label
```
The script installs apt dependencies, pip packages, renders the Nginx server block, requests a Let’s Encrypt certificate (`certbot certonly -d <SUBDOMAIN>`), and writes a systemd unit named `fastapi-<service>.service`. Confirm that `sudo certbot` completed successfully; certificate problems usually stem from DNS or firewall misconfiguration.

## 5. Validate Nginx and Systemd
1. **Reload services**:
   ```bash
   sudo systemctl restart nginx
   sudo systemctl start fastapi-faucet.service
   sudo systemctl status fastapi-faucet.service
   ```
2. **Smoke test**:
   ```bash
   curl -H "Host: <SUBDOMAIN>" https://<SUBDOMAIN>/api/v1/get_wallet_nfts
   ```
   A JSON response indicates the proxy is reachable through Nginx and the certificate is trusted.

## 6. Logs, Metrics, and Monitoring
- Application logs: `tail -f ~/logs/fastapi-<service>.log`.
- Nginx access/error logs: `~/logs/<SUBDOMAIN>-access.log` and `~/logs/<SUBDOMAIN>-error.log`.
- Consider shipping logs to a central aggregator (Loki, Elasticsearch, etc.) and adding systemd health alerts (e.g., via `systemd-notify` hooks) for better observability.

## 7. Updating the Application
1. Pull the latest code:
   ```bash
   cd /opt/fast_api_docker
   git pull
   pip3 install -r requirements.txt
   ```
2. Restart the service:
   ```bash
   sudo systemctl restart fastapi-<service>.service
   sudo systemctl status fastapi-<service>.service
   ```
3. Watch the log file for regressions or stack traces for a few minutes.

Rolling back is as easy as checking out the previous commit and restarting the service again.

## 8. Certificate Renewal
- Let’s Encrypt certificates expire every 90 days. Add a cron entry (or rely on `certbot.timer`) to run `sudo certbot renew` daily.
- Test the renewal path at least once:
  ```bash
  sudo certbot renew --dry-run
  ```
- After renewal, Nginx picks up the new certificates automatically; no reload is required unless you changed the file paths.

## 9. Backup and Recovery
- **Config**: back up `.env`, `/etc/nginx/sites-available/<SUBDOMAIN>`, and `/etc/systemd/system/fastapi-<service>.service`.
- **Certificates**: `/etc/letsencrypt/live/<SUBDOMAIN>` and `/etc/letsencrypt/archive/<SUBDOMAIN>`.
- **Data**: snapshot SQLite databases under `db/` as needed.
- **Automation**: consider using `rsnapshot`, `restic`, or cloud provider snapshots to schedule recurring backups.

## 10. Troubleshooting
- `certbot` fails: ensure the DNS record is visible (`dig +short <SUBDOMAIN>`) and port 80 is open.
- Service won’t start: inspect `sudo journalctl -u fastapi-<service> -f` for Python stack traces or missing environment variables.
- 502 / Bad Gateway: confirm uvicorn is listening on `FASTAPI_PORT` and Nginx’s `proxy_pass` target matches (`config/fastapi-<service>.serverblock`).

Following the sequence above gives you a reproducible, auditable production rollout. Pair it with infrastructure-as-code (Ansible, Terraform) when you need to scale to multiple environments.

