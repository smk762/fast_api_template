#!/usr/bin/env python3
import requests
import time
import hmac
from lib.config import ConfigFastAPI


class RampAPI:
    def __init__(self) -> None:
        self.config = ConfigFastAPI()
        self.url = self.config.API_URLS["RAMP"]
        self.key = self.config.API_KEYS["RAMP"]

    def get_headers(self, endpoint, request, payload=None):
        return {"Content-Type": "application/json"}

    def sendGetRequest(self, request):
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        headers = self.get_headers(endpoint, request)
        url = self.url + endpoint
        print(url)
        url += (
            "?hostApiKey="
            + self.key
            + "&".join(
                [f"{k}={v}" for k, v in request.query_params.items() if k != "endpoint"]
            )
        )

        print(url)
        response = requests.get(url=url, headers=self.get_headers(endpoint, request))
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content

    def sendPostRequest(self, request, payload):
        endpoint = request.query_params["endpoint"]
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = self.url + endpoint + "?hostApiKey=" + self.key
        print(url)
        response = requests.post(
            url=url,
            json=payload,
            headers=self.get_headers(endpoint, request, payload),
        )
        try:
            return response.json()
        except Exception as e:
            print(e)
        return response.content
