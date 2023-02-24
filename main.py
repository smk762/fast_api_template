#!/usr/bin/env python3
import os
import uvicorn
import requests
from dotenv import load_dotenv
from fastapi_utils.tasks import repeat_every
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, FastAPI, HTTPException, status, APIRouter, Body, Request, Response, status

import lib_data
import lib_json
import lib_rpc
from lib_logger import logger

load_dotenv()
SSL_KEY = os.getenv("SSL_KEY")
SSL_CERT = os.getenv("SSL_CERT")


tags_metadata = []
app = FastAPI(openapi_tags=tags_metadata)


@app.on_event("startup")
@repeat_every(seconds=15)
def update_data():
    try:
        data = lib_data.get_data()
        lib_json.write_jsonfile_data('jsondata.json', data)
    except Exception as e:
        logger.info(f"Error in [update_data]: {e}")
        return {"Error: ": str(e)}


@app.get('/api/v1/polls_list', tags=[])
def get_polls_list():
    polls = lib_json.get_jsonfile_data('poll_config.json')
    statuses = lib_data.get_polls_statuses(polls)
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
    statuses = lib_data.get_polls_statuses(polls)
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
    return {}


@app.get("/api/v1/polls/{chain}/{category}/options", tags=[])
def get_poll_options(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    options = polls[chain]["categories"][category]["options"]
    return options


@app.get("/api/v1/polls/{chain}/{category}/addresses", tags=[])
def get_poll_options_addresses(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    options = polls[chain]["categories"][category]["options"]
    addresses = {}
    for option in options:
        addresses.update({option: options[option]["address"]})
    return addresses


@app.get("/api/v1/polls/{chain}/{category}/qr_codes", tags=[])
def get_poll_options_qr_codes(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    options = polls[chain]["categories"][category]["options"]
    qr_codes = {}
    for option in options:
        qr_codes.update({option: options[option]["qr_code"]})
    return qr_codes


@app.get("/api/v1/polls/{chain}/{category}/text", tags=[])
def get_poll_options_text(chain: str, category: str):
    polls = lib_json.get_jsonfile_data('poll_config.json')
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    options = polls[chain]["categories"][category]["options"]
    option_text = {}
    for option in options:
        option_text.update({option: options[option]["text"]})
    return option_text


@app.get('/api/v1/all_polls', tags=[])
def get_all_polls():
    return lib_json.get_jsonfile_data('poll_config.json')


# TODO: RPC per chain
@app.on_event("startup")
@repeat_every(seconds=10)
def rpc_getinfo():
    polls = lib_json.get_jsonfile_data('poll_config.json')
    for i in polls:
        if abs(polls[i]["ends_at"] - time.time()) < 120:
            try:
                rpc = lib_rpc.get_rpc(rpcuser, rpcpass, rpcport)
                info = rpc.getinfo()
                if info["tiptime"] > polls[i]["ends_at"] and not polls[i]["first_overtime_block"]:
                    polls[i]["first_overtime_block"] = info["longestchain"]
                    last_ntx = requests.get(f"https://stats.kmd.io/api/source/coin_last_ntx/?coin={i}&season=Season_6").json()["results"]
                    ac_ntx_height = last_ntx["ac_ntx_height"]
                    if ac_ntx_height > polls[i]["first_overtime_block"] and not polls[i]["final_ntx_block"]:
                        polls[i]["final_ntx_block"] = ac_ntx_height

                    lib_json.write_jsonfile_data('poll_config.json', polls)

            except Exception as e:
                logger.warning(f"RPC not responding! {e}")


@app.on_event("startup")
@repeat_every(seconds=60)
def rpc_getinfo():
    try:
        rpc = lib_rpc.get_rpc(rpcuser, rpcpass, rpcport)
        logger.info(rpc.getinfo())
    except:
        logger.warning("RPC not responding!")    


if __name__ == '__main__':
    if SSL_KEY != "" and SSL_CERT != "":
        uvicorn.run("main:app", host="0.0.0.0", port=8080, ssl_keyfile=SSL_KEY, ssl_certfile=SSL_CERT, reload=True)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
