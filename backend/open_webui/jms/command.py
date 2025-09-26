import re
import time
import logging
import asyncio
from typing import List, Optional
from datetime import datetime

import socketio

from .wisp.protobuf import service_pb2
from .wisp.exceptions import WispError
from .wisp.protobuf.common_pb2 import Session, CommandACL, RiskLevel
from open_webui.env import SRC_LOG_LEVELS
from .base import BaseWisp
from .schemas import CommandRecord, JMSState, AskResponse, AskResponseType, ResponseMeta, reply

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class CommandHandler(BaseWisp):
    WAIT_TICKET_TIMEOUT = 60 * 3
    WAIT_TICKET_INTERVAL = 2

    def __init__(
            self, session: Session, sio: socketio.AsyncServer, sid: str
    ):
        super().__init__()
        self.sio = sio
        self.sid = sid
        self.session = session
        self.cmd_acl_id = ''
        self.cmd_group_id = ''
        self.command_record: Optional[CommandRecord] = None

    async def record_command(self):
        req = service_pb2.CommandRequest(
            sid=self.session.id,
            org_id=self.session.org_id,
            asset=self.session.asset,
            account=self.session.account,
            user=self.session.user,
            timestamp=int(datetime.timestamp(datetime.now())),
            input=self.command_record.input,
            output=self.command_record.output,
            risk_level=self.command_record.risk_level,
            cmd_acl_id=self.cmd_acl_id,
            cmd_group_id=self.cmd_group_id
        )
        resp = self.stub.UploadCommand(req)
        if not resp.status.ok:
            error_message = f'Failed to upload command: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
