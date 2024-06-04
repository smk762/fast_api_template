#!/usr/bin/env python3
import os
import sys
import ssl
import json
import time
import socket
import threading
import requests
import asyncio
import websockets
import lib_sqlite
from lib_logger import logger
from pymemcache.client.base import PooledClient
from web3 import Web3, AsyncWeb3, WebsocketProviderV2
from web3.middleware import geth_poa_middleware
from lib_sqlite import StatusDB



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


class Web3Server():
    __slots__ = ("coin", "url", "protocol", "result", "blockheight", "last_connection")
    
    def __init__(self, coin, url, protocol):
        self.coin = coin
        self.url = url
        self.protocol = protocol
        self.result = None
        self.blockheight = -1
        self.last_connection = -1
                        
    def get_latest_block(self):
        if self.protocol == "WSS":
            try:
                async def connect_and_query():
                    url = self.url.replace("https://", "wss://").replace("http://", "ws://")
                    async with AsyncWeb3(WebsocketProviderV2(url)) as w3:
                        try:
                            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                            return await w3.get_block('latest')
                        except Exception as e:
                            return "server rejected WebSocket connection"
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                status = loop.run_until_complete(connect_and_query())
                if 'number' in status:
                    self.blockheight = int(status['number'])
                    self.last_connection = int(time.time())
                    self.result = "Passed"
                else:            
                    #logger.error(f"[{self.protocol}] {self.coin} {self.url} Failed | {self.result}")
                    self.result = status
            except Exception as e:
                # logger.error(f"[{self.protocol}] {self.coin} {self.url} Failed | {e}")
                self.result = "server rejected WebSocket connection"
        else:
            try:
                w3 = Web3(Web3.HTTPProvider(self.url))
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                data = w3.eth.get_block('latest')
                if 'number' in data:
                    self.blockheight = int(data['number'])
                    self.last_connection = int(time.time())
                    self.result = "Passed"
                else:            
                    logger.error(f"[{self.protocol}] {self.coin} {self.url} Failed | {self.result}")
                    self.result = data
            except Exception as e:
                # logger.error(f"[{self.protocol}] {self.coin} {self.url} Failed | {e}")
                if str(e).find('401 Client Error: Unauthorized') > -1:
                    self.result == "401 Client Error: Unauthorized"
                else:
                    self.result = e


class scan_evm_thread(threading.Thread):
    def __init__(self, coin, url):
        threading.Thread.__init__(self)
        self.coin = coin
        self.url = url

    def run(self):
        try:
            cache_id = f"EVM-{self.url}-WSS"
            data = get(cache_id)
            if data is None:
                el_wss = Web3Server(
                    self.coin,
                    self.url,
                    "WSS"
                )
                el_wss.get_latest_block()
                if el_wss.blockheight > 0: 
                    result = "Passed"
                    logger.loop(f">>>> WSS <<<< {cache_id} OK! Height: {el_wss.blockheight}")
                else:
                    result = el_wss.result
                    # logger.warning(f">>>> WSS <<<< {cache_id} Failed! | {el_wss.blockheight} | {result}")
                data = {
                    "coin": self.coin,
                    "category": "EVM",
                    "url": self.url,
                    "port": "",
                    "protocol": "WSS",
                    "result": str(result),
                    "blockheight": el_wss.blockheight,
                    "last_connection": el_wss.last_connection
                }
                cache(f"{cache_id}", data, 300)
                add_row(data)
        except Exception as e:
            logger.warning(f"{cache_id}: {e}")

        try:
            cache_id = f"EVM-{self.url}-SSL"
            data = get(cache_id)
            if data is None:
                el_ssl = Web3Server(self.coin, self.url, "SSL")
                el_ssl.get_latest_block()
                if el_ssl.blockheight > 0: 
                    result = "Passed"
                    # logger.info(f">>>> SSL <<<< {cache_id} OK! Height: {el_ssl.blockheight}")
                else:
                    result = el_ssl.result
                    # logger.warning(f">>>> SSL <<<< {cache_id} Failed! | {el_ssl.blockheight} | {result}")
                data = {
                    "coin": self.coin,
                    "category": "EVM",
                    "url": self.url,
                    "port": "",
                    "protocol": "SSL",
                    "result": str(result),
                    "blockheight": el_ssl.blockheight,
                    "last_connection": el_ssl.last_connection
                }
                cache(f"{cache_id}", data, 300)
                add_row(data)
        except Exception as e:
            logger.warning(f"{cache_id}: {e}")


class TendermintServer():
    __slots__ = ("coin", "url", "protocol", "result", "blockheight", "last_connection")
    
    def __init__(self, coin, url, protocol):
        self.coin = coin
        self.url = url
        self.protocol = protocol
        self.result = None
        self.blockheight = -1
        self.last_connection = -1
        if self.protocol == "WSS":
            self.url = f"{self.url}/websocket".replace("https://", "wss://").replace("http://", "ws://")
        
    def get_latest_block(self):
            if self.url.endswith("websocket"):

                try:
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    async def connect_and_query():
                        async with websockets.connect(self.url, ssl=ssl_context, timeout=10) as websocket:
                            # Request
                            payload = {"id": 0, "method": "status", "params": []}
                            await websocket.send(json.dumps(payload))
                            await asyncio.sleep(1)
                            status = await asyncio.wait_for(websocket.recv(), timeout=7)
                            status = status.splitlines()
                            if len(status) > 0:
                                status = status[-1]
                            return status
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    status = json.loads(loop.run_until_complete(connect_and_query()))
                    if 'result' in status:
                        if 'sync_info' in status['result']:
                            if 'latest_block_height' in status['result']['sync_info']:
                                self.blockheight = int(status['result']['sync_info']["latest_block_height"])
                                self.last_connection = int(time.time())
                                self.result = "Passed"
                except Exception as e:
                    self.result = f"{e} | {self.result}"
            else:
                try:
                    status = requests.get(f"{self.url}/status").json()
                    if 'result' in status:
                        if 'sync_info' in status['result']:
                            if 'latest_block_height' in status['result']['sync_info']:
                                self.blockheight = int(status['result']['sync_info']["latest_block_height"])
                                self.last_connection = int(time.time())
                                self.result = "Passed"
                    else:            
                        logger.error(f"[{self.protocol}] {self.coin} {self.url} Failed | {self.result}")
                        self.result = status
                except Exception as e:
                    logger.error(f"[{self.protocol}] {self.coin} {self.url} Failed | {e}")
                    self.result = f"{e} | {self.result}"


class scan_tendermint_thread(threading.Thread):
    def __init__(self, coin, url):
        threading.Thread.__init__(self)
        self.coin = coin
        self.url = url

    def run(self):
        try:
            cache_id = f"TENDERMINT-{self.coin}-{self.url}-WSS"
            logger.calc(cache_id)
            data = get(cache_id)
            if data is None:
                el_wss = TendermintServer(self.coin, self.url, "WSS")
                el_wss.get_latest_block()
                if el_wss.blockheight > 0: 
                    result = "Passed"
                    # logger.info(f">>>> WSS <<<< {cache_id} OK! Height: {el_wss.blockheight}")
                else:
                    result = el_wss.result
                    # logger.warning(f">>>> WSS <<<< {cache_id} Failed! | {el_wss.blockheight} | {result}")

                data = {
                    "coin": self.coin,
                    "category": "Tendermint",
                    "url": self.url,
                    "port": "",
                    "protocol": "WSS",
                    "result": str(result),
                    "blockheight": el_wss.blockheight,
                    "last_connection": el_wss.last_connection
                }
                cache(f"{cache_id}", data, 300)
                add_row(data)
        except Exception as e:
            logger.error(f"{cache_id} Failed | {e}")
            self.result = f"{e} | {self.result}"
                
        try:
            cache_id = f"TENDERMINT-{self.coin}-{self.url}-SSL"
            data = get(cache_id)
            if data is None:
                el_ssl = TendermintServer(self.coin, self.url, "SSL")
                el_ssl.get_latest_block()
                if el_ssl.blockheight > 0: 
                    result = "Passed"
                    # logger.info(f">>>> SSL <<<< {cache_id} OK! Height: {el_ssl.blockheight}")
                else:
                    result = el_ssl.result
                    # logger.warning(f">>>> SSL <<<< {cache_id} Failed! | {el_ssl.blockheight} | {result}")
                    
                data = {
                    "coin": self.coin,
                    "category": "Tendermint",
                    "url": self.url,
                    "port": "",
                    "protocol": "SSL",
                    "result": str(result),
                    "blockheight": el_ssl.blockheight,
                    "last_connection": el_ssl.last_connection
                }
                cache(f"{cache_id}", data, 300)
                add_row(data)
        except Exception as e:
            logger.error(f"{cache_id} Failed | {e}")
            self.result = f"{e} | {self.result}"


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
                payload = {"id": 0, "method": "server.version", "params": ["kmd_coins_repo", ["1.4", "1.6"]]}
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
                    payload = {"id": 0, "method": "server.version", "params": ["kmd_coins_repo", ["1.4", "1.6"]]}
                    ssock.send(json.dumps(payload).encode() + b'\n')
                    time.sleep(1)
                    resp = ssock.recv(999999)[:-1].decode()
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
                    payload = {"id": 0, "method": "server.version", "params": ["kmd_coins_repo", ["1.4", "1.6"]]}
                    await websocket.send(json.dumps(payload))
                    await asyncio.sleep(1)
                    resp = await asyncio.wait_for(websocket.recv(), timeout=7)
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


class scan_electrum_thread(threading.Thread):
    def __init__(self, coin, url, port, method, params=None, protocol='TCP'):
        threading.Thread.__init__(self)
        self.coin = coin
        self.url = url
        self.port = port
        self.method = method
        self.params = params
        self.protocol = protocol

    def run(self):
        if self.protocol.lower() == "ssl":
            thread_electrum_ssl(self.coin, self.url, self.port, self.method, self.params)
        elif self.protocol.lower() == "tcp":
            thread_electrum(self.coin, self.url, self.port, self.method, self.params)
        elif self.protocol.lower() == "wss":
            thread_electrum_wss(self.coin, self.url, self.port, self.method, self.params)


def thread_electrum_wss(coin, url, port, method, params):
    try:
        el = ElectrumServer(coin, url, port, "WSS")
        cache_id = f"Electrum-{coin}-{url}-{port}-WSS"
        data = get(cache_id)
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
            elif "block_height" in el.result:
                el.blockheight = int(el.result['block_height'])
                el.last_connection = int(time.time())
            
        if el.blockheight != -1:
            data = {
                "coin": coin,
                "category": "Electrum",
                "url": url,
                "port": port,
                "protocol": el.protocol,
                "result": "Passed",
                "blockheight": el.blockheight,
                "last_connection": el.last_connection
            }
            # logger.loop(f">>>> WSS <<<< {cache_id} OK! Height: {el.blockheight}")
            cache(f"{cache_id}", data, 300)
        else:
            logger.warning(f">>>> WSS <<<< {cache_id} Failed! | {el.blockheight} | {el.result}")
            data = {
                "coin": coin,
                "category": "Electrum",
                "url": url,
                "port": port,
                "protocol": el.protocol,
                "result": str(el.result),
                "blockheight": el.blockheight,
                "last_connection": el.last_connection
            }
            cache(f"{cache_id}", data, 300)

    except Exception as e:
        logger.error(f"{cache_id} Failed! {e} | {resp}")


def thread_electrum(coin, url, port, method, params):
    try:
        el = ElectrumServer(coin, url, port, "TCP")
        cache_id = f"Electrum-{coin}-{url}-{port}-TCP"
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
            elif "block_height" in el.result:
                el.blockheight = int(el.result['block_height'])
                el.last_connection = int(time.time())
                
            if el.blockheight != -1:
                data = {
                    "coin": coin,
                    "category": "Electrum",
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
                logger.warning(f">>>> TCP <<<< {cache_id} Failed! | {el.blockheight} | {el.result}")
                data = {
                    "coin": coin,
                    "category": "Electrum",
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": str(el.result),
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                cache(cache_id, data, 300)
        # logger.query(data)

    except Exception as e:
        logger.error(f">>>> TCP <<<< {cache_id} Failed! {e} | {resp}")


def thread_electrum_ssl(coin, url, port, method, params):
    try:
        el = ElectrumServer(coin, url, port, "SSL")
        cache_id = f"Electrum-{coin}-{url}-{port}-SSL"
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
            elif "block_height" in el.result:
                el.blockheight = int(el.result['block_height'])
                el.last_connection = int(time.time())

            if el.blockheight > -1:
                data = {
                    "coin": coin,
                    "category": "Electrum",
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": "Passed",
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                # logger.info(f">>>> SSL <<<< {cache_id} OK! Height: {el.blockheight}")
                cache(cache_id, data, 300)
            else:
                logger.warning(f">>>> SSL <<<< {cache_id} Failed! | {el.blockheight} | {el.result}")
                data = {
                    "coin": coin,
                    "category": "Electrum",
                    "url": url,
                    "port": port,
                    "protocol": el.protocol,
                    "result": str(el.result),
                    "blockheight": el.blockheight,
                    "last_connection": el.last_connection
                }
                cache(cache_id, data, 300)


    except Exception as e:
        logger.error(f"{cache_id} Failed! {e} | {data}")


def scan_coin_servers(electrum_dict, evm_dict, tendermint_dict):
    thread_list = []      
    try:
        tendermint_dict = get_repo_tendermint_servers()
        logger.info(f"Tendermint servers: {len(tendermint_dict)}")
        for coin in tendermint_dict:
            for server in tendermint_dict[coin]:
                url = server["url"]
                thread_list.append(
                    scan_tendermint_thread(
                        coin,
                        url
                    )
                )
    except Exception as e:
        logger.warning(e)
  
    try:
        evm_dict = get_repo_evm_servers()
        logger.info(f"EMV servers: {len(evm_dict)}")
        for coin in evm_dict:
            for server in evm_dict[coin]:
                url = server["url"]
                thread_list.append(
                    scan_evm_thread(
                        coin,
                        url
                    )
                )
    except Exception as e:
        logger.warning(e)

    try:
        for coin in electrum_dict:
            for electrum in electrum_dict[coin]:
                if 'url' in electrum:
                    url, port = electrum["url"].split(":")
                    if "protocol" in electrum:
                        thread_list.append(
                            scan_electrum_thread(
                                coin,
                                url,
                                port,
                                "blockchain.headers.subscribe",
                                [],
                                electrum["protocol"].lower()
                            )
                        )
    except Exception as e:
        logger.warning(e)

    for thread in thread_list:
        thread.start()
        time.sleep(0.1)


def get_repo_tendermint_servers():
    try:
        repo_tendermint_servers = get("repo_tendermint_servers")
        if repo_tendermint_servers is not None:
            return repo_tendermint_servers
        repo_tendermint_servers = {}
        with open(f"{repo_path}/coins_config.json", "r") as f:
            coins_data = json.load(f)
            for coin in coins_data:
                if 'rpc_urls' in coins_data[coin]:
                    repo_tendermint_servers.update({coin: coins_data[coin]["rpc_urls"]})
            cache("repo_tendermint_servers", repo_tendermint_servers, 43100)
    except json.decoder.JSONDecodeError:
        logger.error(f"repo_tendermint_servers failed to parse, exiting.")
        sys.exit(1)
    return repo_tendermint_servers


def get_repo_evm_servers():
    try:
        repo_evm_servers = get("repo_evm_servers")
        if repo_evm_servers is not None:
            return repo_evm_servers
        repo_evm_servers = {}
        with open(f"{repo_path}/coins_config.json", "r") as f:
            coins_data = json.load(f)
            for coin in coins_data:
                if 'nodes' in coins_data[coin]:
                    repo_evm_servers.update({coin: coins_data[coin]["nodes"]})
            cache("repo_evm_servers", repo_evm_servers, 43100)
    except json.decoder.JSONDecodeError:
        logger.error(f"repo_evm_servers failed to parse, exiting.")
        sys.exit(1)
    return repo_evm_servers

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
        logger.error(f"electrums failed to parse, exiting.")
        sys.exit(1)
    return repo_electrums


def update_servers_status():
    electrum_dict = get_repo_electrums()
    evm_dict = get_repo_evm_servers()
    tendermint_dict = get_repo_tendermint_servers()
    num_electrums = len(electrum_dict)
    logger.info(f"Electrum coins: {num_electrums}")
    scan_coin_servers(electrum_dict, evm_dict, tendermint_dict)


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
        DB = StatusDB()
        db_coins = DB.get_db_coins()
        db_servers = DB.get_db_servers()
        electrum_dict = get_repo_electrums()
        evm_dict = get_repo_evm_servers()
        tendermint_dict = get_repo_tendermint_servers()
        electrum_dict_servers = get_electrum_dict_servers(electrum_dict)

        all_coins = list(electrum_dict.keys()) + list(evm_dict.keys()) + list(tendermint_dict.keys())
        for x in db_coins:
            if x not in all_coins:
                print(f"Deleting {x}")
                DB.delete_electrum_coin(x)
        for coin in electrum_dict:
            for electrum in electrum_dict[coin]:
                if "url" in electrum:
                    url, port = electrum["url"].split(":")
                    for i in ["TCP", "SSL", "WSS"]:
                        data = get(f"Electrum-{coin}-{url}-{port}-{i}")
                        if data is not None:
                            add_row(data)
    except Exception as e:
        logger.warning(e)


def add_row(data):
    DB = StatusDB()
    if int(data['blockheight']) > 0:
        data["result"] ="Passed"
        DB.update_server_status(data)
    else:
        data["result"] = str(data['result']).replace("'", "")
        DB.update_server_status_failed(data)


if __name__ == '__main__':
    update_servers_status()
