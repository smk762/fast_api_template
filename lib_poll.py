import csv
import time
import json
import requests
from decimal import Decimal
import lib_rpc
import lib_json
from lib_logger import logger
import lib_sqlite as db


SELF_SENT_TXIDS = lib_json.get_jsonfile_data(f'self_sent_txids.json')

def get_poll_options(polls, coin, category):
    if coin not in polls.keys():
        return {"error": f"{coin} does not exist!"}
    if category not in polls[coin]["categories"].keys():
        return {"error": f"{coin} has no {category} category!"}
    return polls[coin]["categories"][category]["options"]


def validate_poll_results(polls, coin, final_block):
    logger.info(f'Validating poll results for {coin}')
    deltas_json = []
    rpc = lib_rpc.get_rpc(coin)
    data = requests.get(f'https://kip0001.smk.dog/api/v3/polls/{coin}/info').json()
    explorer = polls[coin]["explorer"]
    for cat in data['categories']:
        for option in data['categories'][cat]["options"]:
            addr = option['address']
            candidate = option['candidate']
            logger.info(f'{candidate}: {addr} ({cat})')
            params = {
                "addresses": [addr],
                "start":1,
                "end":final_block
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

    # Export to JSON and CSV
    lib_json.write_jsonfile_data(f'{coin}_summary.json', deltas_json)
    with open(f'{coin}_summary.csv', 'w') as csvfile:
        field_names = ["candidate", "region", "address", "votes", "deltas"]
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(deltas_json)
    
    # Clear the DB, then repopulate it
    coin_votes = db.VoteTXIDs(coin)
    addresses = coin_votes.get_addresses_list()
    row = db.VoteRow(coin=coin, blockheight=final_block)
    row.delete_coin()
    row.delete_invalid_blocks()
    for i in deltas_json:
        row.address = i["address"]
        row.category = i["region"]
        row.option = i["candidate"]
        logger.info(f'Rescanning for {row.option}: {row.address} ({row.category})')
        for delta in i["deltas"]:
            txid = delta["txid"]
            tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
            if not is_self_send(txid, explorer, row.address, addresses):
                if "blockheight" in tx_info.keys():
                    if tx_info["blockheight"] <= final_block:
                        row.txid = txid
                        row.amount = get_txid_amount(tx_info, row.address)
                        row.blockheight = tx_info["blockheight"]
                        row.blocktime = tx_info["blocktime"]
                        row.insert()
    update_balances(polls, final_block)
    lib_json.write_jsonfile_data('poll_config_v3.json', polls)



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
    logger.info(f"len(vins): {len(vins)}")
    if len(vouts) == 2 and len(vins) == 13:
        vin_addresses = [i["address"] for i in vins]
        notary_addresses = get_notary_addresses()
        if set(vin_addresses).issubset(notary_addresses):
            if vouts[1]["scriptPubKey"]["asm"].find("OP_RETURN") > -1:
                ntx_data = requests.get(f'https://stats.kmd.io/api/tools/decode_opreturn/?OP_RETURN={vouts[1]["scriptPubKey"]["asm"]}').json()
                logger.info(f"ntx_data: {ntx_data}")
                return ntx_data
    return None


def sort_by_time(data):
    r = sorted(data, key=lambda x: x["time"])
    return r


def get_txid_time(explorer, txid):
    tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
    if "blocktime" in tx_info:
        return tx_info["blocktime"]
    else:
        return False


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
    tenure = {}
    veterancy = {}
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


def is_self_send(txid, explorer, address, vote_addresses):
    try:
        if txid in SELF_SENT_TXIDS:
            return True
        tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
        if "vin" in tx_info:
            for i in tx_info['vin']:
                if "coinbase" in i:
                    SELF_SENT_TXIDS.append(txid)
                    bad_row = db.VoteRow(txid=txid)
                    bad_row.delete_txid()
                    return True
                if "addr" in i:
                    if i['addr'] in vote_addresses:
                        SELF_SENT_TXIDS.append(txid)
                        bad_row = db.VoteRow(txid=txid)
                        bad_row.delete_txid()
                        return True
                    if i['addr'] == address:
                        SELF_SENT_TXIDS.append(txid)
                        bad_row = db.VoteRow(txid=txid)
                        bad_row.delete_txid()
                        return True
    except Exception as e:
        logger.info(f"Error in [is_self_send]: {e}")
    return False


def get_address_info(explorer, address):
    info = requests.get(f"{explorer}/insight-api-komodo/addr/{address}").json()
    balance = info["balance"]
    transactions = info["transactions"]
    return balance, transactions


def get_txid_amount(txinfo, address):
    amount = 0
    for i in txinfo["vout"]:
        if "addresses" in i["scriptPubKey"]:
            if address in i["scriptPubKey"]["addresses"]:
                amount += Decimal(i["value"])
    return float(amount)


def update_option(option, coin, explorer, address, category, candidate, poll_txid_list, addresses):
    try:
        candidate_votes = db.VoteTXIDs(coin=coin, address=address)
        row = db.VoteRow()
        row.coin = coin
        row.address = address
        row.category = category
        row.option = candidate

        balance, transactions = get_address_info(explorer, address)
        tx_to_scan = list(set(transactions) - set(poll_txid_list) - set(SELF_SENT_TXIDS))

        for txid in tx_to_scan:
            if txid not in poll_txid_list and txid not in SELF_SENT_TXIDS:
                tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
                if not is_self_send(txid, explorer, address, addresses):
                    if "blockheight" in tx_info.keys():
                        row.txid = txid
                        row.amount = get_txid_amount(tx_info, address)
                        row.blockheight = tx_info["blockheight"]
                        row.blocktime = tx_info["blocktime"]
                        row.insert()
    except Exception as e:
        logger.info(f"Error in [update_option]: {e}")
    return option


def get_testnet_ids(testnet, candidate):
    testnet_ids = []
    for k, v in testnet.items():
        if candidate == v: testnet_ids.append(k)
    return testnet_ids


def is_veteran(candidate, veterans):
    if candidate in veterans: return True
    else: return False


def update_balances(polls, final_block=0):
    veterans = lib_json.get_jsonfile_data('veterans.json')
    for coin in polls:
        try:
            testnet = lib_json.get_jsonfile_data(f'testnet_{coin}.json')
            explorer = polls[coin]["explorer"]
            sync_height = get_sync_data(explorer)["height"]
            if final_block != 0:
                coin_votes = db.VoteTXIDs(coin, final_block=final_block)
            else:    
                coin_votes = db.VoteTXIDs(coin)
            addresses = coin_votes.get_addresses_list()
            poll_txid_list = coin_votes.get_txids_list()
            for category in polls[coin]["categories"]:
                options = polls[coin]["categories"][category]["options"]
                for option in options:
                    address = option["address"]
                    candidate = option["candidate"]

                    option = update_option(option, coin, explorer, address, category, candidate, poll_txid_list, addresses)
                    logger.info(f"Getting {coin} votes for {candidate}")
                    if final_block != 0:
                        candidate_votes = db.VoteTXIDs(coin=coin, address=address, final_block=final_block)
                    else:
                        candidate_votes = db.VoteTXIDs(coin=coin, address=address)
                    candidate_recent_txids = candidate_votes.get_recent_votes()
                    candidate_recent_votes = recast_recent_votes(candidate_recent_txids)

                    option.update({
                        "votes": candidate_votes.get_sum_votes(),
                        "veteran": is_veteran(candidate, veterans),
                        "utxos": []
                    })
                    if testnet:
                        option.update({
                            "testnet": get_testnet_ids(testnet, candidate)
                        })

            recent_txids = coin_votes.get_recent_votes()
            recent_votes = recast_recent_votes(recent_txids)
            polls[coin].update({
                "recent_votes": recent_votes,
                "sum_votes": coin_votes.get_sum_votes(),
                "count_votes": coin_votes.get_num_votes()
            })
            lib_json.write_jsonfile_data('self_sent_txids.json', SELF_SENT_TXIDS)

        except Exception as e:
            logger.warning(f"Error in [update_balances] for {coin}: {e}")


def recast_recent_votes(recent_txids):
    recent_votes = []
    for i in recent_txids:
        vote = {
            "txid": i['txid'],
            "amount": i['amount'],
            "height": i['blockheight'],
            "time": i['blocktime'],
            "candidate": i['option'],
            "region": i['category']
        }
        recent_votes.append(vote)
    return recent_votes


def update_polls():
    try:
        polls = lib_json.get_jsonfile_data('poll_config_v3.json')
        if not polls:
            polls = {}
        now = int(time.time())
        for coin in polls:
            if polls[coin]["results_official"]:
                logger.info(f"Skipping {coin} poll, official results are in")
            else:
                logger.info(f"Updating {coin} poll")
                rpc = lib_rpc.get_rpc(coin)
                info = rpc.getinfo()
                polls[coin]["updated_time"] = now
                blocktip = info["longestchain"]
                block_info = rpc.getblock(str(blocktip))
                block_time = block_info["time"]
                block_txids = block_info["tx"]
                block_hash = block_info["hash"]
                final_block = None
                polls[coin]["current_block"] = {
                    "height": blocktip,
                    "hash": block_hash,
                    "time": block_time
                }

                if polls[coin]["final_ntx_block"]:
                    now = int(time.time())
                    overtime_ended = polls[coin]["overtime_ended_at"]
                    since_ended = now - overtime_ended
                    final_block = polls[coin]["final_ntx_block"]["height"]
                    logger.info(f"Final {coin} block detected: {final_block} at {overtime_ended} ({since_ended} seconds ago)")
                    if now - overtime_ended < 86400:
                        # Compare DB to addressdeltas to resolve reorgs
                        logger.info(f"Rescanning {coin} votes, poll ended < day ago on block {final_block}.")
                        validate_poll_results(polls, coin, polls[coin]["final_ntx_block"]["height"])                
                else:
                    ends_at = polls[coin]["ends_at"]

                    if info["tiptime"] > ends_at and not polls[coin]["first_overtime_block"]:
                        logger.info(f"Looking for first overtime block for {coin}")
                        last_blockinfo = rpc.getblock(str(blocktip-2000))
                        for i in range(blocktip-2000, blocktip+1):
                            block_info = rpc.getblock(str(i))
                            if last_blockinfo['time'] < ends_at:
                                logger.info(f"Last Block {i-1} is before ends_at: {ends_at}")
                                if block_info['time'] > ends_at:
                                    logger.info(f"Block {i} is after ends_at: {ends_at}")
                                    block_info = rpc.getblock(str(i))
                                    polls[coin].update({
                                        "first_overtime_block": {
                                            "height": block_info['height'],
                                            "hash": block_info['hash'],
                                            "time": block_info['time']
                                        }
                                    })
                                    logger.info(polls[coin]["first_overtime_block"])
                                    break
                            last_blockinfo = block_info
                    
                    if polls[coin]["first_overtime_block"] and not polls[coin]["final_ntx_block"]:
                        logger.info(f"Looking for final ntx block for {coin}")
                        polls[coin]["status"] = "overtime"

                        if blocktip >= polls[coin]["first_overtime_block"]["height"]:
                            logger.info(f"longestchain: {blocktip}")

                            for i in range(polls[coin]["first_overtime_block"]["height"], blocktip+1):
                                logger.info(f"Scanning block: {i}")
                                block_info = rpc.getblock(str(i))
                                for txid in block_info["tx"]:
                                    tx_info = rpc.getrawtransaction(txid, 1)
                                    logger.info(f"Scanning txid: {txid}")

                                    if is_ntx(tx_info):
                                        ntx_data = is_ntx(tx_info)["results"]
                                        if ntx_data['notarised_block'] >= polls[coin]["first_overtime_block"]["height"]:
                                            block_info = rpc.getblock(str(ntx_data['notarised_block']))
                                            polls[coin]["final_ntx_block"] = {
                                                "height": ntx_data['notarised_block'],
                                                "hash": block_info["hash"],
                                                "time": block_info["time"],
                                            }
                                            polls[coin].update({
                                                "final_ntx_block_tx": txid,
                                                "overtime_ended_at": block_time,
                                                "status": "historical"
                                            })
                                            final_block = ntx_data['notarised_block']
                                            logger.info(f"Final {coin} block detected: {final_block}")
                                            break
                                if polls[coin]["final_ntx_block"]:
                                    break

                    update_balances(polls, final_block)
                    lib_json.write_jsonfile_data('poll_config_v3.json', polls)
                    lib_json.write_jsonfile_data('self_sent_txids.json', SELF_SENT_TXIDS)

    except Exception as e:
        logger.warning(f"RPC (overtime getinfo) not responding! {e}")


def get_sync_data(explorer):
    url = f"{explorer}/insight-api-komodo/sync"
    sync = requests.get(url).json()
    return sync


if __name__ == '__main__':
    rpc = lib_rpc.get_rpc("KIP0001")
    tx_info = rpc.getrawtransaction("9bb939a7de730487a4023075d1db6fdd0849fd33ced57d16b6453e5f5453edaa", 1)
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
