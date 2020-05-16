#!/usr/bin/env python3

import os
import sys
import requests
import json
import math

WEBHOOK = os.getenv('webhook')  # None
ADDRESS_STRING = os.getenv('addressList')
if WEBHOOK is None or ADDRESS_STRING is None:
    print("error: forgot env variables")
    sys.exit()

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

    # used to see what changed from last poll
    addressMapDiff = {}
    if os.path.exists(FILENAME):
        with open(FILENAME) as json_file:
            data = json.load(json_file)

            for key in addressMap.keys():
                if addressMap[key] != data[key]:
                    addressMapDiff[key] = data[key]

    # send slack message on first run or on change
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

    elif not os.path.exists(FILENAME):
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


    with open(FILENAME, 'w') as outfile:
        json.dump(addressMap, outfile)

except:
    response = requests.post(WEBHOOK, data=json.dumps({'text': "error, check heroku logs"}), headers={'Content-Type': 'application/json'} , verify=True)
