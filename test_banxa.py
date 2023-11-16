#!/usr/bin/env python3
import requests
import time
import hmac

url = 'https://banxa-test.komodo.earth'
# url = 'https://komodo.banxa-sandbox.com'
key = 'Komodo@test060720231102'
secret = b's8GOYVr61h3fkptAuPvi420BXMSAFCBn'

def generateHmac(payload, nonce):
    hmacCode = hmac.digest(secret, payload.encode('utf8'), 'SHA256')
    print(payload)
    print(hmacCode.hex())
    return key + ':' + hmacCode.hex() + ':' + str(nonce)

def sendGetRequest(query):
    nonce = int(time.time())
    data = 'GET\n' + query + '\n' + str(nonce)
    authHeader = generateHmac(data, nonce)
    response = requests.get(url + query,
        headers = {
                'Authorization': 'Bearer ' + authHeader,
                'Content-Type': 'application/json'
        })

    print(response.content)

def sendPostRequest(query, payload):
    nonce = int(time.time())
    print("------------------")
    print("nonce: ", nonce)
    print("payload: ", payload)
    print("endpoint: ", query)
    print("@@@@@@@@@@@@@@@@@@@@")
    data = 'POST\n' + query + '\n' + str(nonce) + '\n' + payload
    print(data)
    print("@@@@@@@@@@@@@@@@@@@@")
    authHeader = generateHmac(data, nonce)
    headers = {
            'Authorization': 'Bearer ' + authHeader,
            'Content-Type': 'application/json'
    }
    print(authHeader)
    print("headers: ", headers)
    print("url + query: ", url + query)
    print("------------------")
    
    
    response = requests.post(
        url + query,
        data = payload,
        headers=headers
    )

    print(response.content)

# sendGetRequest('/api/fiats')

print('----')

sendPostRequest('/api/orders', '{"account_reference":"test01","source":"USD","target":"BTC","source_amount":"100","return_url_on_success":"test.com","wallet_address":"35Rwwc9e2Mj7smFXJ1iXF826cMW3tqfz6x"}')
