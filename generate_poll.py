#!/usr/bin/env python3
import sys
import json


with open("poll_config_v2.json", "w+") as f:
    data = json.load(f)
    ticker = input("Enter chain ticker: ")
    if ticker in data:
        x = ""
        while x.lower() not in ["y", "n"]:
            x = input(f"{ticker} already exists in poll_config_v2.json! Continue [y/n]? ")
            if x.lower() == "n":
                sys.exit()
    explorer = input("Enter chain explorer: ")
    snapshot_at = int(input("Enter snapshot timestamp: "))
    airdrop_at = int(input("Enter airdrop timestamp: "))
    starts_at = int(input("Enter voting start timestamp: "))
    ends_at = int(input("Enter voting end timestamp: "))

    config = {
      ticker: {
        "explorer": explorer,
        "categories": {},
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
    }


    categories = {}
    category_count = int(input("How many categories: "))
    for i in range(category_count):
        cat_name = input("Enter category name: ")
        cat_desc = input("Enter category description: ")
        config[ticker]["categories"].update({
            cat_name: {
                "title": cat_desc,
                "options": {}
            }
        })

        option_count = int(input("How many options: "))
        for i in range(option_count):
            opt_name = input("Enter option name: ")
            opt_desc = input("Enter option description: ")
            opt_addr = input("Enter option address: ")
            # Todo: Automate generating these
            opt_qr_url = input("Enter option qrcode url: ")
            config[ticker]["categories"][cat_name]["options"].update({
                opt_name: {
                    "text": opt_desc,
                    "votes": 0,
                    "address": opt_addr,
                    "qr_code": opt_qr_url
                }
            })

    
    data.update(config)
    json.dump(config, f)