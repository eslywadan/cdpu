import grpc
import dpam.grpc_cust.valclient_pb2 as valclient_pb2
import dpam.grpc_cust.valclient_pb2_grpc as valclient_pb2_grpc
from dpam.tools.config_loader import ConfigLoader

__all__ = {
  'simplemethod'
}

valclient_server = ConfigLoader.config("grpc")["valclient"]["server"]
valclient_port = ConfigLoader.config("grpc")["valclient"]["port"]

SERVER_ADDRESS = "%s:%s" %(valclient_server,valclient_port)


def simplemethod(stub):
  print("------------------Call Simple Method Begin-----------------")
  request = valclient_pb2.Request(client_id="mfg")
  response = stub.ElaborDetail(request)
  print("response from server(%s)" %SERVER_ADDRESS)
  print("response info(%s)" %response)
  print("-----------------Call simplemethod over ------------------")


def main():
  with grpc.insecure_channel(SERVER_ADDRESS) as channel:
    stub = valclient_pb2_grpc.ValclientStub(channel)

    simplemethod(stub)


if __name__ == '__main__':
  main()