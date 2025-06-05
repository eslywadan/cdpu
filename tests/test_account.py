from dpam.tools.account import *

def test_get_client_info_grpc():
  info = get_client_info_grpc("mfg") 
  assert info.password == "28bfd0031d38c6100a0491cf5b18fa6ef861002d"

def test_get_and_verified_apikey():
  apikey = get_client_apikey_grpc("mfg","mfg")
  token = apikey.apikey
  verifiedtoken = verified_client_apikey_grpc(token)
  assert verifiedtoken.assertion == 'mfg:QUERY:/mfg'
  