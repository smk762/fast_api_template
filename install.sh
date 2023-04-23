#!/bin/bash

if [ $# -eq 0 ]; then
    echo "No arguments provided. You need to add an name for the API as a parameter"
    echo "For example: ./install.sh faucet"
    exit 1
fi

mkdir -p ~/logs
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx curl libcurl4-openssl-dev libssl-dev jq
pip3 install -r requirements.txt

echo "Configuring environment..."
./config/configure.py env_vars

echo "Setting up FastAPI..."
./config/configure.py nginx
subdomain=$(python3 ./vars.py subdomain)
sudo certbot certonly -d ${subdomain}
./config/configure.py ssl_env
sudo cp nginx/fastapi-${1}.serverblock /etc/nginx/sites-available/${subdomain}
sudo ln -s /etc/nginx/sites-available/${subdomain} /etc/nginx/sites-enabled/${subdomain}
sudo systemctl restart nginx

echo "Creating service file..."
cp config/TEMPLATE-fastapi.service config/fastapi-${1}.service
sed "s|API_PATH|${PWD}|g" -i "config/fastapi-${1}.service"
sed "s/USERNAME/${USER}/g" -i "config/fastapi-${1}.service"

echo "Copying service file to /etc/systemd/system/..."
sudo cp config/fastapi-${1}.service /etc/systemd/system/fastapi-${1}.service

cd /etc/systemd/system/
sudo systemctl enable fastapi-${1}.service
echo
echo "Deamon service created for fastapi-${1}. To run it, use 'sudo systemctl start fastapi-${1}.service'"
echo "Logs will go to ~/logs/fastapi-${1}.log"
echo
