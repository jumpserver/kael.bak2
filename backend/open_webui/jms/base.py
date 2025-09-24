from jms.wisp import grpc_channel
from jms.wisp.protobuf import service_pb2_grpc


class BaseWisp:

    def __init__(self):
        self.stub = service_pb2_grpc.ServiceStub(grpc_channel)
