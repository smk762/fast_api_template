#!/usr/bin/env python3
import os
import time
import uvicorn
import requests
from dotenv import load_dotenv
from fastapi_utils.tasks import repeat_every
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, FastAPI, HTTPException, status, APIRouter, Body, Request, Response, status

import lib_poll
import lib_json
import lib_rpc
from lib_logger import logger

load_dotenv()
SSL_KEY = os.getenv("SSL_KEY")
SSL_CERT = os.getenv("SSL_CERT")
RPCIP = os.getenv("KMD_RPCIP")
API_PORT = int(os.getenv("FASTAPI_PORT"))
BALANCES = {}
CURRENT_BLOCK = {}

tags_metadata = []
app = FastAPI(openapi_tags=tags_metadata)

#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=["*"],
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
#)

@app.on_event("startup")
@repeat_every(seconds=15)
def update_data():
    try:
        data = lib_poll.get_data()
        lib_json.write_jsonfile_data('jsondata.json', data)
    except Exception as e:
        logger.info(f"Error in [update_data]: {e}")
        return {"Error: ": str(e)}


@app.get('/api/v1/polls_list', tags=[])
def get_polls_list():
    polls = lib_json.get_jsonfile_data('poll_config.json')
    statuses = lib_poll.get_polls_statuses(polls)
    return statuses


@app.get("/api/v1/polls/{chain}/info", tags=[])
def get_poll_info(chain: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    options = polls[chain]
    return options


@app.get("/api/v1/polls/{chain}/categories", tags=[])
def get_poll_categories(chain: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    categories = list(polls[chain]["categories"].keys())
    return categories


@app.get("/api/v1/polls/{chain}/status", tags=[])
def get_poll_status(chain: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    statuses = lib_poll.get_polls_statuses(polls)
    status = {}
    for i in statuses:
        if chain in statuses[i]:
            status.update({"status": i})
    status.update({
        "snapshot_at": polls[chain]["snapshot_at"],
        "airdrop_at": polls[chain]["airdrop_at"],
        "ends_at": polls[chain]["ends_at"],
        "first_overtime_block": polls[chain]["first_overtime_block"],
        "final_ntx_block": polls[chain]["final_ntx_block"]
    })
    return status


@app.get("/api/v1/polls/{chain}/{category}/info", tags=[])
def get_poll_category_info(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    return polls[chain]["categories"][category]


@app.get("/api/v1/polls/{chain}/{category}/tally", tags=[])
def get_poll_tally(chain: str, category: str):
    options = lib_poll.get_poll_options(chain, category)
    if "error" in options: return options
    for option in options:
        address = options[option]["address"]
        if address in BALANCES:
            votes = BALANCES[address]
        else:
            votes = 0
        options[option].update({"votes": votes})
    return options


@app.get("/api/v1/polls/{chain}/{category}/options", tags=[])
def get_poll_options(chain: str, category: str):
    options = lib_poll.get_poll_options(chain, category)
    return options


@app.get("/api/v1/polls/{chain}/{category}/addresses", tags=[])
def get_poll_options_addresses(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    options = lib_poll.get_poll_options(chain, category)
    if "error" in options: return options
    addresses = {}
    for option in options:
        addresses.update({option: options[option]["address"]})
    return addresses


@app.get("/api/v1/polls/{chain}/{category}/qr_codes", tags=[])
def get_poll_options_qr_codes(chain: str, category: str):
    options = lib_poll.get_poll_options(chain, category)
    if "error" in options: return options
    qr_codes = {}
    for option in options:
        qr_codes.update({option: options[option]["qr_code"]})
    return qr_codes


@app.get("/api/v1/polls/{chain}/{category}/text", tags=[])
def get_poll_options_text(chain: str, category: str):
    options = lib_poll.get_poll_options(chain, category)
    if "error" in options: return options
    option_text = {}
    for option in options:
        option_text.update({option: options[option]["text"]})
    return option_text


@app.get('/api/v1/all_polls', tags=[])
def get_all_polls():
    return lib_json.get_jsonfile_data('poll_config.json')


# TODO: RPC per chain
@app.on_event("startup")
@repeat_every(seconds=5)
def update_poll_data():
    try:
        logger.info("Updating poll data...")
        polls = lib_json.get_jsonfile_data('poll_config.json')
        logger.info(polls)
        lib_poll.update_balances(polls, BALANCES)
        for chain in polls:
            lib_poll.check_polls_overtime(polls, chain)
    except Exception as e:
        logger.warning(f"Error in [update_poll_data]: {e}")
        


@app.on_event("startup")
@repeat_every(seconds=60)
def rpc_getinfo():
    try:
        polls = lib_json.get_jsonfile_data('poll_config.json')
        for chain in polls:
            rpc = lib_rpc.get_rpc(chain)
            logger.info(rpc.getinfo())
    except Exception as e:
        logger.warning(f"RPC (getinfo) not responding: {e}")


if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT, reload=True)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, reload=True)
