import asyncio
import logging
from datetime import datetime

from jms.wisp.protobuf import service_pb2
from jms.wisp.exceptions import WispError
from jms.wisp.protobuf.common_pb2 import Session, User
from open_webui.env import SRC_LOG_LEVELS
from ..account import AccountChatHandler
from ..base import BaseWisp

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class JMSSession(BaseWisp):
    def __init__(self, session: Session, sid: str):
        super().__init__()
        self.sid = sid
        self.session = session

        self.command_handler = None
        self.replay_handler = None

    async def close_session(self) -> None:
        req = service_pb2.SessionFinishRequest(
            id=self.session.id,
            date_end=int(datetime.now().timestamp())
        )
        resp = self.stub.FinishSession(req)

        if not resp.status.ok:
            error_message = f'Failed to close session: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)

    async def close(self) -> None:
        from jms import session_manager
        await asyncio.sleep(1)
        await self.replay_handler.upload()
        await self.close_session()
        session_manager.unregister_jms_session(self)


class SessionHandler(BaseWisp):

    def __init__(self, sid: str, ip: str, user: User):
        super().__init__()
        self.sid = sid
        self.remote_address = ip
        self.user = user

    def create_new_session(self, chat_model: str) -> JMSSession:
        account_handler = AccountChatHandler()
        account_data = account_handler.get_account()

        session = self.create_session(chat_model, account_data)
        jms_session = JMSSession(session, self.sid)
        return jms_session

    def create_session(self, chat_model: str, account_data: dict) -> Session:
        req_session = Session(
            user_id=self.user.id,
            user=f'{self.user.name}({self.user.username})',
            account_id=account_data['id'],
            account=f'{account_data["name"]}({account_data["username"]})',
            org_id=account_data['org_id'],
            asset_id=account_data['asset']['id'],
            asset=account_data['asset']['name'],
            login_from=Session.LoginFrom.WT,
            protocol=chat_model,
            date_start=int(datetime.now().timestamp()),
            remote_addr=self.remote_address,
        )
        req = service_pb2.SessionCreateRequest(data=req_session)
        resp = self.stub.CreateSession(req)
        if not resp.status.ok:
            error_message = f'Failed to create session: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
        return resp.data
