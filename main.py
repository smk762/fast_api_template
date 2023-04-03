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

import lib_rpc
import lib_data
import lib_json
from lib_logger import logger

load_dotenv()
SSL_KEY = os.getenv("SSL_KEY")
SSL_CERT = os.getenv("SSL_CERT")

CORS_ORIGINS = []
if os.getenv("CORS_ORIGINS"):
    CORS_ORIGINS = os.getenv("CORS_ORIGINS").split(" ")

API_PORT = 8080
if os.getenv("API_PORT"):
    API_PORT = int(os.getenv("API_PORT"))

tags_metadata = []
app = FastAPI(openapi_tags=tags_metadata)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
@repeat_every(seconds=60)
def update_data():
    data = {}
    for coin in lib_rpc.DEAMONS:
        print(coin)
        try:
            rpc = lib_rpc.get_rpc(coin)
            info = rpc.getinfo()
            data.update({
                coin: {
                    "longestchain": info["longestchain"],
                    "tiptime": info["tiptime"],
                    "notarized": info["notarized"],
                    "balance": info["balance"],
                    "synced": info["synced"],
                    "difficulty": info["difficulty"]
                }
            })
        except Exception as e:
            logger.info(f"Error in [update_data]: {e}")
            return {"Error: ": str(e)}
    lib_json.write_jsonfile_data('blocks_data.json', data)


@app.get('/api/v1/last_block', tags=[])
def get_last_block_data():
    return lib_json.get_jsonfile_data('blocks_data.json')



if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT)
