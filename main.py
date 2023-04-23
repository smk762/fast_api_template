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

from lib.const import ConfigFastAPI
from lib.sqlite import SqliteDB

from lib.logger import logger
import lib.api_proxy as api_proxy
import lib.json_utils as json_utils
import lib.moralis_api as moralis_api


load_dotenv()

config = ConfigFastAPI()
db = SqliteDB(config)

app = FastAPI(openapi_tags=config.API_TAGS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
@repeat_every(seconds=15)
def update_data():
    try:
        data = api_proxy.get_data()
        json_utils.write_jsonfile_data('jsondata.json', data)
    except Exception as e:
        logger.info(f"Error in [update_data]: {e}")
        return {"Error: ": str(e)}


@app.get('/api/v1/get_wallet_nfts', tags=[""])
def get_wallet_nfts():
    return moralis_api.get_wallet_nfts("eth", "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")


@app.get('/api/v1/get_wallet_nft_transfers', tags=[""])
def get_wallet_nft_transfers():
    return moralis_api.get_wallet_nft_transfers("eth", "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")


@app.get('/api/v1/get_nft_metadata', tags=[""])
def get_nft_metadata():
    return moralis_api.get_nft_metadata("eth", "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB", token_id="1")


if __name__ == '__main__':
    if config.SSL_KEY != "" and config.SSL_CERT != "":
        uvicorn.run("main:app", host=config.API_HOST,
                                port=config.API_PORT,
                                ssl_keyfile=config.SSL_KEY,
                                ssl_certfile=config.SSL_CERT)
    else:
        uvicorn.run("main:app", host=config.API_HOST,
                                port=config.API_PORT)
