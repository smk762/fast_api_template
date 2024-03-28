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
from coins.utils import scan_electrums as scan

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
@repeat_every(seconds=600)
def update_data():
    try:
        logger.info("Updating electrum status")
        scan.get_electrums_report()
        with open(f'{script_dir}/coins/utils/electrum_scan_report.json') as f:
            data = json.load(f)
        electrum_coins = list(data.keys())
        db_coins = lib_sqlite.get_db_coins()
        print(electrum_coins)
        print(db_coins)
        for coin in db_coins:
            if coin not in electrum_coins:
                print(f"Deleting {coin}")
                lib_sqlite.delete_electrum_coin(coin)
        logger.info("Electrum status table updated!")
        for coin in data:
            for protocol in ["tcp", "ssl", "wss"]:
                for server in data[coin][protocol]:
                    result = data[coin][protocol][server]['result'].replace("'", "")
                    last = data[coin][protocol][server]['last_connection']
                    if result == "Passed":
                        row = (coin, server, protocol, result, last)
                        lib_sqlite.update_electrum_row(row)
                    else:
                        row = (coin, server, protocol, result, last)
                        lib_sqlite.update_electrum_row_failed(row)
    except Exception as e:
        logger.error(f"Electrum status scan update Failed! {e}")


@app.get('/api/v1/electrums_status', tags=[])
def get_electrums_status():
    data = lib_sqlite.get_electrum_status_data()
    resp = [{k: item[k] for k in item.keys()} for item in data]
    return resp


if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT)
