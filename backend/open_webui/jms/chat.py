import json
import logging

from jms.wisp.exceptions import WispError
from open_webui.env import SRC_LOG_LEVELS

from .base import BaseWisp
from .wisp.protobuf.service_pb2 import HTTPRequest

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])

CHAT_URL = "/api/v1/terminal/chats/"


class ChatHandler(BaseWisp):

    def list(self, query=None) -> list:
        if query is None:
            query = {}

        query = {str(k): ('' if v is None else str(v)) for k, v in query.items()}
        req = HTTPRequest(
            method="GET",
            path=CHAT_URL,
            query=query
        )

        resp = self.stub.CallAPI(req)
        if not resp.status.ok:
            error_message = f'Failed to list chats: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return json.loads(resp.body.decode())

    def retrieve(self, chat_id: str) -> dict:
        req = HTTPRequest(
            method="GET",
            path=f"{CHAT_URL}{chat_id}/",
        )
        resp = self.stub.CallAPI(req)
        if not resp.status.ok:
            error_message = f'Failed to retrieve chat {chat_id}: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return json.loads(resp.body.decode())

    def create(self, data: dict) -> dict:
        json_bytes = json.dumps(data).encode()
        req = HTTPRequest(
            method="POST",
            path=CHAT_URL,
            body=json_bytes,
        )
        resp = self.stub.CallAPI(req)
        if not resp.status.ok:
            error_message = f'Failed to list chats: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return json.loads(resp.body.decode())

    def update(self, chat_id: str, data: dict) -> dict:
        json_bytes = json.dumps(data).encode()
        req = HTTPRequest(
            method="PATCH",
            path=f"{CHAT_URL}{chat_id}/",
            body=json_bytes,
        )
        resp = self.stub.CallAPI(req)
        if not resp.status.ok:
            error_message = f'Failed to update chat {chat_id}: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return json.loads(resp.body.decode())

    def destroy(self, chat_id: str, data: dict = None) -> None:
        if data is None:
            req = HTTPRequest(
                method="DELETE",
                path=f"{CHAT_URL}{chat_id}/",
            )
        else:
            json_bytes = json.dumps(data).encode()
            req = HTTPRequest(
                method="DELETE",
                path=CHAT_URL,
                body=json_bytes,
            )
        resp = self.stub.CallAPI(req)
        if not resp.status.ok:
            error_message = f'Failed to delete chat {chat_id}: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)


chat_manager = ChatHandler()
