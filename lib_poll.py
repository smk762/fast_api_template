import time
import requests
import lib_rpc
import lib_json
from lib_logger import logger

def get_poll_options(chain, category):
    if chain not in polls.keys():
        return {"error": f"{chain} does not exist!"}
    if category not in polls[chain]["categories"].keys():
        return {"error": f"{chain} has no {category} category!"}
    return polls[chain]["categories"][category]["options"]


def get_polls_statuses(polls):
    now = int(time.time())
    status = {
        "historical": [],
        "active": [],
        "overtime": [],
        "upcoming": []
    }
    for i in polls:
        if polls[i]["starts_at"] > now:
            status["upcoming"].append(i)
        elif polls[i]["ends_at"] > now:
            status["active"].append(i)
        elif polls[i]["overtime_ended_at"]:
            status["historical"].append(i)
        else:
            status["overtime"].append(i)
    return status


def get_notary_addresses():
    r = requests.get(f"https://stats.kmd.io/api/table/addresses/?season=Season_6&server=Main&coin=KMD").json()["results"]
    addresses = [i["address"] for i in r]
    return addresses


def is_ntx(tx_info):
    vouts = tx_info["vout"]
    vins = tx_info["vin"]
    if len(vouts) == 2 and len(vins) == 13:
        vin_addresses = [i["address"] for i in vins]
        notary_addresses = get_notary_addresses()
        if set(vin_addresses).issubset(notary_addresses):
            if vouts[1]["scriptPubKey"]["asm"].find("OP_RETURN") > -1:
                return True
    return False


def get_balance_data(explorer, address):
    balance_data = requests.get(f"{explorer}/insight-api-komodo/addr/{address}").json()
    balance = balance_data["balance"]
    # params = {"addresses": [address]}
    # r = rpc.getaddressbalance(params)
    # balance = r["balance"]/100000000
    return balance


def update_balances(polls, polls_v2, final_block=0):
    try:
        for chain in polls:
            sync_height = get_sync_data(polls[chain]['explorer'])["height"]
            explorer = polls[chain]["explorer"]
            for category in polls[chain]["categories"]:
                for option in polls[chain]["categories"][category]["options"]:
                    address = polls[chain]["categories"][category]["options"][option]["address"]
                    logger.info(f"Getting {chain} balance for {address}")

                    if final_block != 0:
                        rpc = lib_rpc.get_rpc(chain)
                        balance_data = rpc.getaddressdeltas({"addresses": [address], "start":1, "end": final_block})
                        balance = 0
                        for i in balance_data:
                            balance += i["satoshis"]
                        polls[chain]["categories"][category]["options"][option].update({"votes": balance/100000000})
                        polls_v2[chain]["categories"][category]["options"][option].update({"votes": balance/100000000})
                    elif not polls[chain]["final_ntx_block"]:
                        balance = get_balance_data(explorer, address)
                        polls[chain]["categories"][category]["options"][option].update({"votes": balance})
                        polls_v2[chain]["categories"][category]["options"][option].update({"votes": balance})
                    elif sync_height <= polls[chain]["final_ntx_block"]["height"]:
                        balance = get_balance_data(explorer, address)
                        polls[chain]["categories"][category]["options"][option].update({"votes": balance})
                        polls_v2[chain]["categories"][category]["options"][option].update({"votes": balance})
                    else:
                        logger.info(f"Not updating {chain} votes, poll is over.")

    except Exception as e:
        logger.warning(f"Error in [update_balances] for {chain}: {e}")


def update_polls():
    try:
        polls = lib_json.get_jsonfile_data('poll_config.json')
        polls_v2 = lib_json.get_jsonfile_data('poll_config_v2.json')
        now = int(time.time())
        for chain in polls:
            rpc = lib_rpc.get_rpc(chain)
            info = rpc.getinfo()
            polls[chain]["updated_time"] = now
            polls_v2[chain]["updated_time"] = now
            blocktip = info["longestchain"]
            blockinfo = rpc.getblock(str(blocktip))
            block_time = blockinfo["time"]
            block_txids = blockinfo["tx"]
            block_hash = blockinfo["hash"]
            polls[chain]["current_block"] = blocktip
            polls_v2[chain]["current_block"] = {
                "height": blocktip,
                "hash": block_hash,
                "time": block_time,
            }

            if not polls[chain]["final_ntx_block"]:
                update_balances(polls, polls_v2)
                ends_at = polls[chain]["ends_at"]

                if info["tiptime"] > polls[chain]["ends_at"] and not polls_v2[chain]["first_overtime_block"]:
                    polls[chain]["first_overtime_block"] = blocktip
                    polls_v2[chain]["first_overtime_block"] = {
                        "height": blocktip,
                        "hash": block_hash,
                        "time": block_time,
                    }

                if polls[chain]["first_overtime_block"]:
                    polls[chain]["status"] = "overtime"
                    polls_v2[chain]["status"] = "overtime"
                    if blocktip >= polls_v2[chain]["first_overtime_block"]["height"]:
                        logger.info(f"longestchain: {blocktip}")
                        for i in range(polls_v2[chain]["first_overtime_block"]["height"], blocktip+1):
                            logger.info(f"Scanning block: {i}")
                            for txid in block_txids:
                                tx_info = rpc.getrawtransaction(txid, 1)
                                if is_ntx(tx_info):
                                    logger.info(f"ntx found in: {i}")
                                    blockinfo = rpc.getblock(str(i))
                                    polls[chain]["final_ntx_block"] = i
                                    polls_v2[chain]["final_ntx_block"] = {
                                        "height": i,
                                        "hash": blockinfo["hash"],
                                        "time": blockinfo["time"],
                                    }

                                    polls[chain]["overtime_ended_at"] = block_time
                                    polls[chain]["status"] = "historical"
                                    polls_v2[chain]["overtime_ended_at"] = block_time
                                    polls_v2[chain]["status"] = "historical"
                                    update_balances(polls, polls_v2, i)
                                    lib_json.write_jsonfile_data('poll_config.json', polls)
                                    lib_json.write_jsonfile_data('poll_config_v2.json', polls_v2)
                                    return
                lib_json.write_jsonfile_data('poll_config.json', polls)
                lib_json.write_jsonfile_data('poll_config_v2.json', polls_v2)

    except Exception as e:
        logger.warning(f"RPC (overtime getinfo) not responding! {e}")


def get_sync_data(explorer):
    return requests.get(f"{explorer}/insight-api-komodo/sync").json()


if __name__ == '__main__':
    rpc = lib_rpc.get_rpc("KIP0001")
    tx_info = rpc.getrawtransaction("0a95b1ecf0163640d5e631767877fa745f40bf9480631b1f9c5f64a953c3b1c7", 1)
    print(is_ntx(tx_info))
    assert is_ntx(tx_info)
    tx_info = rpc.getrawtransaction("dfc390cf85a40dac5c4b3ec6540f32ba229610a14039cb1f30afec9cdddf8c34", 1)
    print(is_ntx(tx_info))
    assert not is_ntx(tx_info)

    balance_data = rpc.getaddressdeltas({"addresses": ["RReduceRewardsXXXXXXXXXXXXXXUxPxuC"], "start":1, "end": 19925})
    balance = 0
    for i in balance_data:
        balance += i["satoshis"]
    print(balance/100000000)

    balance_data = rpc.getaddressdeltas({"addresses": ["RKeepRewardsXXXXXXXXXXXXXXXXYKRSuF"], "start":1, "end": 19925})
    balance = 0
    for i in balance_data:
        balance += i["satoshis"]
    print(balance/100000000)
