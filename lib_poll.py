import time
import requests
import lib_rpc
import lib_json
from lib_logger import logger

def get_data():
    return {"Hello": "World"}


def get_poll_options(chain, category):
    polls = lib_json.get_jsonfile_data('poll_config.json')
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
        "upcoming": []
    }
    for i in polls:
        if polls[i]["starts_at"] > now:
            status["upcoming"].append(i)
        elif polls[i]["ends_at"] > now:
            status["active"].append(i)
        else:
            status["historical"].append(i)
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


def check_polls_overtime(polls, chain):
    try:
        if not polls[chain]["final_ntx_block"]:

            now = int(time.time())
            ends_at = polls[chain]["ends_at"]

            rpc = lib_rpc.get_rpc(chain)
            info = rpc.getinfo()
            blocktip = info["longestchain"]
            if info["tiptime"] > polls[chain]["ends_at"] and not polls[chain]["first_overtime_block"]:
                polls[chain]["first_overtime_block"] = blocktip

            if polls[chain]["first_overtime_block"]:
                if blocktip >= polls[chain]["first_overtime_block"]:
                    logger.info(f"longestchain: {blocktip}")
                    for i in range(polls[chain]["first_overtime_block"], blocktip):
                        block_txids = rpc.getblock(str(i))["tx"]

                        for txid in block_txids:
                            tx_info = rpc.getrawtransaction(txid, 1)
                            if is_ntx(tx_info):
                                polls[chain]["final_ntx_block"] = i
                                lib_json.write_jsonfile_data('poll_config.json', polls)
                                return
            lib_json.write_jsonfile_data('poll_config.json', polls)

    except Exception as e:
        logger.warning(f"RPC (overtime getinfo) not responding! {e}")


def update_balances(polls, balances):
    try:
        for chain in polls:
            if not polls[chain]["final_ntx_block"]:
                rpc = lib_rpc.get_rpc(chain)
                if rpc:
                    for category in polls[chain]["categories"]:
                        for option in polls[chain]["categories"][category]["options"]:
                            address = polls[chain]["categories"][category]["options"][option]["address"]
                            logger.info(f"Getting {chain} balance for {address}")
                            params = {"addresses": [address]}
                            r = rpc.getaddressbalance(params)
                            balance = r["balance"]/100000000
                            balances.update({address: balance})
                            polls[chain]["categories"][category]["options"][option].update({"votes": balance})
                    lib_json.write_jsonfile_data('poll_config.json', polls)
                else:
                    logger.warning(rpc)
            else:
                logger.info(f"Not updating {chain} votes, poll is over.")
    except Exception as e:
        logger.warning(f"Error in [update_balances] for {chain} {category} {option}: {e}")
    logger.info(f"balances: {balances}")
    return balances


if __name__ == '__main__':
    rpc = lib_rpc.get_rpc("KIP0001")
    tx_info = rpc.getrawtransaction("0a95b1ecf0163640d5e631767877fa745f40bf9480631b1f9c5f64a953c3b1c7", 1)
    print(is_ntx(tx_info))
    assert is_ntx(tx_info)
    tx_info = rpc.getrawtransaction("dfc390cf85a40dac5c4b3ec6540f32ba229610a14039cb1f30afec9cdddf8c34", 1)
    print(is_ntx(tx_info))
    assert not is_ntx(tx_info)