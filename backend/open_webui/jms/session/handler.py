import asyncio
import logging
from datetime import datetime
import socketio

from jms.wisp.protobuf import service_pb2
from jms.wisp.exceptions import WispError
from jms.wisp.protobuf.common_pb2 import Session, User
from open_webui.env import SRC_LOG_LEVELS
from ..replay import ReplayHandler
from ..command import CommandHandler
from ..base import BaseWisp

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class JMSSession(BaseWisp):
    def __init__(self, session: Session, sio: socketio.AsyncServer, sid: str):
        super().__init__()
        self.sio = sio
        self.sid = sid
        self.session = session

        self.command_handler = None
        self.replay_handler = None

    def active_session(self) -> None:
        self.replay_handler = ReplayHandler(self.session)
        self.command_handler = CommandHandler(
            self.session, self.sio, self.sid
        )

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

    def __init__(self, sio: socketio.AsyncServer, sid: str, ip: str, user: User):
        super().__init__()
        self.sio = sio
        self.sid = sid
        self.remote_address = ip
        self.user = user

    def create_new_session(self, ai_model: str, account_data: dict) -> JMSSession:
        session = self.create_session(ai_model, account_data)
        jms_session = JMSSession(session, self.sio, self.sid)
        return jms_session

    def create_session(self, ai_model: str, account_data: dict) -> Session:
        req_session = Session(
            user_id=self.user.id,
            user=f'{self.user.name}({self.user.username})',
            account_id=account_data['id'],
            account=f'{account_data["name"]}({account_data["username"]})',
            org_id=account_data['org_id'],
            asset_id=account_data['asset']['id'],
            asset=account_data['asset']['name'],
            login_from=Session.LoginFrom.WT,
            protocol=ai_model,
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
