# Below code is used for testing the apds get data

import requests
import json

# get sample conditions
url_0 =  "http://tnvpapds01/api/convertFormToJson.do" 
# querying data api 

url_1 = "http://tnvpapds01/api/generateCSV.do"

headers = {
    "Content-Type": "application/json",
    "Accept": "appliction/json"
}

response_0 = requests.post(url_0, headers=headers)

if response_0.status_code == 200:
    conditions = response_0.json()
    response = requests.post(url_1, headers=headers, json= conditions)

else: 
    print(f"response code {response_0.status_code}")