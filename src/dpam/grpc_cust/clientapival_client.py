import grpc
import dpam.grpc_cust.clientapival_pb2 as clientapival_pb2
import dpam.grpc_cust.clientapival_pb2_grpc as clientapival_pb2_grpc
from dpam.tools.config_loader import ConfigLoader
from dpam.tools.logger import Logger

__all__ = {
  'simplemethod'
}

clientapival_server = ConfigLoader.config("grpc")["clientapival"]["server"]
clientapival_port = ConfigLoader.config("grpc")["clientapival"]["port"]

SERVER_ADDRESS = "%s:%s" %(clientapival_server,clientapival_port)


def clientinfo(stub,clientid):
  # print("------------------Enquiry Client Info Begin-----------------")
  request = clientapival_pb2.ClientId(clientid=clientid)
  # print("request clientid %s to server(%s)" %(request, SERVER_ADDRESS))
  Logger.log(f"Begin Enquiry Client Info from clientid {clientid}")
  response = stub.clientinfo(request)
  # print("response from server(%s)" %SERVER_ADDRESS)
  # print("response info(%s)" %response)
  Logger.log(f"response {response} from server{SERVER_ADDRESS} End")
  # print("-----------------Call  over ------------------")
  return response


def clientapikey(stub,clientid, password):
  # print("------------------Enquiry Client Info Begin-----------------")
  Logger.log(f"Begin Request APIKey from clientid {clientid}")
  request = clientapival_pb2.ClientCred(clientid=clientid, password=password)
  # print("request client api key %s to server(%s)" %(request, SERVER_ADDRESS))
  response = stub.clientapikey(request)
  # print("response from server(%s)" %SERVER_ADDRESS)
  # print("response info(%s)" %response)
  # print("-----------------Call  over ------------------")
  Logger.log(f"Response {response} from server {SERVER_ADDRESS} End")
  return response


def verifiedapikey(stub,token):
  #print("------------------Verify API Key Begin-----------------")
  request = clientapival_pb2.APIKey(apikey=token)
  # print("request verified client api key %s to server(%s)" %(request, SERVER_ADDRESS))
  Logger.log(f"Begin verified API Key by token {token}")
  response = stub.verifiedapikey(request)
  # print("response from server(%s)" %SERVER_ADDRESS)
  # print("response info(%s)" %response)
  # print("-----------------Call  over ------------------")
  Logger.log(f"Response {response} from server {SERVER_ADDRESS} End")
  return response


def get_clientinfo(clientid):
  with grpc.insecure_channel(SERVER_ADDRESS) as channel:
    stub = clientapival_pb2_grpc.ClientAPIValStub(channel)

    return clientinfo(stub,clientid)

  
def get_clientapikey(clientid, password):
  with grpc.insecure_channel(SERVER_ADDRESS) as channel:
    stub = clientapival_pb2_grpc.ClientAPIValStub(channel)

    return clientapikey(stub,clientid,password)

  
def get_verified_apikey(token):
  with grpc.insecure_channel(SERVER_ADDRESS) as channel:
    stub = clientapival_pb2_grpc.ClientAPIValStub(channel)

    return verifiedapikey(stub,token)

