#!/usr/bin/env python3
import requests
import time
import hmac
from lib.config import ConfigFastAPI


class BanxaAPI2():
    def __init__(self) -> None:
        self.config = ConfigFastAPI()
        self.url = self.config.BANXA_URL
        self.key = self.config.BANXA_KEY
        self.secret = bytes(self.config.BANXA_SECRET, 'utf8')

    
    def generateHmac(self, payload, nonce):
        hmacCode = hmac.digest(self.secret, payload.encode('utf8'), 'SHA256')
        print(payload)
        print(hmacCode.hex())
        return self.key + ':' + hmacCode.hex() + ':' + str(nonce)


    def sendGetRequest(self, query):
        nonce = int(time.time())
        data = 'GET\n' + query + '\n' + str(nonce)
        authHeader = self.generateHmac(data, nonce)
        url = self.url + query
        print(url)
        response = requests.get(url,
            headers = {
                    'Authorization': 'Bearer ' + authHeader,
                    'Content-Type': 'application/json'
            })
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content


    def sendPostRequest(self, query, payload):
        nonce = int(time.time())
        data = 'POST\n' + query + '\n' + str(nonce) + '\n' + payload
        authHeader = self.generateHmac(data, nonce)
        url = self.url + query
        print(url)
        response = requests.post(url,
            data = payload,
            headers = {
                    'Authorization': 'Bearer ' + authHeader,
                    'Content-Type': 'application/json'
            })
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content