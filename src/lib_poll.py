import os
import csv
import time
import json
import segno
import requests
from decimal import Decimal
import lib_rpc
import lib_json
from lib_logger import logger
import lib_sqlite as db
from const import coin_info
import memcached


script_path = os.path.realpath(os.path.dirname(__file__))

def get_self_sent_txids(ticker):
    try:
        if ticker.startswith("KIP"):
            path = f'{script_path}/kip/{ticker.replace("KIP", "")}'
        else:
            path = f'{script_path}/vote/{ticker.replace("VOTE", "")}'
        path = f'{path}/self_sent_txids.json'
        if os.path.exists(path):
            txids = lib_json.get_jsonfile_data(path)
            if txids is not None:
                return txids
        with open(path, "w") as f:
            f.write('[]')
    except Exception as e:
        with open(path, "w") as f:
            f.write('[]')
    return []

def get_poll_options(polls, ticker, category):
    if ticker not in polls.keys():
        return {"error": f"{ticker} does not exist!"}
    if category not in polls[ticker]["categories"].keys():
        return {"error": f"{ticker} has no {category} category!"}
    return polls[ticker]["categories"][category]["options"]


def get_candidates():
    season = requests.get("https://stats.kmd.io/api/info/notary_season/").json()["results"].split('_')[1]
    url = f"https://raw.githubusercontent.com/KomodoPlatform/NotaryNodes/master/season{season}/candidates.json"
    return requests.get(url).json()


def validate_poll_results(polls, ticker, final_block):
    candidates = get_candidates()
    logger.calc(f'Validating poll results for {ticker}')
    logger.calc(f'Candidates:  {candidates}')
    try:
        deltas_json = []
        rpc = lib_rpc.get_rpc(
            os.getenv("rpcuser"),
            os.getenv("rpcpass"),
            ticker.lower(),
            coin_info[ticker]["rpcport"]
        )
        data = requests.get(f'http://127.0.0.1:8088/api/v3/polls/{ticker}/info').json()
        explorer = coin_info[ticker]["explorer"]
        for cat in data['categories']:
            for option in data['categories'][cat]["options"]:
                addr = option['address']
                # recalc candidate and region in case of pre window close shift
                candidate = db.get_address_owner(candidates, addr)
                region = get_address_region(candidates, addr)
                logger.info(f'{candidate}_{region}: {addr}')
                if candidate not in candidates:
                    logger.warning(f"{candidate} not in candidates!")
                    continue
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
                    "region": region,
                    "address": addr,
                    "votes": str(round(sats/100000000,8)),
                    "deltas": deltas
                }
                if ticker.startswith("VOTE"):
                    x.update({
                        "veteran": is_veteran(candidate),
                        "testnet": get_testnet_ids(ticker, candidate)
                    })
                deltas_json.append(x)
    except Exception as e:
        logger.error(e)

    # Export to JSON and CSV
    if ticker.startswith("KIP"):
        path = f'{script_path}/kip/{ticker.replace("KIP", "")}'
    else:
        path = f'{script_path}/vote/{ticker.replace("VOTE", "")}'
    lib_json.write_jsonfile_data(f'{path}/{ticker}_summary.json', deltas_json)
    with open(f'{script_path}/{ticker}_summary.csv', 'w') as csvfile:
        field_names = ["candidate", "region", "address", "votes", "deltas", "veteran", "testnet"]
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(deltas_json)
    
    # Clear the DB, then repopulate it
    coin_votes = db.VoteTXIDs(ticker)
    addresses = coin_votes.get_addresses_list()
    row = db.VoteRow(coin=ticker, blockheight=final_block)
    row.delete_coin()
    row.delete_invalid_blocks()
    self_sent_txids = get_self_sent_txids(ticker)
    for i in deltas_json:
        row.address = i["address"]
        row.category = i["region"]
        row.option = i["candidate"]
        logger.info(f'Rescanning for {row.option}: {row.address} ({row.category})')
        for delta in i["deltas"]:
            txid = delta["txid"]
            logger.merge(txid)
            if not is_self_send(txid, ticker, row.address, addresses, self_sent_txids):
                tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
                logger.merge(tx_info)
                if "blockheight" in tx_info.keys():
                    if tx_info["blockheight"] <= final_block:
                        row.txid = txid
                        row.amount = get_txid_amount(tx_info, row.address)
                        row.blockheight = tx_info["blockheight"]
                        row.blocktime = tx_info["blocktime"]
                        row.insert()
    update_balances(polls, ticker, final_block)
    polls = memcached.set_polls(polls)



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
    season = requests.get("https://stats.kmd.io/api/info/notary_season/").json()["results"]
    r = requests.get(f"https://stats.kmd.io/api/table/addresses/?season={season}&server=Main&coin=KMD").json()["results"]
    addresses = [i["address"] for i in r]
    return addresses


def is_ntx(tx_info):
    vouts = tx_info["vout"]
    vins = tx_info["vin"]
    if len(vouts) == 2 and len(vins) == 13:
        vin_addresses = [i["address"] for i in vins]
        notary_addresses = get_notary_addresses()
        # logger.info(vin_addresses)
        # logger.calc([i for i in vin_addresses if i not in notary_addresses])
        # if "scriptPubKey" in vouts[1]:
            # if "asm" in vouts[1]["scriptPubKey"]:
                # logger.calc(vouts[1]["scriptPubKey"]["asm"])
        if set(vin_addresses).issubset(notary_addresses):
            # logger.info(vouts)
            if vouts[1]["scriptPubKey"]["asm"].find("OP_RETURN") > -1:
                # logger.info(vouts)
                url = f'https://stats.kmd.io/api/tools/decode_opreturn/?OP_RETURN={vouts[1]["scriptPubKey"]["asm"]}'
                ntx_data = requests.get(url).json()
                # logger.info(f"ntx_data: {ntx_data}")
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
    if notary.startswith("0_"):
        notary = notary.replace("0_", "")
    notary = notary.split("_")[0]
    if notary in ["kolox"] or notary.endswith("2"):
        notary = notary[:-1]
    if notary == "chmexvet":
        notary = "chmex"
    if notary == "blackice":
        notary = "decker"
    if notary == "strobnidan":
        notary = "strob"
    return notary


def get_veterans():
    tenure = {}
    veterancy = {}
    season = requests.get("https://stats.kmd.io/api/info/notary_season/").json()["results"]
    x = int(season.replace("Season_", ""))
    for i in range(1, x + 1):
        url = f"https://stats.kmd.io/api/info/notary_nodes/?season=Season_{i}"
        data = requests.get(url).json()["results"]
        data = [reduce_notary_name(notary) for notary in data]
        data = list(set(data))
        logger.info(data)
        for notary in data:
            if notary not in tenure:
                tenure[notary] = 0
            tenure[notary] += 1
    for notary in sorted(tenure, key=tenure.get, reverse=True):
        if tenure[notary] > 1:
            veterancy.update({notary: tenure[notary]})
    return veterancy


def is_self_send(txid, ticker, address, vote_addresses, self_sent_txids):
    try:
        if txid in self_sent_txids:
            return True
        explorer = coin_info[ticker]["explorer"]
        tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
        if "vin" in tx_info:
            for i in tx_info['vin']:
                if "coinbase" in i:
                    bad_row = db.VoteRow(txid=txid)
                    bad_row.delete_txid()
                    return True
                if "addr" in i:
                    if i['addr'] in vote_addresses:
                        bad_row = db.VoteRow(txid=txid)
                        bad_row.delete_txid()
                        return True
                    if i['addr'] == address:
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


def update_option(option, ticker, explorer, category, poll_txid_list, addresses, final_block, self_sent_txids):
    try:
        address = option["address"]
        if "candidate" in option:
            candidate = option["candidate"]
        elif "name" in option:
            candidate = option["name"]
        else:
            candidate = ""
        if option["qr_code"] == "":
            logger.calc(f"Creating QR code for {option}")
            get_address_qrcode(address)
            option.update({
                "qr_code": f"https://raw.githubusercontent.com/smk762/fast_api_template/vote/src/qrcodes/{address}.png"
            })
        candidate_votes = db.VoteTXIDs(coin=ticker, address=address)
        row = db.VoteRow()
        row.coin = ticker
        row.address = address
        row.category = category
        row.option = candidate
        balance, transactions = get_address_info(explorer, address)
        tx_to_scan = list(set(transactions) - set(poll_txid_list) - set(self_sent_txids))
        for txid in tx_to_scan:
            if txid not in poll_txid_list and txid not in self_sent_txids:
                if not is_self_send(txid, ticker, address, addresses, self_sent_txids):
                    tx_info = requests.get(f"{explorer}/insight-api-komodo/tx/{txid}").json()
                    if "blockheight" in tx_info.keys():
                        row.txid = txid
                        row.amount = get_txid_amount(tx_info, address)
                        row.blockheight = tx_info["blockheight"]
                        row.blocktime = tx_info["blocktime"]
                        row.insert()
                else:
                    self_sent_txids.append(txid)
        if ticker.startswith("KIP"):
            path = f'{script_path}/kip/{ticker.replace("KIP", "")}'
        else:
            path = f'{script_path}/vote/{ticker.replace("VOTE", "")}'
        # This gets written to in a loop too often, do it better.
        lib_json.write_jsonfile_data(f'{path}/self_sent_txids.json', self_sent_txids, log=False)
        logger.info(f"Getting {ticker} votes for {candidate}")
        if final_block != 0:
            candidate_votes = db.VoteTXIDs(coin=ticker, address=address, final_block=final_block)
        else:
            candidate_votes = db.VoteTXIDs(coin=ticker, address=address)
        option.update({
            "votes": candidate_votes.get_sum_votes(),
            "utxos": []
        })
        if ticker.startswith("VOTE"):
            option.update({
                "veteran": is_veteran(candidate),
                "testnet": get_testnet_ids(ticker, candidate)
            })
                
    except Exception as e:
        logger.error(f"Error in [update_option] for {ticker} {option}: {e}")
    return option


def get_testnet_ids(ticker, candidate):
    try:
        id = ticker.replace("VOTE", "")
        path = f'{script_path}/vote/{id}/testnet.json'
        if os.path.exists(path):
            testnet_data = lib_json.get_jsonfile_data(path)
        else:
            with open(path, "w") as f:
                f.write('{}')
                return []
        testnet_ids = []
        for k, v in testnet_data.items():
            if candidate == v: testnet_ids.append(k)
        return testnet_ids
    except Exception as e:
        return []

    return testnet_ids


def is_veteran(candidate):
    veterans = lib_json.get_jsonfile_data(f'{script_path}/veterans.json')
    if reduce_notary_name(candidate) in veterans:
        return True
    else:
        return False


def update_balances(polls, ticker, final_block=0):
    try:
        self_sent_txids = get_self_sent_txids(ticker)
        explorer = coin_info[ticker]["explorer"]
        sync_height = get_sync_data(explorer)["height"]
        if final_block != 0:
            coin_votes = db.VoteTXIDs(ticker, final_block=final_block)
        else:    
            coin_votes = db.VoteTXIDs(ticker)
        addresses = coin_votes.get_addresses_list()
        poll_txid_list = coin_votes.get_txids_list()
        logger.calc(f"poll_txid_list {poll_txid_list}")
        for category in polls[ticker]["categories"]:
            options = polls[ticker]["categories"][category]["options"]
            for option in options:
                option = update_option(option, ticker, explorer, category, poll_txid_list, addresses, final_block, self_sent_txids)

        recent_txids = coin_votes.get_recent_votes()
        recent_votes = recast_recent_votes(recent_txids)
        votes = {
            "recent_votes": recent_votes,
            "sum_votes": coin_votes.get_sum_votes(),
            "count_votes": coin_votes.get_num_votes()
        }
        polls[ticker].update(votes)
        logger.calc(f"Updated balances for {ticker}")
    except Exception as e:
        logger.warning(f"Error in [update_balances] for {ticker}: {e}")


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
        polls = memcached.get_polls()
        for ticker in polls:
            logger.debug(f"updating {ticker} poll")
            if ticker.startswith("KIP"):
                ticker_path = f'{script_path}/kip/{ticker.replace("KIP", "")}'
            else:
                ticker_path = f'{script_path}/vote/{ticker.replace("VOTE", "")}'
            if not os.path.exists(ticker_path):
                os.makedirs(ticker_path)
            update_poll(polls, ticker)
    except Exception as e:
        logger.warning(f"RPC (overtime getinfo) not responding! {e}")

def update_poll(polls, ticker):
    try:
        if polls[ticker]["results_official"]:
            logger.info(f"Skipping {ticker} poll, official results are in")
        else:
            now = int(time.time())
            rpc = lib_rpc.get_rpc(
                os.getenv("rpcuser"),
                os.getenv("rpcpass"),
                ticker.lower(),
                coin_info[ticker]["rpcport"]
            )
            info = rpc.getinfo()
            polls[ticker]["updated_time"] = now
            blocktip = info["longestchain"]
            block_info = rpc.getblock(str(blocktip))
            block_time = block_info["time"]
            block_txids = block_info["tx"]
            block_hash = block_info["hash"]
            final_block = None
            polls[ticker]["current_block"] = {
                "height": blocktip,
                "hash": block_hash,
                "time": block_time
            }
            
            if polls[ticker]["final_ntx_block"] is not None:
                overtime_ended = polls[ticker]["overtime_ended_at"]
                since_ended = now - overtime_ended
                final_block = polls[ticker]["final_ntx_block"]["height"]
                logger.info(f"Final {ticker} block detected: {final_block} at {overtime_ended} ({since_ended} seconds ago)")
                if now - overtime_ended < 86400:
                    # Compare DB to addressdeltas to resolve reorgs
                    logger.info(f"Rescanning {ticker} votes, poll ended < day ago on block {final_block}.")
                    validate_poll_results(polls, ticker, polls[ticker]["final_ntx_block"]["height"])                
            else:
                
                ends_at = polls[ticker]["ends_at"]
                logger.calc(f"{ticker} ends at {ends_at}. Tiptime is {info['tiptime']}.")
                logger.calc(f"{ends_at - info['tiptime']} sec remaining until overtime")
                # Uncomment this after candidate proposal window closes
                # To repair votes cast before region swaps
                # Then comment out again once repaired
                # validate_poll_results(polls, ticker, blocktip) 
                # Does not fix recent votes :/
                if info["tiptime"] > ends_at and not polls[ticker]["first_overtime_block"]:
                    logger.info(f"Looking for first overtime block for {ticker}")
                    last_blockinfo = rpc.getblock(str(blocktip-2000))
                    logger.info(f"Starting at {blocktip-2000} {last_blockinfo}")
                    for i in range(blocktip-2000, blocktip+1):
                        block_info = rpc.getblock(str(i))
                        if last_blockinfo['time'] < ends_at:
                            logger.info(f"Last Block {i-1} is before ends_at: {ends_at}")
                            if block_info['time'] > ends_at:
                                logger.info(f"Block {i} is after ends_at: {ends_at}")
                                block_info = rpc.getblock(str(i))
                                polls[ticker].update({
                                    "first_overtime_block": {
                                        "height": block_info['height'],
                                        "hash": block_info['hash'],
                                        "time": block_info['time']
                                    }
                                })
                                logger.info(polls[ticker]["first_overtime_block"])
                                break
                        last_blockinfo = block_info
                
                if None not in [polls[ticker]["first_overtime_block"], polls[ticker]["final_ntx_block"]]:
                    logger.info(f"Looking for final ntx block for {ticker}")
                    polls[ticker]["status"] = "overtime"

                    if blocktip >= polls[ticker]["first_overtime_block"]["height"]:
                        logger.info(f'Scanning blocks {polls[ticker]["first_overtime_block"]["height"]} to {blocktip}')

                        for i in range(polls[ticker]["first_overtime_block"]["height"], blocktip+1):
                            block_info = rpc.getblock(str(i))

                            for txid in block_info["tx"]:
                                tx_info = rpc.getrawtransaction(txid, 1)

                                test = is_ntx(tx_info)
                                
                                if test:
                                    ntx_data = test["results"]

                                    if ntx_data['notarised_block'] >= polls[ticker]["first_overtime_block"]["height"]:
                                        block_info = rpc.getblock(str(ntx_data['notarised_block']))
                                        polls[ticker]["final_ntx_block"] = {
                                            "height": ntx_data['notarised_block'],
                                            "hash": block_info["hash"],
                                            "time": block_info["time"],
                                        }
                                        polls[ticker].update({
                                            "final_ntx_block_tx": txid,
                                            "overtime_ended_at": block_time,
                                            "status": "historical"
                                        })
                                        final_block = ntx_data['notarised_block']
                                        logger.info(f"Final {ticker} block detected: {final_block}")
                                        break

                            if polls[ticker]["final_ntx_block"]:
                                break

                update_balances(polls, ticker, final_block)
                memcached.set_polls(polls)


    except Exception as e:
        logger.error(f"updating {ticker} failed: {e}")

def get_sync_data(explorer):
    url = f"{explorer}/insight-api-komodo/sync"
    sync = requests.get(url).json()
    return sync


def get_address_qrcode(addr):
    qrcode = segno.make(addr, micro=False)
    qrcode.save(
        f'{script_path}/qrcodes/{addr}.png',
        scale=10,
        dark='#002530',
        light='#ffeeff'
    )

if __name__ == '__main__':
    rpc = lib_rpc.get_rpc(
        os.getenv("rpcuser"),
        os.getenv("rpcpass"),
        "KIP0001",
        coin_info["KIP0001"]["rpcport"]
    )
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
