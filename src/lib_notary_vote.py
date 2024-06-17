#!/usr/bin/env python3
import sys
import requests
import const
import lib_poll
from validate import enforce_input
from lib_logger import logger


def update_notary_vote(candidates, poll_config, vote_chain, loop=False):
    if vote_chain not in poll_config and loop is False:
        explorer = enforce_input("Enter chain explorer: ")
        if explorer.endswith("/"):
            explorer = explorer[:-1]
        snapshot_at = enforce_input("Enter snapshot timestamp: ", True)
        airdrop_at = enforce_input("Enter airdrop timestamp: ", True)
        starts_at = enforce_input("Enter voting start timestamp: ", True)
        ends_at = enforce_input("Enter voting end timestamp: ", True)
        poll_config.update({
            vote_chain: {
                "explorer": explorer,
                "categories": list(const.REGIONS.keys()),
                "snapshot_at": snapshot_at,
                "airdrop_at": airdrop_at,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "overtime_ended_at": None,
                "first_overtime_block": None,
                "final_ntx_block": None,
                "current_block": {},
                "updated_time": 0,
                "status": "new"
            }    
        })

    categories = poll_config[vote_chain]['categories']
    for region in categories:
        logger.calc(f"Updating {region} region candidates for {vote_chain}")
        # logger.merge(poll_config[vote_chain]["categories"][region])
        existing_region_candidates = {
            i['candidate']: i['votes'] for i in
            poll_config[vote_chain]["categories"][region]['options']
        }
        # logger.loop(existing_region_candidates)
        poll_config[vote_chain]["categories"].update({
            region: {
                "title": f"Which candidates would you like to serve in the {const.REGIONS[region]} region?",
                "options": []
            }
        })

        
        for i in candidates[region]:
            candidate = i['candidate']
            votes = 0
            if candidate in existing_region_candidates:
                votes = 0
            x = {
                "address": i["address"],
                "candidate": i["candidate"],
                "qr_code": i["qr_code"],
                "text": i["text"],
                "votes": votes
            }
            if vote_chain.startswith("VOTE"):
                x.update({
                    "veteran": lib_poll.is_veteran(candidate),
                    "testnet": lib_poll.get_testnet_ids(vote_chain, candidate)
                })
            poll_config[vote_chain]["categories"][region]["options"].append(x)

    return poll_config
