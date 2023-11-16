#!/usr/bin/env python3
import requests
import time
import hmac
import json
from lib.config import ConfigFastAPI


class BanxaAPI:
    def __init__(self) -> None:
        self.config = ConfigFastAPI()
        self.url = self.config.API_URLS["BANXA"]
        self.key = self.config.API_KEYS["BANXA"]
        self.secret = bytes(self.config.API_SECRETS["BANXA"], "utf8")

    def generateHmac(self, payload, nonce):
        hmacCode = hmac.digest(self.secret, payload.encode('utf8'), 'SHA256')
        return self.key + ':' + hmacCode.hex() + ':' + str(nonce)

    def get_headers(self, endpoint, request, payload=None):
        newline = "\n"
        nonce = int(time.time())
        if request.method == "POST":
            data = 'POST\n' + endpoint + '\n' + str(nonce) + '\n' + payload
        else:
            endpoint += "?" + "&".join([
                f"{k}={v}" for k, v in request.query_params.items()
                if k != "endpoint"
            ])
            data = f"GET{newline}{endpoint}{newline}{nonce}"
        return {
            "Authorization": f"Bearer {self.generateHmac(data, nonce)}",
            "Content-Type": "application/json",
        }

    def sendGetRequest(self, request):
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        headers = self.get_headers(endpoint, request)
        url = self.url + endpoint
        print(url)
        url += "?" + "&".join([
                f"{k}={v}" for k, v in request.query_params.items()
                if k != "endpoint"
            ])
        response = requests.get(
            url=url,
            headers=headers
        )
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content

    def sendPostRequest(self, request, payload):
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        headers = self.get_headers(endpoint, request, payload)

        response = requests.post(
            self.url + endpoint,
            data = payload,
            headers=headers
        )
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content

