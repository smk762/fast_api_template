#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import socket
import string
import mnemonic
from dotenv import load_dotenv
from lib.logger import logger

load_dotenv()

special_chars = ["@", "~", "-", "_", "|", ":", "+"]


def generate_rpc_pass(length):
    rpc_pass = ""
    quart = int(length/4)
    while len(rpc_pass) < length:
        rpc_pass += ''.join(random.sample(string.ascii_lowercase,
                            random.randint(1, quart)))
        rpc_pass += ''.join(random.sample(string.ascii_uppercase,
                            random.randint(1, quart)))
        rpc_pass += ''.join(random.sample(string.digits,
                            random.randint(1, quart)))
        rpc_pass += ''.join(random.sample(special_chars,
                            random.randint(1, quart)))
    str_list = list(rpc_pass)
    random.shuffle(str_list)
    return ''.join(str_list)


def configure_atomicdex(path=None):
    logger.info("Configuring AtomicDEX...")
    if not path:
        path = ""
    elif not path.endswith("/"):
        path = f"{path}/"

    ATOMICDEX_IP = os.getenv("ATOMICDEX_IP")
    ATOMICDEX_PORT = os.getenv("ATOMICDEX_PORT")
    ATOMICDEX_USERPASS = os.getenv("ATOMICDEX_USERPASS")
    ATOMICDEX_SEEDPHRASE = os.getenv("ATOMICDEX_SEEDPHRASE")
    if None in [ATOMICDEX_IP, ATOMICDEX_PORT, ATOMICDEX_USERPASS, ATOMICDEX_SEEDPHRASE]:
        logger.warning("Missing environment variables. Please check .env file.")
        logger.warning("or run './configure.py env_vars' to populate.")
        logger.warning("Exiting...")
        sys.exit(1)

    conf = {
        "gui": "FAUCET",
        "netid": 7777,
        "rpc_ip": f"{ATOMICDEX_IP}:{ATOMICDEX_PORT}",
        "rpc_password": ATOMICDEX_USERPASS,
        "passphrase": ATOMICDEX_SEEDPHRASE,
        "userhome": "/${HOME#\"/\"}"
    }

    with open(f"{path}MM2.json", "w+") as f:
        json.dump(conf, f, indent=4)
    logger.info(f"{path}MM2.json file created.")

    with open(f"{path}userpass", "w+") as f:
        f.write(f'{path}userpass="{ATOMICDEX_USERPASS}"')
    logger.info(f"{path}userpass file created.")
    logger.info("AtomicDEX configured successfully!")

def generate_seed():
    q = "[E]nter seed manually or [G]enerate one? [E/G]: "
    a = input(q)
    while a not in ["G", "g", "E", "e"]:
        logger.warning("Invalid input!")
        a = input(q)

    if a in ["E", "e"]:
        passphrase = input("Enter a seed phrase: ")
    else:
        m = mnemonic.Mnemonic('english')
        passphrase = m.generate(strength=256)
    return passphrase


def check_dotenv():
    req_vars = ["ATOMICDEX_SEEDPHRASE", "ATOMICDEX_USERPASS",
                "ATOMICDEX_PORT", "ATOMICDEX_IP",
                'SSL_KEY', 'SSL_CERT', 'FASTAPI_PORT',
                "SUBDOMAIN", "DB_PATH", "WEBROOT",
                "NGINX_PROXY_HOST", "FAUCET_COINS",
                "DISCORD_TOKEN"
    ]
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("")
    with open(".env", "r+") as f:
        existing_vars = [k.split("=")[0] for k in f.readlines()]
    with open(".env", "a+") as f:
        vars_to_add = [k for k in req_vars if k not in existing_vars]

        if vars_to_add:
            for var in vars_to_add:
                if var == "ATOMICDEX_SEEDPHRASE":
                    val = generate_seed()
                elif var == "ATOMICDEX_USERPASS":
                    val = generate_rpc_pass(16)
                elif var == "ATOMICDEX_PORT":
                    val = 7783
                elif var == "WEBROOT":
                    home = os.path.expanduser("~")
                    val = f"{home}/fastapi"
                    os.makedirs(val, exist_ok=True)
                elif var == "FAUCET_COINS":
                    val = "RICK MORTY DOC MARTY ZOMBIE"
                elif var == "FASTAPI_PORT":
                    val = 8077
                elif var == "NGINX_PROXY_HOST":
                    val = '127.0.0.1'
                elif var == "ATOMICDEX_IP":
                    val = 'http://127.0.0.1'
                elif var == "DB_PATH":
                    val = 'faucet.db'
                elif var in ["SSL_KEY", "SSL_CERT"]:
                    val = "None"
                else:
                    val = input(f"Value for {var}? [press Enter to skip]: ")
                f.write(f'{var}="{val}"\n')


def create_serverblock():
    home = os.path.expanduser("~")
    script_path = os.path.realpath(os.path.dirname(__file__))
    blockname = f"{script_path}/nginx/fastapi-faucet.serverblock"
    with open(f"{script_path}/nginx/TEMPLATE.serverblock", "r") as r:
        with open(blockname, "w") as w:
            for line in r.readlines():
                line = line.replace("HOMEDIR", home)
                line = line.replace("WEBROOT", os.getenv("WEBROOT"))
                line = line.replace("SUBDOMAIN", os.getenv("SUBDOMAIN"))
                line = line.replace("NGINX_PROXY_HOST", os.getenv("NGINX_PROXY_HOST"))
                line = line.replace("FASTAPI_PORT", os.getenv("FASTAPI_PORT"))
                w.write(f"{line}")
    logger.info(f"NGINX config saved to {blockname}")
    logger.info(f"Activate it with 'sudo ln -s {blockname} /etc/nginx/sites-enabled/fastapi-faucet.serverblock'")
    logger.info(f"Then restart nginx with 'sudo systemctl restart nginx'")


def get_subdomain_ip(subdomain):
    '''Get the IP address of a subdomain to confirm DNS.'''
    try:
        return socket.gethostbyname(subdomain)
    except socket.gaierror as e:
        logger.warning(f"DNS lookup failed for {subdomain}: {e}")
        return None


def update_ssl_env():
    subdomain = os.getenv("SUBDOMAIN")
    if get_subdomain_ip(subdomain):
        with open('.env', 'r', encoding='utf-8') as f:
            data = f.readlines()
            for i in range(len(data)):
                if data[i].find("SSL_KEY") != -1:
                    data[i] = f'SSL_KEY="/etc/letsencrypt/live/{subdomain}/privkey.pem"\n'
                elif data[i].find("SSL_CERT") != -1:
                    data[i] = f'SSL_CERT="/etc/letsencrypt/live/{subdomain}/fullchain.pem"\n'
        with open('.env', 'w', encoding='utf-8') as f:
            f.writelines(data)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "env_vars":
            check_dotenv()
        elif sys.argv[1] == "atomicdex":
            configure_atomicdex('atomicdex')
        elif sys.argv[1] == "nginx":
            create_serverblock()
        elif sys.argv[1] == "ssl_env":
            update_ssl_env()
        else:
            logger.warning("Unknown argument")

