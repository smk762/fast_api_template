# FastAPI Moralis Proxy

FastAPI wrapper around Moralis RPC endpoints with SQLite-backed caching and periodic refresh jobs. The repository also ships with tooling to generate environment variables, issue TLS certificates, and install a hardened Nginx + systemd stack.

## Features
- FastAPI app with Moralis-backed routes such as `/api/v1/get_wallet_nfts` and `/api/v1/get_nft_metadata`
- Background sync task that writes the latest payload to `jsondata.json`
- SQLite helper and configurable schema via `config/table_config.json`
- Automated provisioning script that installs apt packages, configures `.env`, Nginx, TLS (Let’s Encrypt via `certbot`), and a systemd unit

## Requirements
- Ubuntu 20.04+ (tested with Linux 5.4 kernels)
- sudo access for installing packages, writing to `/etc/systemd/system`, and `certbot`
- DNS record that points `SUBDOMAIN` to the host so certificates can be issued
- Python 3.10+ and `pip`
- Moralis API key

## Quick Start
1. Clone the repository and enter the project directory:
   ```bash
   git clone https://github.com/<org>/fast_api_docker.git
   cd fast_api_docker
   ```
2. Make sure the install script is executable: `chmod +x install.sh`.
3. Run the provisioning script, passing a service name (e.g., `faucet`):
   ```bash
   ./install.sh faucet
   ```
   The service name becomes part of the generated Nginx server block and systemd unit (`fastapi-faucet`).
4. Start the service: `sudo systemctl start fastapi-faucet.service` and check logs in `~/logs/fastapi-faucet.log`.

## What the Installer Does
Running `./install.sh <service>` performs these steps:
- Installs apt packages (`python3`, `python3-venv`, `nginx`, `certbot`, etc.) and pip requirements
- Calls `config/configure.py env_vars` to scaffold `.env` with generated secrets (seed phrase, RPC password) and sensible defaults
- Calls `config/configure.py nginx <service>` to render an Nginx server block, then enables it under `/etc/nginx/sites-enabled`
- Requests a Let’s Encrypt certificate for the configured subdomain and updates `.env` with the resulting key/cert paths
- Clones `config/fastapi-TEMPLATE.service`, injects absolute project paths and username, then enables the unit under `/etc/systemd/system`

## Environment Variables
The `.env` file contains the runtime configuration. Key entries include:

| Variable | Description |
| --- | --- |
| `SUBDOMAIN` | Public DNS name used by the API and TLS certificate |
| `FASTAPI_HOST` / `FASTAPI_PORT` | Bind host and port for the FastAPI/uvicorn process (default `127.0.0.1:8088`) |
| `SSL_KEY` / `SSL_CERT` | Optional direct TLS key/cert pair when *not* proxying through Nginx |
| `CORS_ORIGINS` | Space-delimited list of additional origins the API should accept |
| `SQLITEDB_PATH` | Location of the SQLite database (defaults to `db/fastapi.db`) |
| `MORALIS_API_KEY` | Moralis API key used by the proxy endpoints |
| `ATOMICDEX_*` | Connection details for AtomicDEX (`IP`, `PORT`, `USERPASS`, `SEEDPHRASE`) |
| `WEBROOT`, `NGINX_PROXY_HOST`, `FAUCET_COINS`, `DISCORD_TOKEN` | Miscellaneous values consumed by the provisioning scripts |

Use `python3 vars.py print` to dump the parsed configuration for debugging.

## Running the App Manually
For local testing without systemd:
```bash
pip install -r requirements.txt
python3 config/configure.py env_vars  # populate .env if needed
python3 main.py
```
Visit `http://127.0.0.1:8088/docs` to inspect the OpenAPI schema. By default, TLS is handled by the fronting Nginx server, so the built-in uvicorn server listens on HTTP.

## Managing the Systemd Service
- Start: `sudo systemctl start fastapi-<service>.service`
- Stop: `sudo systemctl stop fastapi-<service>.service`
- Restart after code updates: `sudo systemctl restart fastapi-<service>.service`
- Logs: `tail -f ~/logs/fastapi-<service>.log`

## Production Deployment
Detailed, step-by-step deployment guidance (DNS checks, firewall rules, TLS renewal, and update strategies) lives in `docs/production-deployment.md`.

## Additional Notes
- Nginx rate-limiting is preconfigured in `config/fastapi-TEMPLATE.serverblock`. Adjust per your traffic profile.
- `config/configure.py atomicdex` can be run separately to regenerate AtomicDEX configuration artifacts if required by your workflow.

Happy hacking!
