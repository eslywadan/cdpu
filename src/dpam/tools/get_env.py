import os

if "api_account_env" in os.environ.keys(): env = os.environ["api_account_env"] 
else: env = "prd"

