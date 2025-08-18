import pandas as pd
import json

with open("event_test_data.json", "r", encoding='utf-8') as file:
    data = json.load(file)

df = pd.json_normalize(data['event'])

df.to_csv("events.csv", index=False, encoding='utf-8')
