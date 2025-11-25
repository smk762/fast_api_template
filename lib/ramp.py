#!/usr/bin/env python3
import requests
import time
import hmac
from lib.config import ConfigFastAPI
from lib.logger import logger


class RampAPI:
    def __init__(self) -> None:
        self.config = ConfigFastAPI()
        self.url = self.config.API_URLS["RAMP_PROD"]
        self.key = self.config.API_KEYS["RAMP_PROD"]
        self.test_url = self.config.API_URLS["RAMP"]
        self.test_key = self.config.API_KEYS["RAMP"]
        self.headers = {"Content-Type": "application/json"}

    def get_params(self, request):
        return "&".join(
                [f"{k}={v}" for k, v in request.query_params.items() if k not in ["endpoint", "is_test_mode"]]
            )
        
    def sendGetRequest(self, request):
        url = self.url
        key = self.key
        if "is_test_mode" in request.query_params:
            if request.query_params["is_test_mode"].lower() == "true":
                logger.info("Using test mode")
                url = self.test_url
                key = self.test_key
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
            
        url = url + endpoint
        url_params = self.get_params(request)
        if endpoint not in ["/currencies"]:
            url += "?hostApiKey=" + key + '&' + url_params
        else:
            url += "?" + url_params

        response = requests.get(url=url, headers=self.headers)
        try:
            resp = response.json()
            if "message" in resp:
                if key in resp["message"]:
                    resp["message"] = resp["message"].replace(key, "<***API***KEY***>")
            return resp
        except Exception as e:
            print(e)
            print(response.content)
        return {"error": "Invalid response from Ramp API. Check logs for details."}

    def sendPostRequest(self, request, payload):
        url = self.url
        key = self.key
        if "is_test_mode" in request.query_params:
            if request.query_params["is_test_mode"].lower() == "true":
                logger.info("Using test mode")
                url = self.test_url
                key = self.test_key
        endpoint = request.query_params["endpoint"]



        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = url + endpoint
        if endpoint not in ["/currencies"]:
            url += "?hostApiKey=" + key
        print(url)
        response = requests.post(
            url=url,
            json=payload,
            headers=self.headers,
        )
        try:
            resp = response.json()
            if "message" in resp:
                if key in resp["message"]:
                    resp["message"] = resp["message"].replace(key, "<***API***KEY***>")
            return resp
        except Exception as e:
            print(e)
            print(response.content)
        return {"error": "Invalid response from Ramp API. Check logs for details."}

