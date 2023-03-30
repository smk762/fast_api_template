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
    API_PORT = os.getenv("API_PORT")

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
@repeat_every(seconds=15)
def update_data():
    try:
        data = lib_data.get_data()
        lib_json.write_jsonfile_data('jsondata.json', data)
    except Exception as e:
        logger.info(f"Error in [update_data]: {e}")
        return {"Error: ": str(e)}


@app.get('/api/v1/data', tags=[])
def get_jsonfile_data():
    return lib_json.get_jsonfile_data('jsondata.json')


if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT)
