#!/usr/bin/env python3
import os
import json
import time
import json
import uvicorn
import requests
from dotenv import load_dotenv
from fastapi_utils.tasks import repeat_every
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, FastAPI, HTTPException, status, APIRouter, Body, Request, Response, status

import lib_sqlite
import lib_data
import lib_json
from lib_logger import logger
import lib_coins as scan

script_dir = os.path.abspath( os.path.dirname( __file__ ) )

load_dotenv()
SSL_KEY = os.getenv("SSL_KEY")
SSL_CERT = os.getenv("SSL_CERT")
API_PORT = os.getenv("API_PORT")
if not API_PORT:
    API_PORT = 8999

tags_metadata = []
#app = FastAPI(openapi_tags=tags_metadata)
app = FastAPI()


cors_origins = [
    "http://localhost:3000",
    "http://116.203.120.91:8762/",
    "http://stats.kmd.io",
    "https://116.203.120.91:8762/",
    "https://stats.kmd.io",
    "https://vote.komodoplatform.com",
    "http://vote.komodoplatform.com",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
@repeat_every(seconds=120)
def update_data():
    try:
        logger.info("Updating electrum status")
        scan.get_electrums_report()
    except Exception as e:
        logger.error(f"Electrum status scan update Failed! {e}")

@app.on_event("startup")
@repeat_every(seconds=60)
def update_db():
    try:
        logger.query("Updating electrum db")
        scan.update_db()
    except Exception as e:
        logger.error(f"Electrum update_db Failed! {e}")

@app.on_event("startup")
@repeat_every(seconds=3600)
def update_coins_data():
    try:
        url = "https://raw.githubusercontent.com/KomodoPlatform/coins/6914dbe31c71c9aa54851ae96350f542347f8f32/utils/coins_config_unfiltered.json"
        # url = "https://komodoplatform.github.io/coins/utils/coins_config_unfiltered.json"
        data = requests.get(url).json()
        with open(f"{script_dir}/coins_config.json", "w+") as f:
            json.dump(data, f, indent=2)
        logger.query("Updating coins_config")
        scan.update_db()
    except Exception as e:
        logger.error(f"coins_config update Failed! {e}")


@app.get('/api/v1/electrums_status', tags=[])
def get_electrums_status(coin: str = None):
    data = lib_sqlite.get_electrum_status_data()
    if coin is not None:
        return [{k: item[k] for k in item.keys()} for item in data if item['coin'] == coin]
    return [{k: item[k] for k in item.keys()} for item in data]


@app.get('/api/v1/coins_status', tags=[])
def get_coins_status(coin: str = None):
    resp = {}
    data = lib_sqlite.get_electrum_status_data()
    status = [{k: item[k] for k in item.keys()} for item in data]
    for i in status:
        _coin = i["coin"]
        result = i["result"]
        protocol = i["protocol"]
        blockheight = i["blockheight"]
        if _coin not in resp:
            resp.update({_coin: {
                "coin": _coin,
                "TCP": False,
                "SSL": False,
                "WSS": False,
                "blockheight": blockheight
            }})
        if result == "Passed":
            resp[_coin][protocol] = True
            resp[_coin]["blockheight"] = blockheight
    if coin is not None:
        return [i for i in resp.values() if i['coin'] == coin] 
    return [i for i in resp.values()] 


if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT)
