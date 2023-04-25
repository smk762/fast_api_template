import time
import json
import requests
import lib_rpc
import lib_json
from lib_logger import logger
import lib_sqlite as db


SELF_SEND_TXIDS = []

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
    if "blocktime" in tx_info:
        return tx_info["blocktime"]
    else:
        return False


def get_address_utxos(explorer, address):
    try:
        reduced = []
        utxos = requests.get(f"{explorer}/insight-api-komodo/addr/{address}/utxo").json()
        for utxo in utxos:
            utxo_time = get_txid_time(explorer, utxo["txid"])
            if utxo_time and utxo["txid"] not in SELF_SEND_TXIDS:
                reduced_utxo = {
                    "txid": utxo["txid"],
                    "amount": utxo["amount"],
                    "height": utxo["height"],
                    "time": utxo_time
                }
                reduced.append(reduced_utxo)
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


def reduce_notary_name(notary):
    notary = notary.split("_")[0]
    if notary in ["kolox", "ptyx2"]:
        notary = notary[:-1]
    if notary == "blackice":
        notary = "decker"
    if notary == "strobnidan":
        notary = "strob"
    return notary


def get_veterans():
    veterancy = {}
    tenure = {}
    for i in range(1, 7):
        url = f"https://stats.kmd.io/api/info/notary_nodes/?season=Season_{i}"
        data = requests.get(url).json()["results"]
        data = [reduce_notary_name(notary) for notary in data]
        data = list(set(data))
        for notary in data:
            if notary not in tenure:
                tenure[notary] = 0
            tenure[notary] += 1

    for notary in sorted(tenure, key=tenure.get, reverse=True):
        if tenure[notary] > 1:
            veterancy.update({notary: tenure[notary]})
    return veterancy


def is_self_send(txid, explorer, vote_addresses):
    try:
        if txid in SELF_SEND_TXIDS:
            return True
        tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
        if "vin" in tx_info:
            for i in tx_info['vin']:
                if "addr" in i:
                    if i['addr'] in vote_addresses:
                        SELF_SEND_TXIDS.append(txid)
                        bad_row = db.VoteRow(txid=txid)
                        bad_row.delete_txid()
                        print(f"Source [{i['addr']}] in [{txid}] is a vote address, skipping")
                        return True
    except Exception as e:
        print(f"Error in [is_self_send]: {e}")    
    return False

def get_address_transactions(explorer, address):
    # 50 max. Need to loop over pages.
    while True:
        from_ = 1
        to_ = 50
        transactions = requests.get(f"{explorer}/insight-api-komodo/addrs/{address}/txs?from={from_}&to={to_}").json()
        tx_count = transactions["totalItems"]
        break

    print(transactions)

    


def update_balances(polls, final_block=0, testnet=False):
    veterans = lib_json.get_jsonfile_data('veterans.json')
    for coin in polls:
        try:
            existing_txids = db.VoteTXIDs(coin)
            poll_txids = existing_txids.get_txids()
            poll_txid_list = [i["txid"] for i in poll_txids]
            explorer = polls[coin]["explorer"]
            balances = existing_txids.get_sum_by_address()
            balances = [dict(i) for i in balances]
            addresses = [i["address"] for i in balances]
            sync_height = get_sync_data(polls[coin]['explorer'])["height"]
            all_utxos = []
            for category in polls[coin]["categories"]:
                for option in polls[coin]["categories"][category]["options"]:
                    address = option["address"]
                    transactions = get_address_transactions(explorer, address)
                    candidate = option["candidate"]

                    testnet_ids = []
                    for k, v in testnet.items():
                        if candidate == v:
                            testnet_ids.append(k)
                    option.update({"testnet": testnet_ids})

                    if candidate in veterans:
                        option.update({"veteran": True})
                    else:
                        option.update({"veteran": False})

                    row = db.VoteRow()
                    row.coin = coin
                    row.address = address
                    row.category = category
                    row.option = candidate

                    if final_block != 0:
                        balance = get_address_balance(balances, address, final_block)

                    elif not polls[coin]["final_ntx_block"]:
                        utxos = get_address_utxos(explorer, address)
                        good_utxos = []
                        for utxo in utxos:
                            utxo.update({
                                "candidate": candidate,
                                "region": category
                            })
                            if not is_self_send(utxo["txid"], explorer, addresses):
                                if utxo["txid"] not in poll_txid_list and utxo["txid"] not in SELF_SEND_TXIDS:
                                    if "height" in utxo.keys():
                                        row.txid = utxo["txid"]
                                        row.amount = utxo["amount"]
                                        row.blockheight = utxo["height"]
                                        row.blocktime = utxo["time"]
                                        row.insert()
                                good_utxos.append(utxo)
                        print(f"{len(utxos)} before filtering self sent")
                        utxos = good_utxos
                        print(f"{len(utxos)} after filtering self sent")
                        all_utxos += utxos
                        option.update({
                            "votes": get_address_balance(balances, address),
                            "utxos": [i for i in utxos if i["amount"] >= 1]
                        })

                    elif sync_height <= polls[coin]["final_ntx_block"]["height"]:
                        utxos = get_address_utxos(explorer, address)
                        logger.info(f"{len(utxos)} {coin} utxos for {address}")
                        good_utxos = []
                        for utxo in utxos:
                            utxo.update({
                                "candidate": candidate,
                                "region": category
                            })
                            if not is_self_send(utxo["txid"], explorer, addresses):
                                if utxo["txid"] not in poll_txid_list and utxo["txid"] not in SELF_SEND_TXIDS:
                                    if "height" in utxo.keys():
                                        row.txid = utxo["txid"]
                                        row.amount = utxo["amount"]
                                        row.blockheight = utxo["height"]
                                        row.blocktime = utxo["time"]
                                        row.insert()
                                good_utxos.append(utxo)

                        print(f"{len(utxos)} before filtering self sent")
                        utxos = good_utxos
                        print(f"{len(utxos)} after filtering self sent")
                        all_utxos += utxos
                        option.update({
                            "votes": get_address_balance(balances, address),
                            "utxos":  [i for i in utxos if i["amount"] >= 1]
                        })
                    else:
                        logger.info(f"Not updating {coin} votes, poll is over.")
            if all_utxos:
                sum_utxos = sum([i["amount"] for i in all_utxos])
                sorted_utxos = sort_by_time(all_utxos)
                sorted_utxos.reverse()
                sorted_utxos = [i for i in sorted_utxos if i["amount"] >= 1]
                last_100 = sorted_utxos[:100]
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
                "time": block_time
            }

            if "total_votes" in polls[coin].keys():
                del polls[coin]["total_votes"]

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
