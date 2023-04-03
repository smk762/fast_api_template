#!/usr/bin/env python3
import sys
import time
import requests
import lib_rpc
import lib_json
import lib_poll
from lib_logger import logger

def validate(poll_data, coin):
    rpc = lib_rpc.get_rpc(coin)
    poll_data = lib_json.get_jsonfile_data("poll_config_v2.json")
    final_ntx_block_height = poll_data[coin]["final_ntx_block"]["height"]
    final_ntx_block_hash = poll_data[coin]["final_ntx_block"]["hash"]
    notarisation_tx = poll_data[coin]["final_ntx_block_tx"]
    first_overtime_block = poll_data[coin]["first_overtime_block"]["height"]    
    tx_info = rpc.getrawtransaction(notarisation_tx, 1)
    ntx_data = lib_poll.is_ntx(tx_info)

    if not ntx_data:
        logger.error(f"final_ntx_block_tx {notarisation_tx} is not a notarisation tx!")
        sys.exit()
    else:
        ntx_data = ntx_data["results"]
        if ntx_data["notarised_block"] != final_ntx_block_height:
            logger.error(f"final_ntx_block {final_ntx_block_height} does not match notarised_block {ntx_data['notarised_block']} in final_ntx_block_tx {notarisation_tx}!")
            sys.exit()
        if ntx_data["notarised_blockhash"] != final_ntx_block_hash:
            logger.error(f"final_ntx_block_hash {final_ntx_block_hash} does not match notarised_blockhash {ntx_data['notarised_blockhash']} in final_ntx_block_tx {notarisation_tx}!")
            sys.exit()
        if final_ntx_block_height < first_overtime_block:
            logger.error(f"final_ntx_block {final_ntx_block_height} is less than first_overtime_block {first_overtime_block}!")
            sys.exit()
    
    explorer_url = poll_data[coin]["explorer"]
    print(f"\nnotarisation_tx: {explorer_url}/tx/{notarisation_tx}")
    print(f"final_ntx_block: {explorer_url}/block-index/{final_ntx_block_height}")
    print(f"final_ntx_blockhash: {explorer_url}/block/{final_ntx_block_hash}")


    for category in poll_data[coin]["categories"]:
        for option in poll_data[coin]["categories"][category]["options"]:
            address = poll_data[coin]["categories"][category]["options"][option]["address"]
            balance_data = rpc.getaddressdeltas({"addresses": [address], "start":1, "end": final_ntx_block_height})

            poll_data[coin]["categories"][category]["options"][option].update({"address_deltas":balance_data})
            voter_addresses = []
            balance = 0
            for i in balance_data:
                balance += i["satoshis"]
                tx_info = rpc.getrawtransaction(i["txid"], 1)
                for vin in tx_info["vin"]:
                    vin_address = vin["address"]
                    if vin_address not in voter_addresses:
                        voter_addresses.append(vin_address)
            balance = balance/100000000
            print(f"\n{address} validated balance: {balance}")
            print(f"{address} voters: {len(voter_addresses)}")
            print(f"Average vote per address: {balance/len(voter_addresses)}")


    lib_json.write_jsonfile_data(f"{coin}_poll_results.json", poll_data[coin])


if __name__ == '__main__':
    # Load config
    poll_data = lib_json.get_jsonfile_data("poll_config_v2.json")
    coin = input("Enter ticker of chain to validate: ")
    if coin not in poll_data:
        logger.error(f"{coin} not found in poll_config_v2.json!")
        sys.exit()
    else:
        logger.info(f"Validating {coin}...")
        validate(poll_data, coin)


