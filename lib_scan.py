#!/usr/bin/env python3
import os
import sys
import ssl
import json
import time
import socket
import requests
import threading
from lib_electrum import ElectrumConnection
import lib_sqlite

script_dir = os.path.abspath( os.path.dirname( __file__ ) )



class scan_thread(threading.Thread):
    def __init__(self, coin, url, port, ssl, method, params=None):
        threading.Thread.__init__(self)
        self.coin = coin
        self.url = url
        self.port = port
        self.method = method
        self.params = params
        self.ssl = ssl
    def run(self):
        thread_electrum(self.coin, self.url, self.port, self.ssl, self.method, self.params)


# def thread_ws(coin, url, port, method, params):
#     #resp = get_from_ws(url, port, method, params)
#     try:
#         resp_json = json.loads(resp)['result']
#         print(f"{coin} {url}:{port} OK!", 'green')
#         if coin not in passed_ws:
#             passed_ws.update({coin:[]})
#         passed_ws[coin].append(f"{url}:{port}")
#     except Exception as e:
#         if str(resp).find('{"jsonrpc": "2.0"') > -1:
#             if coin not in passed_ws:
#                 passed_ws.update({coin:[]})
#             passed_ws[coin].append(f"{url}:{port}")
#             print(f"{coin} {url}:{port} OK!", 'green')
#             return
#         if coin not in failed_ws:
#             failed_ws.update({coin:{}})
#         failed_ws[coin].update({f"{url}:{port}": f"{resp}"})
#         print(f"{coin} {url}:{port} Failed! {e} | {resp}", 'red')


def thread_electrum(coin, url, port, ssl, method, params):
    electrum = ElectrumConnection(url, port, ssl)
    time.sleep(3)
    now = int(time.time())
    resp = electrum.get_tip()
    try:
        if isinstance(resp, str) or isinstance(resp, OSError) or isinstance(resp, ConnectionResetError) \
             or isinstance(resp, ConnectionRefusedError) or isinstance(resp, socket.gaierror) \
             or isinstance(resp, json.decoder.JSONDecodeError):
            resp = str(resp).replace("'", "")
            row = (coin, f"{url}:{port}", ssl, "Failing", resp)
            lib_sqlite.update_electrum_row_failed(row)
            print(f"<<<< Failed: {row}")
        elif isinstance(resp, dict):
            resp = json.dumps(resp)
            row = (coin, f"{url}:{port}", ssl, "OK", resp, now)
            lib_sqlite.update_electrum_row(row)
            print(f">>>> OK: {row}")

    except Exception as e:
        resp = str(resp)
        row = (coin, f"{url}:{port}", ssl, "Failing", resp)
        lib_sqlite.update_electrum_row_failed(row)
        #print(f"<<<< Failed: {row} {e}")
        

def update_electrums_status():
    electrum_dict = get_repo_electrums()
    scan_electrums(electrum_dict)


def get_repo_electrums():
    electrum_coins = [f for f in os.listdir(f"{script_dir}/coins/electrums") if os.path.isfile(f"{script_dir}/coins/electrums/{f}")]
    repo_electrums = {}
    for coin in electrum_coins:
        with open(f"{script_dir}/coins/electrums/{coin}", "r") as f:
            electrums = json.load(f)
            repo_electrums.update({coin: electrums})
    return repo_electrums


def scan_electrums(electrum_dict):
    thread_list = []
    ws_list = []
    ssl_list = []
    non_ssl_list = []

    for coin in electrum_dict:
        for electrum in electrum_dict[coin]:
            url, port = electrum["url"].split(":")
            if "protocol" in electrum:
                if electrum["protocol"] == "SSL":
                    ssl_list.append(coin)
                    thread_list.append(scan_thread(coin, url, port, True, "blockchain.headers.subscribe"))
                    continue
            non_ssl_list.append(coin)
            thread_list.append(scan_thread(coin, url, port, False, "blockchain.headers.subscribe"))

    # for coin in electrum_dict:
    #     for electrum in electrum_dict[coin]:
    #         if "ws_url" in electrum:
    #             url, port = electrum["ws_url"].split(":")
    #             ws_list.append(coin)
    #             thread_list.append(scan_thread(coin, url, port, "blockchain.headers.subscribe", [1,2], "ws"))

    for thread in thread_list:
        thread.start()
        time.sleep(0.05)
    return set(ssl_list), set(non_ssl_list)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "scan":
            update_electrums_status()

        if sys.argv[1] == "clean":
            electrum_coins = list(get_repo_electrums().keys())
            db_coins = lib_sqlite.get_db_coins()
            print(electrum_coins)
            print(db_coins)
            for coin in db_coins:
                if coin not in electrum_coins:
                    print(f"Deleting {coin}")
                    lib_sqlite.delete_electrum_coin(coin)
