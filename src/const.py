import os
import sys
from dotenv import load_dotenv, find_dotenv

#load_dotenv(find_dotenv())
load_dotenv()


def get_api_port():
    ''' Returns the port for the API. '''
    API_PORT = int(os.getenv("FASTAPI_PORT"))
    if not API_PORT:
        API_PORT = 8077
    else:
        API_PORT = int(API_PORT)
    return API_PORT


def get_ssl_certs():
    ''' Returns the SSL key and cert. '''
    SSL_KEY = os.getenv("SSL_KEY")
    if SSL_KEY in ["None", ""]:
        SSL_KEY = None
    SSL_CERT = os.getenv("SSL_CERT")
    if SSL_CERT in ["None", ""]:
        SSL_CERT = None
    return SSL_KEY, SSL_CERT


def get_db_path():
    ''' Returns the path to the database. '''
    return os.getenv('DB_PATH')


REGIONS = {
    "AR": "Asia / Russia",
    "EU": "Europe",
    "NA": "North America",
    "SH": "Southern Hemisphere"
}

coin_info = {
    "VOTE2023": {
        "explorer": "https://vote2023.dragonhound.info",
        "p2pport": 29806,
        "rpcport": 29807,
        "launch": {
            "ac_name": "VOTE2023",
            "ac_supply": "139706361",
            "ac_public": "1",
            "ac_staked": "10",
            "addnode": ["185.220.204.44", "178.159.2.6"]
        } 
    },
    "KIP0001": {
        "explorer": "https://kip0001.explorer.kmd.io",
        "p2pport": 46855,
        "rpcport": 46856,
        "launch": {
            "ac_name": "KIP0001",
            "ac_supply": "139419284",
            "ac_public": "1",
            "ac_staked": "10",
            "addnode": ["178.159.2.6", "116.203.120.163", "51.75.122.83", "15.235.204.174", "148.113.1.52", "65.21.77.109", "89.19.26.211", "89.19.26.212", "65.21.52.182"]
        }
    },
    "KIP0002": {
        "explorer": "https://kip0002.kmdexplorer.io/",
        "p2pport": 63161,
        "rpcport": 63160,
        "launch": {
            "ac_name": "KIP0002",
            "ac_supply": "149687271",
            "ac_public": "1",
            "ac_staked": "10",
            "addnode": ["209.222.101.247", "103.195.100.32", "51.75.122.83", "15.235.204.174", "148.113.1.52", "65.21.77.109", "89.19.26.211", "89.19.26.212", "65.21.52.182"]
        }
    },
    "KIP0003": {
        "explorer": "https://kip0003.kmdexplorer.io/",
        "p2pport": 48530,
        "rpcport": 48531,
        "launch": {
            "ac_name": "KIP0003",
            "ac_supply": "149687271",
            "ac_public": "1",
            "ac_staked": "10",
            "addnode": ["209.222.101.247", "103.195.100.32", "51.75.122.83", "15.235.204.174", "148.113.1.52", "65.21.77.109", "89.19.26.211", "89.19.26.212", "65.21.52.182"]
        }
    },
    "KIP0004": {
        "explorer": "https://kip0004.kmdexplorer.io/",
        "p2pport": 58225,
        "rpcport": 58226,
        "launch": {
            "ac_name": "KIP0004",
            "ac_supply": "149687271",
            "ac_public": "1",
            "ac_staked": "10",
            "addnode": ["209.222.101.247", "103.195.100.32", "51.75.122.83", "15.235.204.174", "148.113.1.52", "65.21.77.109", "89.19.26.211", "89.19.26.212", "65.21.52.182"]
        }
    }
}