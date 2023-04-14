#!/usr/bin/env python3
import sys
import requests
import const

def parse_candidates(season):
    base_url = f"https://github.com/KomodoPlatform/NotaryNodes/tree/master/season{season}"
    data = requests.get(f"https://raw.githubusercontent.com/KomodoPlatform/NotaryNodes/master/season{season}/candidates/README.md").text
    candidates = {}
    headers = []
    for line in data.split("\n"):
        if line.startswith("|") and line.find("--") == -1:
            if len(headers) == 0:
                headers = [i.strip() for i in line.split("|")][2:]
                for header in headers:
                    if len(header) > 1:
                        candidates.update({header:{}})
            else:
                line_data = [i.strip() for i in line.split("|")][2:]
                for i in range(len(line_data)):
                    notary = line_data[i].split("]")[0].replace("[", "")
                    if len(notary) > 1:
                        info = line_data[i].split("]")[1].replace("(", "").replace(")", "")
                        proposal = info.split(" ")[0]
                        address = info.split(" ")[1].replace('"', '')
                        candidates[headers[i]].update({
                            notary: {
                                "proposal": f"{base_url}/candidates/{proposal}",
                                "address": address,
                                "qr_code": f'{base_url.replace("tree", "blob")}/qr_codes/{notary}_{headers[i]}.jpg'
                            }
                        })
    return candidates

def enforce_input(q, is_int=False):
    if is_int:
        while True:
            try:
                a = int(input(q))
                if not isinstance(a, int):
                    print("Try again, must be integer!")
                else:
                    return int(a)
            except:
                print("Try again, must be integer!")
    else:
        while True:
            a = input(q)
            if a == "":
                print("Try again, no input!")
            else:
                return a


def add_notary_vote_to_poll_config(candidates, poll_config):
    ticker = enforce_input("Enter chain ticker: ")
    if ticker in poll_config:
        x = ""
        while x.lower() not in ["y", "n"]:
            x = input(f"{ticker} already exists in poll_config_v3.json! Continue [y/n]? ")
            if x.lower() == "n":
                sys.exit()

    explorer = enforce_input("Enter chain explorer: ")
    if explorer.endswith("/"): explorer = explorer[:-1]
    snapshot_at = enforce_input("Enter snapshot timestamp: ", True)
    airdrop_at = enforce_input("Enter airdrop timestamp: ", True)
    starts_at = enforce_input("Enter voting start timestamp: ", True)
    ends_at = enforce_input("Enter voting end timestamp: ", True)

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

    categories = list(candidates.keys())
    for category in categories:
        config[ticker]["categories"].update({
            category: {
                "title": f"Which candidates would you like to serve in the {const.REGIONS[category]} region?",
                "options": []
            }
        })

        
        for candidate in candidates[category]:
            # Todo: Automate generating QR codes
            config[ticker]["categories"][category]["options"].append({
                "candidate": candidate,
                "text": candidates[category][candidate]["proposal"],
                "votes": 0,
                "address": candidates[category][candidate]["address"],
                "qr_code": candidates[category][candidate]["qr_code"]
            })

    
    poll_config.update(config)
    return poll_config