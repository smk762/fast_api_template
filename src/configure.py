#!/usr/bin/env python3

import string
import shutil
import requests
import secrets
import json
import sys
import os
from pathlib import Path
from const import coin_info

home = os.path.expanduser('~')
script_path = os.path.realpath(os.path.dirname(__file__))
project_root = Path(script_path).parent
print(script_path)
print(project_root)


def get_debug_file(ticker, container=True) -> str:
    path = f"{home}/.komodo/{ticker}"
    if container:
        path = path.replace(home, "/home/komodian")
    return f"{path}/debug.log"


def get_service_yaml(ticker):
    service = []
    info = coin_info[ticker]
    p2p_port = info["p2pport"]
    rpc_port = info["rpcport"]
    service.append(f'  {ticker.lower()}:\n')
    service.append(f'    env_file:\n')
    service.append(f'      - src/.env\n')
    service.append(f'    build:\n')
    service.append(f'      context: ./src\n')
    service.append(f'      dockerfile: Dockerfile.KMD\n')
    service.append(f'    ports:\n')
    service.append(f'      - "127.0.0.1:{rpc_port}:{rpc_port}"\n')
    service.append(f'      - "127.0.0.1:{p2p_port}:{p2p_port}"\n')
    service.append(f'    volumes:\n')
    service.append(f'      - <<: *zcash-params\n')
    service.append(f'      - {home}/.komodo/{ticker}:/home/komodian/.komodo/{ticker}\n')
    service.append(f'    container_name: {ticker.lower()}\n')
    service.append(f'    restart: always\n')
    service.append(f'    stop_grace_period: 15s\n')
    service.append(f'    logging:\n')
    service.append(f'      driver: "json-file"\n')
    service.append(f'      options:\n')
    service.append(f'        max-size: "20m"\n')
    service.append(f'        max-file: "10"\n')
    service.append(f'    command: ["/run_{ticker}.sh"]\n')
    service.append(f'\n')
    return service



def format_param(param, value):
    return f'-{param}={value}'


def generate_rpc_pass(length=24):
    special_chars = "@~-_|():+"
    rpc_chars = string.ascii_letters + string.digits + special_chars
    return "".join(secrets.choice(rpc_chars) for _ in range(length))


def create_cli_wrapper(ticker):
    cli = f"komodo-cli -ac_name={ticker}"
    wrapper = f"{script_path}/cli_wrappers/{ticker.lower()}-cli"
    with open(wrapper, 'w') as conf:
        conf.write('#!/bin/bash\n')
        conf.write(f'docker exec -it {ticker.lower()} {cli} "$@"\n')
        os.chmod(wrapper, 0o755)


def create_launch_file(ticker):
    params = []
    info = coin_info[ticker]
    for param, value in info["launch"].items():
        if isinstance(value, list):
            for v in value:
                params.append(format_param(param, v))
        else:
            params.append(format_param(param, value))
    launch = "komodod " + ' '.join(params)
    launch_file = f"{script_path}/launch_files/run_{ticker}.sh"
    debug = get_debug_file(ticker)
    cli = f"komodo-cli -ac_name={ticker}"
    with open(launch_file, 'w') as f:
        with open(f"{script_path}/templates/launch.template", 'r') as t:
            for line in t.readlines():
                line = line.replace('CLI', cli)
                line = line.replace('COIN', ticker)
                line = line.replace('DEBUG', debug)
                line = line.replace('LAUNCH', launch)
                f.write(line)
        os.chmod(launch_file, 0o755)


def create_conf(ticker):
    conf_file = f"{home}/.komodo/{ticker}/{ticker}.conf"
    data_path = os.path.split(conf_file)[0]
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        
    with open(conf_file, 'w') as conf:
        info = coin_info[ticker]
        rpcip = "0.0.0.0"
        rpcuser = os.getenv("rpcuser")
        rpcpass = os.getenv("rpcpass")
        conf.write(f'rpcuser={rpcuser}\n')
        conf.write(f'rpcpassword={rpcpass}\n')
        conf.write('txindex=1\n')
        conf.write('server=1\n')
        conf.write('daemon=1\n')
        conf.write('rpcworkqueue=256\n')
        conf.write(f'rpcbind={rpcip}:{info["rpcport"]}\n')
        conf.write(f'rpcallowip={rpcip}/0\n')
        conf.write(f'port={info["p2pport"]}\n')
        conf.write(f'rpcport={info["rpcport"]}\n')
    # create debug.log files if not existing
    debug_file = get_debug_file(ticker, False)
    if not os.path.exists(debug_file):
        with open(debug_file, 'w') as f:
            f.write('')




if __name__ == '__main__':
    
    shutil.copy(f'{script_path}/templates/docker-compose.template', f'{project_root}/docker-compose.yml')
    with open(f'{project_root}/docker-compose.yml', 'a+') as conf:
        for ticker in coin_info:
            create_launch_file(ticker)
            create_cli_wrapper(ticker)
            create_conf(ticker)
            yaml = get_service_yaml(ticker)
            conf.writelines(yaml)
            
            





