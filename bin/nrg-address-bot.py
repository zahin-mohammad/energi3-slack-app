#!/usr/bin/env python3

import os
import sys
import requests
import json
import math
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Create service account JSON file
FIRESTORE_JSON = os.getenv('webhook') 
print(FIRESTORE_JSON)
WEBHOOK = os.getenv('webhook')
ADDRESS_STRING = os.getenv('addressList')

if WEBHOOK is None or ADDRESS_STRING is None or FIRESTORE_JSON is None :
    print("error: forgot env variables")
    sys.exit()

with open("firestore-admin.json", "w") as jsonFile:
    jsonFile.write(FIRESTORE_JSON)

cred = credentials.Certificate('firestore-admin.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Differentiate people by their slack webhook
doc_ref = db.collection("NRG").document(WEBHOOK[-24:])

addressList = ADDRESS_STRING.split(' ')

URL_BASE = "https://explorer.energi.network/api"
URL_MULTI_ADDRESS_BALANCE = f"?module=account&action=balancemulti&address={','.join([str(address) for address in addressList])}"
URL_PRICE = "https://explorer.energi.network/api?module=stats&action=ethprice"
FILENAME = "lastChecked.json"


try:
    currentPrice = ((requests.get(URL_PRICE)).json())["result"]

    addressMap = {}
    response = requests.get(f"{URL_BASE}{URL_MULTI_ADDRESS_BALANCE}")
    # Get accounts NRG balance
    for account in response.json()['result']:
        address = account["account"]
        addressMap[address] = {"NRG": float(account["balance"]) / math.pow(10, 18)}

    # Get accounts token balances
    for address in addressList:
        URL_TOKEN_BALANCE = f"?module=account&action=tokenlist&address={address.lower()}"
        response = requests.get(f"{URL_BASE}{URL_TOKEN_BALANCE}")

        for token in (response.json())["result"]:
            sym = token["symbol"]
            name = token["name"]
            decimals = int(token["decimals"])
            balance = float(token["balance"])/math.pow(10, decimals)
            addressMap[address.lower()][sym] = balance

    # see what changed from last poll
    doc_ref = db.collection("NRG").document(WEBHOOK[-24:])
    doc = doc_ref.get()
    addressMapDiff = {}

    if doc.exists:
        data = doc.to_dict()
        for key in addressMap.keys():
            if addressMap[key] != data[key]:
                addressMapDiff[key] = data[key]
    else:
        # send slack message on first run
        messageBlocks = []
        messageBlocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Thanks for using NRG-bot! <https://github.com/zahin-mohammad/nrg-slack-app|Source Code!>\n"
            }
        })

        for key, value in addressMap.items():
            URL_EXPLORER = f"<https://explorer.energi.network/address/{key}|{key}>"
            
            for token, currentBalance in value.items():
                tokenInfo = f"{token}: \n\tFiat: ${float(currentPrice['ethusd'])*currentBalance} USD \n\tCurrent: {currentBalance}"

            messageBlocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"`{URL_EXPLORER}`\n{tokenInfo}"
                }
            })

        requests.post(WEBHOOK, data=json.dumps({"blocks": messageBlocks}), headers={
                    'Content-Type': 'application/json'}, verify=True)

    # send slack message on change from last poll
    if len(addressMapDiff) != 0:
        messageBlocks = []
        messageBlocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Some of your addresses have balance changes!\n"
            }
        })

        for key, value in addressMapDiff.items():

            URL_EXPLORER = f"<https://explorer.energi.network/address/{key}|{key}>"
            
            for token, prevBalance in value.items():
                currentBalance = addressMap[key][token]
                diff = currentBalance - prevBalance
                emoji = ":red_circle:" if currentBalance < prevBalance else ":large_blue_circle:"
                tokenInfo = f"{token}: {emoji}\n\tFiat: ${float(currentPrice['ethusd'])*currentBalance} USD \n\tDifference: {diff}\n\tCurrent: {currentBalance}\n\tPrevious: {prevBalance}\n"

            messageBlocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"`{URL_EXPLORER}`\n{tokenInfo}"
                }
            })

        requests.post(WEBHOOK, data=json.dumps({"blocks": messageBlocks}), headers={
                    'Content-Type': 'application/json'}, verify=True)
                    
    # write data to firestore
    doc_ref.set(addressMap)

except:
    response = requests.post(WEBHOOK, data=json.dumps({'text': "error, check heroku logs"}), headers={'Content-Type': 'application/json'} , verify=True)
