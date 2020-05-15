import os
import requests
import json
import math



webhook = os.getenv('webhook') # None
address = os.getenv('address')  

baseURL = "https://explorer.energi.network/"
summary = f"api?module=account&action=eth_get_balance&address={address}"
try:
    response = requests.get(f"{baseURL}{summary}")
    balance = int(response.json()["result"],0) / math.pow(10,18)
    data = {'text': f'-balance: {balance} NRG \n-address: {address}'}
    response = requests.post(webhook, data=json.dumps(data), headers={'Content-Type': 'application/json'} , verify=True)
except:
    response = requests.post(webhook, data=json.dumps(data), headers={'Content-Type': 'application/json'} , verify=True)
