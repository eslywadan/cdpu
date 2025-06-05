from grpc_cust.clientapival_client import get_clientinfo, get_clientapikey, get_verified_apikey


def test_clientapival_client():
    info = get_clientinfo("mfg")
    assert info is not None

    apikey = get_clientapikey("IamWrongClient","IamWrongClient")
    assert apikey.expiry == "1900-01-01"

    apikey = get_clientapikey("mfg","mfg")
    token = apikey.apikey

    verifiedresult = get_verified_apikey(token)
    assert verifiedresult.assertion.split(":")[2] == "/mfg"

    apikey = get_clientapikey("eng","eng")
    token = apikey.apikey
    verifiedresult = get_verified_apikey(token)
    assert verifiedresult.assertion.split(":")[2] == "/eng"
    

    
