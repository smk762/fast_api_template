import os
import re
import platform
from slickrpc import Proxy
from lib_logger import logger

# fucntion to define rpc_connection
def get_rpc(rpcuser, rpcpass, rpcip, rpcport):
    try:
        url = f"http://{rpcuser}:{rpcpass}@{rpcip}:{rpcport}"
        return (Proxy(url, timeout=90))
    except Exception as e:
        error = f"Unable to set RPC proxy, please confirm rpcuser, rpcpassword and rpcport are set: {e}"
        logger.info(error)
        return False

