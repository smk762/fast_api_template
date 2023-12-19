#!/usr/bin/env python3
import requests
import time
import hmac
import json
from lib.logger import logger
from lib.config import ConfigFastAPI


class BanxaAPI:
    def __init__(self) -> None:
        self.config = ConfigFastAPI()
        self.url = self.config.API_URLS["BANXA_PROD"]
        self.key = self.config.API_KEYS["BANXA_PROD"]
        self.secret = bytes(self.config.API_SECRETS["BANXA_PROD"], "utf8")
        
        self.test_url = self.config.API_URLS["BANXA"]
        self.test_key = self.config.API_KEYS["BANXA"]
        self.test_secret = bytes(self.config.API_SECRETS["BANXA"], "utf8")
        

    def generateHmac(self, payload, nonce, secret, key):
        hmacCode = hmac.digest(secret, payload.encode("utf8"), "SHA256")
        return key + ":" + hmacCode.hex() + ":" + str(nonce)

    def get_headers(self, endpoint, request, secret, key, payload=None):
        newline = "\n"
        nonce = int(time.time())
        if request.method == "POST":
            data = "POST\n" + endpoint + "\n" + str(nonce) + "\n" + payload
        else:
            if endpoint == "/api/orders" and "order_id" in request.query_params:
                endpoint += "/" + request.query_params["order_id"]
            else:
                endpoint += "?" + "&".join(
                    [f"{k}={v}" for k, v in request.query_params.items() if k not in ["endpoint", "is_test_mode"]]
                )
            data = 'GET\n' + endpoint + '\n' + str(nonce)
        return {
            "Authorization": f"Bearer {self.generateHmac(data, nonce, secret, key)}",
            "Content-Type": "application/json",
        }

    def sendGetRequest(self, request):
        url = self.url
        key = self.key
        secret = self.secret
        if "is_test_mode" in request.query_params:
            if request.query_params["is_test_mode"].lower() == "true":
                logger.info("Using test mode")
                url = self.test_url
                key = self.test_key
                secret = self.test_secret            
            
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        headers = self.get_headers(endpoint, request, secret, key)
        if endpoint == "/api/orders" and "order_id" in request.query_params:
            endpoint += "/" + request.query_params["order_id"]
            url += endpoint
        else:
            url += endpoint
            url += "?" + "&".join(
                [f"{k}={v}" for k, v in request.query_params.items() if k not in ["endpoint", "is_test_mode"]]
            )
        response = requests.get(url=url, headers=headers)
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content

    def sendPostRequest(self, request, payload):
        url = self.url
        key = self.key
        secret = self.secret
        if "is_test_mode" in request.query_params:
            if request.query_params["is_test_mode"].lower() == "true":
                url = self.test_url
                key = self.test_key
                secret = self.test_secret 
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        headers = self.get_headers(endpoint, request, secret, key, payload)

        response = requests.post(url + endpoint, data=payload, headers=headers)
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content
