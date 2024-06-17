#!/bin/bash

pip3 install -r src/requirements.txt


echo "Setting up .env file..."
USER_ID=$(id -u)
GROUP_ID=$(id -g)
echo "USER_ID=${USER_ID}" > src/.env
echo "GROUP_ID=${GROUP_ID}" >> src/.env
echo "RPC_USER=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 12)" >> src/.env
echo "RPC_PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16)" >> src/.env


cd src
mkdir -p /home/${USER}/.zcash-params
./fetch-params.sh
./configure.py
cd -
docker compose build

./update_clis.sh
