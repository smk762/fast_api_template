#!/usr/bin/env python3
import sys
import json


with open("poll_config.json", "r") as f:
    data = json.load(f)
    ticker = input("Enter chain ticker: ")
    if ticker in data:
        x = ""
        while x.lower() not in ["y", "n"]:
            x = input(f"{ticker} already exists in poll_config.json! Continue [y/n]? ")
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
    "results_official": None,
    "overtime_ended_at": None,
    "first_overtime_block": None,
    "final_ntx_block": None,
    "current_block": {},
    "updated_time": 0,
    "status": "new"
    }    
}


categories = {}
while True:
    print(f"1. Notary Election")
    print(f"2. KIP Vote")
    r = input(f"What kind of poll?")
    if r in ["1", "2"]:
        r = int(r)
        break
    print(f"Error, must be either '1' or '2'")

x = 0
y = 0
category_count = 1
if r == 1:
    category_count = 4

for i in range(category_count):
    x += 1
    cat_name = input(f"Enter category {x} name (Region or KIP): ")
    cat_desc = input(f"Enter category {x} title: ")
    config[ticker]["categories"].update({
        cat_name: {
            "title": cat_desc,
            "options": []
        }
    })

    option_count = int(input("How many options: "))
    for i in range(option_count):
        y += 1
        opt_name = input(f"Enter {cat_name} option {y} name: ")
        opt_desc = input(f"Enter {cat_name} option {y} description: ")
        opt_addr = input(f"Enter {cat_name} option {y} address: ")

        config[ticker]["categories"][cat_name]["options"].append({
            "name": str(opt_name),
            "text": str(opt_desc),
            "votes": 0,
            "address": str(opt_addr),
            "qr_code": ""
        })


with open("poll_config.json", "w") as f:
    data.update(config)
    json.dump(data, f, indent=4)