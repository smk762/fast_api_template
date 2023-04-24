import time
import json
import requests
import lib_rpc
import lib_json
from lib_logger import logger
import lib_sqlite as db

def get_poll_options(polls, coin, category):
    if coin not in polls.keys():
        return {"error": f"{coin} does not exist!"}
    if category not in polls[coin]["categories"].keys():
        return {"error": f"{coin} has no {category} category!"}
    return polls[coin]["categories"][category]["options"]


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
                ntx_data = requests.get(f'https://stats.kmd.io/api/tools/decode_opreturn/?OP_RETURN={vouts[1]["scriptPubKey"]["asm"]}').json()
                return ntx_data
    return None


def get_balance_data(explorer, address):
    balance_data = requests.get(f"{explorer}/insight-api-komodo/addr/{address}").json()
    balance = balance_data["balance"]
    # params = {"addresses": [address]}
    # r = rpc.getaddressbalance(params)
    # balance = r["balance"]/100000000
    return balance


def sort_by_time(data):
    r = sorted(data, key=lambda x: x["time"])
    return r


def get_txid_time(explorer, txid):
    tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
    return tx_info["blocktime"]


def get_address_utxos(explorer, address):
    try:
        reduced = []
        utxos = requests.get(f"{explorer}/insight-api-komodo/addr/{address}/utxo").json()
        for utxo in utxos:
            utxo_time = get_txid_time(explorer, utxo["txid"])
            reudced_utxo = {
                "txid": utxo["txid"],
                "amount": utxo["amount"],
                "height": utxo["height"],
                "time": utxo_time
            }
            reduced.append(reudced_utxo)
        return reduced
    except Exception as e:
        logger.warning(f"Error in [get_address_utxos]: {e}")
        return []


def get_address_balance(balances, address, final_block=None):
    if final_block:
        balance = [i["votes"] for i in balances if i["address"] == address and i["height"] <= final_block]
    else:
        balance = [i["votes"] for i in balances if i["address"] == address]
    if len(balance) > 0:
        balance = balance[0]
        return round(balance, 4)
    else:
        return 0
                            

def update_balances(polls, final_block=0, testnet=False):
    try:
        for coin in polls:
            existing_txids = db.VoteTXIDs(coin)
            poll_txids = existing_txids.get_txids()
            poll_txid_list = [i["txid"] for i in poll_txids]
            balances = existing_txids.get_sum_by_address()
            balances = [dict(i) for i in balances]
            # logger.info(balances)
            sync_height = get_sync_data(polls[coin]['explorer'])["height"]
            explorer = polls[coin]["explorer"]
            all_utxos = []
            for category in polls[coin]["categories"]:
                for option in polls[coin]["categories"][category]["options"]:
                    address = option["address"]
                    candidate = option["candidate"]

                    testnet_ids = []
                    for k, v in testnet.items():
                        if candidate == v:
                            testnet_ids.append(k)
                    option.update({"testnet": testnet_ids})
                    row = db.VoteRow()
                    row.coin = coin
                    row.address = address
                    row.category = category
                    row.option = candidate

                    if final_block != 0:
                        balance = get_address_balance(balances, address, final_block)

                    elif not polls[coin]["final_ntx_block"]:
                        utxos = get_address_utxos(explorer, address)
                        for utxo in utxos:
                            if utxo["txid"] not in poll_txid_list:
                                if "height" in utxo.keys():
                                    row.txid = utxo["txid"]
                                    row.amount = utxo["amount"]
                                    row.blockheight = utxo["height"]
                                    row.blocktime = utxo["time"]
                                    row.insert()

                            utxo.update({
                                "candidate": candidate,
                                "region": category
                            })
                        all_utxos += utxos
                        option.update({
                            "votes": get_address_balance(balances, address),
                            "utxos": utxos,
                        })

                    elif sync_height <= polls[coin]["final_ntx_block"]["height"]:
                        utxos = get_address_utxos(explorer, address)
                        logger.info(f"{len(utxos)} {coin} utxos for {address}")
                        for utxo in utxos:
                            if utxo["txid"] not in poll_txid_list:
                                if "height" in utxo.keys():
                                    row.txid = utxo["txid"]
                                    row.amount = utxo["amount"]
                                    row.blockheight = utxo["height"]
                                    row.blocktime = utxo["time"]
                                    row.insert()
                            utxo.update({
                                "candidate": candidate,
                                "region": category
                            })
                        all_utxos += utxos
                        option.update({
                            "votes": get_address_balance(balances, address),
                            "utxos": utxos,
                        })
                    else:
                        logger.info(f"Not updating {coin} votes, poll is over.")
            if all_utxos:
                sorted_utxos = sort_by_time(all_utxos)
                sorted_utxos.reverse()
                last_100 = sorted_utxos[:100]
                sum_utxos = sum([i["amount"] for i in sorted_utxos])
                polls[coin].update({
                    "recent_votes": sorted_utxos[:100],
                    "sum_votes": sum_utxos,
                    "count_votes": len(sorted_utxos)
                })


    except Exception as e:
        logger.warning(f"Error in [update_balances] for {coin}: {e}")


def update_polls():
    try:
        polls = lib_json.get_jsonfile_data('poll_config_v3.json')
        if not polls:
            polls = {}
        now = int(time.time())
        for coin in polls:
            testnet = lib_json.get_jsonfile_data(f'testnet_{coin}.json')
            rpc = lib_rpc.get_rpc(coin)
            info = rpc.getinfo()
            polls[coin]["updated_time"] = now
            blocktip = info["longestchain"]
            blockinfo = rpc.getblock(str(blocktip))
            block_time = blockinfo["time"]
            block_txids = blockinfo["tx"]
            block_hash = blockinfo["hash"]
            polls[coin]["current_block"] = {
                "height": blocktip,
                "hash": block_hash,
                "time": block_time,
            }

            if not polls[coin]["final_ntx_block"]:
                update_balances(polls, testnet=testnet)
                ends_at = polls[coin]["ends_at"]

                if polls[coin]["first_overtime_block"]:
                    polls[coin]["status"] = "overtime"
                    if blocktip >= polls[coin]["first_overtime_block"]["height"]:
                        logger.info(f"longestchain: {blocktip}")
                        for i in range(polls[coin]["first_overtime_block"]["height"], blocktip+1):
                            logger.info(f"Scanning block: {i}")
                            for txid in block_txids:
                                tx_info = rpc.getrawtransaction(txid, 1)
                                if is_ntx(tx_info):
                                    ntx_data = is_ntx(tx_info)["results"]
                                    logger.info(f"ntx for block {ntx_data['notarised_block']} found in: {i}")
                                    if ntx_data['notarised_block'] >= polls[coin]["first_overtime_block"]:
                                        blockinfo = rpc.getblock(str(ntx_data['notarised_block']))
                                        polls[coin]["final_ntx_block"] = {
                                            "height": ntx_data['notarised_block'],
                                            "hash": blockinfo["hash"],
                                            "time": blockinfo["time"],
                                        }
                                        polls[coin].update({"final_ntx_block_tx": txid})

                                        polls[coin]["overtime_ended_at"] = block_time
                                        polls[coin]["status"] = "historical"
                                        update_balances(polls, ntx_data['notarised_block'], testnet=testnet)
                                        lib_json.write_jsonfile_data('poll_config_v3.json', polls)
                                        return

                elif info["tiptime"] > polls[coin]["ends_at"]:
                    polls[coin]["first_overtime_block"] = {
                        "height": blocktip,
                        "hash": block_hash,
                        "time": block_time,
                    }

                lib_json.write_jsonfile_data('poll_config_v3.json', polls)

    except Exception as e:
        logger.warning(f"RPC (overtime getinfo) not responding! {e}")


def get_sync_data(explorer):
    url = f"{explorer}/insight-api-komodo/sync"
    return requests.get(url).json()


if __name__ == '__main__':
    rpc = lib_rpc.get_rpc("KIP0001")
    tx_info = rpc.getrawtransaction("0a95b1ecf0163640d5e631767877fa745f40bf9480631b1f9c5f64a953c3b1c7", 1)
    logger.info(is_ntx(tx_info))
    assert is_ntx(tx_info)
    tx_info = rpc.getrawtransaction("dfc390cf85a40dac5c4b3ec6540f32ba229610a14039cb1f30afec9cdddf8c34", 1)
    logger.info(is_ntx(tx_info))
    assert not is_ntx(tx_info)

    balance_data = rpc.getaddressdeltas({"addresses": ["RReduceRewardsXXXXXXXXXXXXXXUxPxuC"], "start":1, "end": 19925})
    balance = 0
    for i in balance_data:
        balance += i["satoshis"]
    logger.info(balance/100000000)

    balance_data = rpc.getaddressdeltas({"addresses": ["RKeepRewardsXXXXXXXXXXXXXXXXYKRSuF"], "start":1, "end": 19925})
    balance = 0
    for i in balance_data:
        balance += i["satoshis"]
    logger.info(balance/100000000)
