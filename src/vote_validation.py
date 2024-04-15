#!/usr/bin/env python3
import requests
from decimal import Decimal
import lib_rpc
import lib_json

deltas_json = []
rpc = lib_rpc.get_rpc("VOTE2023")
data = requests.get('https://kip0001.smk.dog/api/v3/polls/VOTE2023/info').json()
for cat in data['categories']:
    for option in data['categories'][cat]["options"]:
        addr = option['address']
        candidate = option['candidate']
        print(f'{candidate}: {addr} ({cat})')
        params = {
            "addresses": [addr],
            "start":1,
            "end":51278
        }
        deltas = rpc.getaddressdeltas(params)
        sats = Decimal(0)
        for i in deltas:
            sats += Decimal(i["satoshis"])
        x = {
             "candidate": candidate,
             "region": cat,
             "address": addr,
             "votes": str(round(sats/100000000,8)),
             "deltas": deltas
        }
        deltas_json.append(x)

lib_json.write_jsonfile_data('vote2023_summary.json', deltas_json)


candidate_address_dict = {}
print("/n/n")
for i in deltas_json:
    candidate_address_dict.update({i['address']: f"{i['candidate']}_{i['region']}"})
    print(f"{i['region']}, {i['candidate']}, {i['address']}, {i['votes']}")

lib_json.write_jsonfile_data('vote2023_address_dict.json', candidate_address_dict)
