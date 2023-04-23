#!/usr/bin/env python3
from moralis import evm_api #pip install moralis

from lib.const import ConfigFastAPI
from lib.sqlite import SqliteDB

from lib.logger import logger
import lib.api_proxy as api_proxy
import lib.json_utils as json_utils

config = ConfigFastAPI()
print(config.as_dict)

# https://moralisweb3.github.io/Moralis-Python-SDK/evm_api/nft.html#get_wallet_nfts
def get_wallet_nfts(chain, address, format="decimal", limit=10, disable_total=True,
                    token_addresses=None, cursor="", normalizeMetadata=True, media_items=True):
    if not token_addresses:
        token_addresses = []

    params = {
        "address": address, 
        "chain": chain.lower(), 
        "format": format, 
        "limit": limit, 
        "disable_total": disable_total, 
        "token_addresses": token_addresses, 
        "cursor": cursor, 
        "normalizeMetadata": normalizeMetadata, 
        "media_items": media_items
    }
    print(config.MORALIS_API_KEY)
    result = evm_api.nft.get_wallet_nfts(
        api_key=config.MORALIS_API_KEY,
        params=params
    )

    return result


# https://moralisweb3.github.io/Moralis-Python-SDK/evm_api/nft.html#get_wallet_nft_transfers
def get_wallet_nft_transfers(chain, address, format="decimal", limit=10, disable_total=True, cursor="",
                    to_block="", from_block="", direction="both"):

    params = {
        "address": address, 
        "chain": chain.lower(), 
        "format": format, 
        "limit": limit, 
        "disable_total": disable_total, 
        "cursor": cursor, 
        "direction": direction
    }
    if to_block:
        params.update({"to_block": to_block})
    if from_block:
        params.update({"from_block": from_block})
    print(config.MORALIS_API_KEY)
    result = evm_api.nft.get_wallet_nft_transfers(
        api_key=config.MORALIS_API_KEY,
        params=params
    )

    return result



# https://moralisweb3.github.io/Moralis-Python-SDK/evm_api/nft.html#get_nft_metadata
def get_nft_metadata(chain, address,  token_id="", format="decimal",
                     normalizeMetadata=True, media_items=True):

    params = {
        "address": address, 
        "chain": chain.lower(), 
        "format": format,
        "token_id": token_id,
        "normalizeMetadata": normalizeMetadata, 
        "media_items": media_items
    }
    print(config.MORALIS_API_KEY)
    result = evm_api.nft.get_nft_metadata(
        api_key=config.MORALIS_API_KEY,
        params=params
    )

    return result

