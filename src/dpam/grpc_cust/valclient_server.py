from concurrent import futures
from threading import Thread
from urllib import response
from tools.account import get_client_info
import grpc
import grpc_cust.valclient_pb2 as valclient_pb2
import grpc_cust.valclient_pb2_grpc as valclient_pb2_grpc
from tools.config_loader import ConfigLoader


__all__ = 'ValClient'

valclient_server = ConfigLoader.config("grpc")["valclient"]["server"]
valclient_port = ConfigLoader.config("grpc")["valclient"]["port"]

SERVER_ADDRESS = "%s:%s" %(valclient_server,valclient_port)

class ValClient(valclient_pb2_grpc.ValclientServicer):

    def ElaborDetail(self, request, context):
      print("ElaborDetail called by client(%s)" %(request.client_id))
      info = get_client_info(request.client_id)
      if(info["CLIENT_ID"]!={}):
          print("client id %s has registered info" %(request.client_id))
          response = valclient_pb2.Response(
            client_id=request.client_id,
            password = str(info["PASSWORD"][0]),
            type = info["TYPE"][0],
            expiry = str(info["EXPIRY"][0]),
            permission = str(info["PERMISSION"][0])
          )
      else:
          print("client id %s has NO registered info" %(request.client_id))
          response = valclient_pb2.Response(
            client_id=request.client_id,
            password = "",
            type = 0,
            expiry = "1900-01-01",
            permission = "None")

      return response


def main():
    server = grpc.server(futures.ThreadPoolExecutor())

    valclient_pb2_grpc.add_ValclientServicer_to_server(ValClient(),server)

    server.add_insecure_port(SERVER_ADDRESS)
    print("---------------Start Python Client Auth Server----------------------------------")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
  main()