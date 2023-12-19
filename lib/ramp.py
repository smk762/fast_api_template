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
        
    def get_headers(self, endpoint, request, payload=None):
        return {"Content-Type": "application/json"}

    def sendGetRequest(self, request):
        url = self.url
        key = self.key
        if "is_test_mode" in request.query_params:
            if request.query_params["is_test_mode"].lower() == "false":
                logger.info("Using test mode")
                url = self.test_url
                key = self.test_key
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        headers = self.get_headers(endpoint, request)
        url = url + endpoint
        print(url)
        url += (
            "?hostApiKey="
            + key + "&"
            + "&".join(
                [f"{k}={v}" for k, v in request.query_params.items() if k not in ["endpoint", "is_test_mode"]]
            )
        )

        print(url)
        response = requests.get(url=url, headers=self.get_headers(endpoint, request))
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
            if request.query_params["is_test_mode"].lower() == "false":
                logger.info("Using test mode")
                url = self.test_url
                key = self.test_key
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = url + endpoint + "?hostApiKey=" + key
        print(url)
        response = requests.post(
            url=url,
            json=payload,
            headers=self.get_headers(endpoint, request, payload),
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

