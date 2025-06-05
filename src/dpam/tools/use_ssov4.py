import requests

from dpam.tools.validate_user import *

"""
type: "Post",
url: baseAddr + "/api/SSO/VerifyToken",
data: JSON.stringify(data),
contentType: "application/json"
"""



ssov4_api = {"test":"https://tsamv4athe.cminl.oa/api/SSO/VerifyToken", 
             "prod":"http://psamv4athetn.cminl.oa/api/SSO/VerifyToken"}
data =  {
            "Token": "18bfeb94-2dc2-49c3-b014-1fd54fec3c6c",
            "IsCheckIP": True,
            "SysID": "datastudio"
        }
headers= {"Content-Type": "application/json"}

response = requests.post(url=ssov4_api['test'], json=data, headers=headers)