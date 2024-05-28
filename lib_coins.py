#!/usr/bin/env python3
import os
import sys
import ssl
import json
import time
import socket
import threading
import asyncio
import websockets
import lib_sqlite
from lib_logger import logger
from pymemcache.client.base import PooledClient


class JsonSerde(object):  # pragma: no cover
    def serialize(self, key, value):
        if isinstance(value, str):
            return value.encode("utf-8"), 1
        return json.dumps(value).encode("utf-8"), 2

    def deserialize(self, key, value, flags):
        if flags == 1:
            return value.decode("utf-8")
        if flags == 2:
            return json.loads(value.decode("utf-8"))
        raise Exception("Unknown serialization format")


MEMCACHE = PooledClient(
    ("127.0.0.1", 11211),
    serde=JsonSerde(),
    timeout=10,
    max_pool_size=50,
    ignore_exc=True,
)
MEMCACHE.flush_all()

def cache(key, value, expiry):
    MEMCACHE.set(key, value, expiry)

def get(key):
    return MEMCACHE.get(key)

socket.setdefaulttimeout(10)
script_path = os.path.abspath(os.path.dirname(__file__))
repo_path = script_path.replace("/utils", "")
os.chdir(script_path)

class ElectrumServer:
    __slots__ = ("coin", "url", "port", "protocol", "result", "blockheight", "last_connection")
    
    def __init__(self, coin, url, port, protocol):
        self.coin = coin
        self.url = url
        self.port = port
        self.protocol = protocol
        self.result = None
        self.blockheight = -1
        self.last_connection = -1

    def tcp(self, method, params=None):
        if params:
            params = [params] if type(params) is not list else params
        try:
            with socket.create_connection((self.url, self.port)) as sock:
                # Handshake
                payload = {"id": 0, "method": "server.version", "params": ["smk", ["1.4", "1.6"]]}
                sock.send(json.dumps(payload).encode() + b'\n')
                time.sleep(1)
                resp = sock.recv(999999)[:-1].decode()
                # logger.info(f"TCP {self.url}:{self.port} {resp}")
                # Request
                payload = {"id": 0, "method": method}
                if params:
                    payload.update({"params": params})
                sock.send(json.dumps(payload).encode() + b'\n')
                time.sleep(1)
                resp = sock.recv(999999)[:-1].decode()
                resp = resp.splitlines()
                if len(resp) > 0:
                    resp = resp[-1]
                return resp
        except Exception as e:
            return e

    def ssl(self, method, params=None):
        if params:
            params = [params] if type(params) is not list else params
        context = ssl.SSLContext(verify_mode=ssl.CERT_NONE)
        try:
            with socket.create_connection((self.url, self.port)) as sock:
                with context.wrap_socket(sock, server_hostname=self.url) as ssock:
                    # Handshake
                    payload = {"id": 0, "method": "server.version", "params": ["smk", ["1.4", "1.6"]]}
                    ssock.send(json.dumps(payload).encode() + b'\n')
                    time.sleep(1)
                    resp = ssock.recv(999999)[:-1].decode()
                    # logger.info(f"SSL {self.url}:{self.port} {resp}")
                    # Request                    
                    payload = {"id": 0, "method": method}
                    if params:
                        payload.update({"params": params})
                    ssock.send(json.dumps(payload).encode() + b'\n')
                    time.sleep(1)
                    resp = ssock.recv(999999)[:-1].decode()
                    resp = resp.splitlines()
                    if len(resp) > 0:
                        resp = resp[-1]
                    return resp
        except Exception as e:
            return e

    def wss(self, method, params=None):    
        if params:
            params = [params] if type(params) is not list else params
        
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            async def connect_and_query():
                async with websockets.connect(f"wss://{self.url}:{self.port}", ssl=ssl_context, timeout=10) as websocket:
                    # Handshake
                    payload = {"id": 0, "method": "server.version", "params": ["smk", ["1.4", "1.6"]]}
                    await websocket.send(json.dumps(payload))
                    await asyncio.sleep(1)
                    resp = await asyncio.wait_for(websocket.recv(), timeout=7)
                    # logger.info(f"WSS {self.url}:{self.port} {resp}")
                    # Request
                    payload = {"id": 0, "method": method}
                    if params:
                        payload.update({"params": params})
                    await websocket.send(json.dumps(payload))
                    await asyncio.sleep(1)
                    resp = await asyncio.wait_for(websocket.recv(), timeout=7)
                    resp = resp.splitlines()
                    if len(resp) > 0:
                        resp = resp[-1]
                    return resp
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(connect_and_query())
            return response
        except Exception as e:
            return e


class scan_thread(threading.Thread):
    def __init__(self, coin, url, port, method, params=None, protocol='tcp'):
        threading.Thread.__init__(self)
        self.coin = coin
        self.url = url
        self.port = port
        self.method = method
        self.params = params
        self.protocol = protocol

    def run(self):
        if self.protocol == "ssl":
            thread_electrum_ssl(self.coin, self.url, self.port, self.method, self.params)
        elif self.protocol == "tcp":
            thread_electrum(self.coin, self.url, self.port, self.method, self.params)
        elif self.protocol == "wss":
            thread_electrum_wss(self.coin, self.url, self.port, self.method, self.params)


def thread_electrum_wss(coin, url, port, method, params):
    try:
        el = ElectrumServer(coin, url, port, "WSS")
        cache_id = f"{coin}-{url}-{port}-WSS"
        data = None # get(cache_id)
        if data is not None:
            logger.info(f"Using cache for {cache_id}")
            el.result = data["result"]
            el.blockheight = data["blockheight"]
            el.last_connection = data["last_connection"]
        else:
            el.wss("blockchain.headers.subscribe", [])
            resp = el.wss(method, params)

            if str(resp).lower().find('timeout') > -1:
                el.result = "Timeout"
            elif str(resp).lower().find('connect call failed') > -1:
                el.result = "Connection refused"
            elif str(resp).lower().find('oserror') > -1:
                el.result = "OS Error"
            elif str(resp).lower().find('gaierror') > -1:
                el.result = "Gai Error"
            elif len(str(resp)) < 3:
                el.result = "Empty response"
                
            elif "result" in json.loads(resp):
                el.result = json.loads(resp)['result']
            elif "params" in json.loads(resp):
                el.result = json.loads(resp)['params'][0]
            else:
                logger.error(f"Unable to get result for {cache_id}")
                logger.error(json.loads(resp))

            if "height" in el.result:
                el.blockheight = int(el.result['height'])
                el.last_connection = int(time.time())
                # logger.loop(f">>>> WSS <<<< {cache_id} OK! Height: {el.blockheight}")
            elif "block_height" in el.result:
                el.blockheight = int(el.result['block_height'])
                el.last_connection = int(time.time())
                # logger.loop(f">>>> WSS <<<< {cache_id} OK! Height: {el.blockheight}")
            
        if el.blockheight != -1:
            data = {
                "coin": coin,
                "url": url,
                "port": port,
                "protocol": el.protocol,
                "result": "Passed",
                "blockheight": el.blockheight,
                "last_connection": el.last_connection
            }
            # logger.merge(f">>>> WSS <<<< {cache_id} OK! Height: {el.blockheight}")
            cache(f"{cache_id}", data, 300)
        else:
            logger.merge(f">>>> WSS <<<< {cache_id} Failed! | {el.blockheight} | {resp}")
            data = {
                "coin": coin,
                "url": url,
                "port": port,
                "protocol": el.protocol,
                "result": el.result,
                "blockheight": el.blockheight,
                "last_connection": el.last_connection
            }
            cache(f"{cache_id}", data, 60)

    except Exception as e:
        logger.error(f"{cache_id} Failed! {e} | {resp}")


def thread_electrum(coin, url, port, method, params):
    try:
        el = ElectrumServer(coin, url, port, "TCP")
        cache_id = f"{coin}-{url}-{port}-TCP"
        data = get(cache_id)
        if data is not None:
            logger.info(f"Using cache for {cache_id}")
            el.result = data["result"]
            el.blockheight = data["blockheight"]
            el.last_connection = data["last_connection"]
        else:
            el.tcp("blockchain.headers.subscribe", [])
            resp = el.tcp(method, params)
            if len(str(resp)) < 5:
                logger.calc(f"{cache_id}: {resp}")
            if str(resp).lower().find('timeout') > -1:
                el.result = "Timeout"
            elif str(resp).lower().find('refused') > -1:
                el.result = "Connection refused"
            elif str(resp).lower().find('oserror') > -1:
                el.result = "OS Error"
            elif str(resp).lower().find('gaierror') > -1:
                el.result = "Gai Error"
            elif "result" in json.loads(resp):
                el.result = json.loads(resp)['result']
            elif "params" in json.loads(resp):
                el.result = json.loads(resp)['params'][0]
            else:
                logger.error(f"Unable to get result for {cache_id}")
                logger.error(json.loads(resp))

            if "height" in el.result:
                el.blockheight = int(el.result['height'])
                el.last_connection = int(time.time())
                # logger.loop(f">>>> TCP <<<< {cache_id} OK! Height: {el.blockheight}")
            elif "block_height" in el.result:
                el.blockheight = int(el.result['block_height'])
                el.last_connection = int(time.time())
                # logger.loop(f">>>> TCP <<<< {cache_id} OK! Height: {el.blockheight}")
                
            if el.blockheight != -1:
                data = {
                    "coin": coin,
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": "Passed",
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                # logger.merge(f">>>> TCP <<<< {cache_id} OK! Height: {el.blockheight}")
                cache(cache_id, data, 300)
            else:
                logger.merge(f">>>> TCP <<<< {cache_id} Failed! | {el.blockheight} | {resp}")
                data = {
                    "coin": coin,
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": el.result,
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                cache(cache_id, data, 60)
        # logger.query(data)

    except Exception as e:
        logger.error(f">>>> TCP <<<< {cache_id} Failed! {e} | {resp}")


def thread_electrum_ssl(coin, url, port, method, params):
    try:
        el = ElectrumServer(coin, url, port, "SSL")
        cache_id = f"{coin}-{url}-{port}-SSL"
        data = get(cache_id)
        if data is not None:
            logger.info(f"Using cache for {cache_id}")
            el.result = data["result"]
            el.blockheight = data["blockheight"]
            el.last_connection = data["last_connection"]
        else:
            el.ssl("blockchain.headers.subscribe", [])
            resp = el.ssl(method, params)

            if str(resp).lower().find('timeout') > -1:
                el.result = "Timeout"
            elif str(resp).lower().find('refused') > -1:
                el.result = "Connection refused"
            elif str(resp).lower().find('oserror') > -1:
                el.result = "OS Error"
            elif str(resp).lower().find('gaierror') > -1:
                el.result = "Gai Error"
            elif "result" in json.loads(resp):
                el.result = json.loads(resp)['result']
            elif "params" in json.loads(resp):
                el.result = json.loads(resp)['params'][0]
            else:
                logger.error(f"Unable to get result for {cache_id}")
                logger.error(json.loads(resp))

            if "height" in el.result:
                el.blockheight = int(el.result['height'])
                el.last_connection = int(time.time())
                # logger.loop(f">>>> SSL <<<< {cache_id} OK! Height: {el.blockheight}")
            elif "block_height" in el.result:
                el.blockheight = int(el.result['block_height'])
                el.last_connection = int(time.time())
                # logger.loop(f">>>> SSL <<<< {cache_id} OK! Height: {el.blockheight}")

            if el.blockheight > -1:
                data = {
                    "coin": coin,
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": "Passed",
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                # logger.merge(f">>>> SSL <<<< {cache_id} OK! Height: {el.blockheight}")
                cache(cache_id, data, 300)
            else:
                logger.merge(f">>>> SSL <<<< {cache_id} Failed! | {el.blockheight} | {resp}")
                data = {
                    "coin": coin,
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": el.result,
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                cache(cache_id, data, 60)


    except Exception as e:
        logger.error(f"{cache_id} Failed! {e} | {resp}")


def scan_electrums(electrum_dict):
    thread_list = []

    for coin in electrum_dict:
        for electrum in electrum_dict[coin]:
            if 'url' in electrum:
                url, port = electrum["url"].split(":")
                if "protocol" in electrum:
                    thread_list.append(
                        scan_thread(
                            coin,
                            url,
                            port,
                            "blockchain.headers.subscribe",
                            [],
                            electrum["protocol"].lower()
                        )
                    )

        
    for thread in thread_list:
        thread.start()
        time.sleep(0.2)


def get_repo_electrums():
    try:
        repo_electrums = get("repo_electrums")
        if repo_electrums is not None:
            return repo_electrums
        repo_electrums = {}
        with open(f"{repo_path}/coins_config.json", "r") as f:
            coins_data = json.load(f)
            for coin in coins_data:
                if 'electrum' in coins_data[coin]:
                    repo_electrums.update({coin: coins_data[coin]["electrum"]})
            cache("repo_electrums", repo_electrums, 43100)
            # TODO: Scan for EVM nodes
    except json.decoder.JSONDecodeError:
        print(f"electrums failed to parse, exiting.")
        sys.exit(1)
    return repo_electrums


def get_electrums_report():
    electrum_dict = get_repo_electrums()
    num_electrums = sum([len(electrum_dict[i]['electrum']) for i in electrum_dict if 'electrum' in electrum_dict[i]])
    logger.info(f"{num_electrums} electrum servers to scan...")
    scan_electrums(electrum_dict)


def get_electrum_dict_servers(electrum_dict):
    electrum_dict_servers = get("electrum_dict_servers")
    if electrum_dict_servers is not None:
        return electrum_dict_servers
    electrum_dict_servers = []
    for coin in electrum_dict:
        if "electrum" in electrum_dict[coin]:
            for x in electrum_dict[i]["electrum"]:
                electrum_dict_servers.append(x)
    cache("electrum_dict_servers", electrum_dict_servers, 3600)
    return electrum_dict_servers


def update_db():
    try:
        db_coins = lib_sqlite.get_db_coins()
        db_servers = lib_sqlite.get_db_servers()
        electrum_dict = get_repo_electrums()
        electrum_dict_servers = get_electrum_dict_servers(electrum_dict)

        for coin in electrum_dict:
            # logger.calc(f"{len(electrum_dict[coin])} servers for {coin}")

            for x in db_coins:
                if x not in electrum_dict.keys():
                    print(f"Deleting {x}")
                    lib_sqlite.delete_electrum_coin(x)
            '''
            for x in db_servers:
                if x not in electrum_dict_servers:
                    print(f"Deleting {x}")
                    lib_sqlite.delete_electrum_server(x)
            '''
            for electrum in electrum_dict[coin]:
                if electrum["url"] not in db_servers:
                    logger.warning(f'{electrum["url"]} not in db_servers!')
                if "url" in electrum:
                    url, port = electrum["url"].split(":")
                    for i in ["TCP", "SSL", "WSS"]:
                        data = get(f"{coin}-{url}-{port}-{i}")
                        if data is not None:
                            add_row(data)
    except Exception as e:
        logger.warning(e)


def add_row(data):
    data['result'] = str(data['result']).replace("'", "")
    if int(data['blockheight']) > 0:
        row = (
            data['coin'],
            f"{data['url']}:{data['port']}",
            data['protocol'],
            "Passed",
            int(data['blockheight']),
            int(data['last_connection'])
        )
        lib_sqlite.update_electrum_row(row)
    else:
        row = (
            data['coin'],
            f"{data['url']}:{data['port']}",
            data['protocol'],
            data['result'],
            int(data['blockheight']),
            int(data['last_connection'])
        )
        lib_sqlite.update_electrum_row_failed(row)


if __name__ == '__main__':
    get_electrums_report()
