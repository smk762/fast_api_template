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
from fastapi import (
    Depends,
    Request,
    FastAPI,
    HTTPException,
    status,
    APIRouter,
    Body,
    Request,
    Response,
    status,
)

from lib.config import ConfigFastAPI
from lib.sqlite import SqliteDB
from lib.banxa import BanxaAPI
from lib.ramp import RampAPI
from lib.models import ApiProxyGet
from lib.logger import logger
import lib.json_utils as json_utils


load_dotenv()

config = ConfigFastAPI()
db = SqliteDB(config)
banxa = BanxaAPI()
ramp = RampAPI()

app = FastAPI(openFASTAPI_TAGS=config.FASTAPI["TAGS"])
if config.FASTAPI["USE_MIDDLEWARE"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.FASTAPI["CORS_ORIGINS"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/v1/{org}", tags=["api"])
def get_response(org, request: Request):
    if org == "banxa":
        return banxa.sendGetRequest(request)
    if org == "ramp":
        return ramp.sendGetRequest(request)
    return {
        "error": f"Invalid endpoint {request.query_params['endpoint']} for {org}",
        "query": request.query_params,
    }


@app.post("/api/v1/{org}", tags=["api"])
async def get_response(org, request: Request):
    body = await request.json()
    if org == "banxa":
        payload = json.dumps(body).replace(" ", "")
        return banxa.sendPostRequest(request, payload)
    if org == "ramp":
        return ramp.sendPostRequest(request, body)
    return {
        "error": f"Invalid endpoint {request.query_params['endpoint']} for {org}",
        "query": request.query_params,
        "body": body,
    }


if __name__ == "__main__":
    if config.FASTAPI["SSL_KEY"] != "" and config.FASTAPI["SSL_CERT"] != "":
        uvicorn.run(
            "main:app",
            host=config.FASTAPI["HOST"],
            port=config.FASTAPI["PORT"],
            ssl_keyfile=config.FASTAPI["SSL_KEY"],
            ssl_certfile=config.FASTAPI["SSL_CERT"],
        )
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=config.FASTAPI["FASTAPI_PORT"])
