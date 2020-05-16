#!/usr/bin/env python3

import os
import requests
import json
import math



webhook = os.getenv('webhook') # None
addressString = os.getenv('addressList')
addressList = addressString.split(' ')
print(addressList)
print(webhook)
if webhook is None or addressList is None or len(addressList) == 0:
    print("error: forgot env variables") 

baseURL = "https://explorer.energi.network/api"
multiAddressBalance = f"?module=account&action=balancemulti&address={','.join([str(address) for address in addressList])}"

addressMap = {}
try:
    response = requests.get(f"{baseURL}{multiAddressBalance}")
    for account in response.json()['result']:
        addressMap[account["account"]] = float(account["balance"]) / math.pow(10,18)
    print(addressMap)
    response = requests.post(webhook, data=json.dumps({'text':json.dumps(addressMap, indent=2)}), headers={'Content-Type': 'application/json'} , verify=True)
except:
    response = requests.post(webhook, data=json.dumps("error"), headers={'Content-Type': 'application/json'} , verify=True)
