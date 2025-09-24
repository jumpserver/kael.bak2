import logging

from fastapi import Request
from wisp.protobuf import service_pb2
from wisp.exceptions import WispError
from wisp.protobuf.common_pb2 import User
from open_webui.env import SRC_LOG_LEVELS

from .base import BaseWisp

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class CheckUserHandler(BaseWisp):

    def check_user_by_cookies(self, request: Request) -> User:
        req = service_pb2.CookiesRequest()
        for name, value in request.cookies.items():
            c = req.cookies.add()
            c.name = name
            c.value = value

        user_resp = self.stub.CheckUserByCookies(req)
        if not user_resp.status.ok:
            error_message = f'Failed to check user: {user_resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return user_resp.data
