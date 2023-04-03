import os
import re
import platform
from slickrpc import Proxy
from lib_logger import logger
from dotenv import load_dotenv
load_dotenv()


RPCIP = "127.0.0.1"
if os.getenv("RPCIP"):
    RPCIP = os.getenv("RPCIP")


DEAMONS = ['RICK', 'MORTY']
if os.getenv("DEAMONS"):
    DEAMONS = os.getenv("DEAMONS").split(" ")
print(DEAMONS)

def def_data_dir():
    try:
        operating_system = platform.system()
        if operating_system == 'Darwin':
            ac_dir = os.environ['HOME'] + '/Library/Application Support/Komodo'
        elif operating_system == 'Linux':
            ac_dir = os.environ['HOME'] + '/.komodo'
        elif operating_system == 'Windows':
            ac_dir = '%s/komodo/' % os.environ['APPDATA']
        return(ac_dir)
    except Exception as e:
        logger.warning(f"Error in [def_data_dir]: {e}")


# fucntion to define rpc_connection
def get_rpc(chain):
    try:
        rpcport = '';
        ac_dir = def_data_dir()
        if chain == 'KMD':
            coin_config_file = f"{ac_dir}/komodo.conf"
        else:
            coin_config_file = f"{ac_dir}/{chain}/{chain}.conf"
        with open(coin_config_file, 'r') as f:
            for line in f:
                l = line.rstrip()
                if re.search('rpcuser', l):
                    rpcuser = l.replace('rpcuser=', '').strip()
                elif re.search('rpcpassword', l):
                    rpcpassword = l.replace('rpcpassword=', '').strip()
                elif re.search('rpcport', l):
                    rpcport = l.replace('rpcport=', '').strip()
        if len(rpcport) == 0:
            if chain == 'KMD':
                rpcport = 7771
            else:
                logger.info("rpcport not in conf file, exiting")
                logger.info(f"check {coin_config_file}")
        url = f"http://{rpcuser}:{rpcpassword}@{RPCIP}:{rpcport}"
        return (Proxy(url, timeout=90))
    except Exception as e:
        error = f"Unable to set RPC proxy, please confirm rpcuser, rpcpassword and rpcport are set: {e}"
        logger.info(error)
        return False
