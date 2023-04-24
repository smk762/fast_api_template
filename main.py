#!/usr/bin/env python3
import os
import time
import random
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
import const
import lib_sqlite as db
from lib_logger import logger

load_dotenv()


BALANCES = {}
CURRENT_BLOCK = {}
RPCIP = os.getenv("KMD_RPCIP")
API_PORT = const.get_api_port()
VOTE_ACTIVE = time.time() < 1682899199
SSL_KEY, SSL_CERT = const.get_ssl_certs()
API_ADDRESS = "RTj2SYWR7AM5fGN1RHSatpnmHSwyNsvz1p"


tags_metadata = []

def create_app():
    print("Creating app...")
    db.create_tbl()
    app = FastAPI(openapi_tags=tags_metadata)
    return app

app = create_app()


#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=["*"],
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
#)


# Update poll data
@app.on_event("startup")
@repeat_every(seconds=20)
def update_poll_data():
    try:
        logger.info("Updating poll data...")
        lib_poll.update_polls()
        logger.info("Poll data updated!")
    except Exception as e:
        logger.warning(f"Error in [update_poll_data]: {e}")
       

# TX generator
@app.on_event("startup")
@repeat_every(seconds=30)
def move_chains():
    try:
        polls = lib_json.get_jsonfile_data('poll_config_v3.json')
        if not polls:
            polls = {}
        chains = polls.keys()
        for chain in chains:
            rpc = lib_rpc.get_rpc(chain)
            logger.info(f"{chain} sendtoaddress {API_ADDRESS} 0.00762")
            logger.info(rpc.sendtoaddress(API_ADDRESS, 0.00762))
    except Exception as e:
        logger.error(e)
 

@app.on_event("startup")
@repeat_every(seconds=60)
def rpc_getinfo():
    try:
        polls = lib_json.get_jsonfile_data('poll_config_v3.json')
        if not polls:
            polls = {}
        for chain in polls:
            rpc = lib_rpc.get_rpc(chain)
            #logger.info(rpc.getinfo())
    except Exception as e:
        logger.warning(f"RPC (getinfo) not responding: {e}")


@app.on_event("startup")
@repeat_every(seconds=915)
def update_candidates():
    if VOTE_ACTIVE:
        try:
            votes = {}
            poll_data = lib_json.get_jsonfile_data('poll_config_v3.json')
            for region in poll_data["VOTE2023"]["categories"]:
                if region not in votes:
                    votes.update({region: {}})
                for i in poll_data["VOTE2023"]["categories"][region]["options"]:
                    votes[region].update({i["candidate"]: i["votes"]})


            candidates_data = requests.get("https://raw.githubusercontent.com/KomodoPlatform/NotaryNodes/master/season7/candidates.json").json()                    
            for region in candidates_data:
                for i in candidates_data[region]:
                    if i["candidate"] in votes[region]:
                        i.update({"votes": votes[region][i["candidate"]]})
                    else:
                        i.update({"votes": 0})
            
            for region in poll_data["VOTE2023"]["categories"]:
                poll_data["VOTE2023"]["categories"][region]["options"] = candidates_data[region]

            lib_json.write_jsonfile_data('poll_config_v3.json', poll_data)
        except Exception as e:
            logger.error(e)



@app.get('/api/v3/polls_list', tags=[])
def get_polls_v3_list():
    polls = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    statuses = lib_poll.get_polls_statuses(polls)
    return statuses


@app.get("/api/v3/polls/{chain}/info", tags=[])
def get_poll_info(chain: str):
    polls = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    options = polls[chain]
    return options


@app.get("/api/v3/polls/{chain}/categories", tags=[])
def get_poll_categories(chain: str):
    polls = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    categories = list(polls[chain]["categories"].keys())
    return categories


@app.get("/api/v3/polls/{chain}/status", tags=[])
def get_poll_status(chain: str):
    polls = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
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
        "overtime_ended_at": polls[chain]["overtime_ended_at"],
        "first_overtime_block": polls[chain]["first_overtime_block"],
        "current_block": polls[chain]["current_block"],
        "updated_time": polls[chain]["updated_time"],
        "final_ntx_block": polls[chain]["final_ntx_block"]
    })
    return status


@app.get("/api/v3/polls/{chain}/{category}/info", tags=[])
def get_poll_category_info(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    return polls[chain]["categories"][category]


@app.get("/api/v3/polls/{chain}/{category}/tally", tags=[])
def get_poll_tally(chain: str, category: str):
    polls_v3 = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    options = lib_poll.get_poll_options(polls_v3, chain, category)
    tally = {}
    for option in options:
        tally.update({options[option]["address"]: options[option]["votes"]})
    return tally


@app.get("/api/v3/polls/{chain}/{category}/options", tags=[])
def get_poll_options(chain: str, category: str):
    polls_v3 = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    options = lib_poll.get_poll_options(polls_v3, chain, category)
    return options


@app.get("/api/v3/polls/{chain}/{category}/addresses", tags=[])
def get_poll_options_addresses(chain: str, category: str):
    polls_v3 = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    options = lib_poll.get_poll_options(polls_v3, chain, category)
    if "error" in options: return options
    addresses = {}
    for option in options:
        addresses.update({option: options[option]["address"]})
    return addresses


@app.get("/api/v3/polls/{chain}/{category}/qr_codes", tags=[])
def get_poll_options_qr_codes(chain: str, category: str):
    polls_v3 = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    options = lib_poll.get_poll_options(polls_v3, chain, category)
    if "error" in options: return options
    qr_codes = {}
    for option in options:
        qr_codes.update({option: options[option]["qr_code"]})
    return qr_codes


@app.get("/api/v3/polls/{chain}/{category}/text", tags=[])
def get_poll_options_text(chain: str, category: str):
    polls_v3 = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    options = lib_poll.get_poll_options(polls_v3, chain, category)
    if "error" in options: return options
    option_text = {}
    for option in options:
        option_text.update({option: options[option]["text"]})
    return option_text


@app.get('/api/v3/all_polls', tags=[])
def get_all_polls():
    polls = lib_json.get_jsonfile_data('poll_config_v3.json')
    if not polls:
        polls = {}
    return polls

if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT, reload=True)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, reload=True)
