import logging
from typing import Optional
from datetime import datetime

from .wisp.protobuf import service_pb2
from .wisp.exceptions import WispError
from .wisp.protobuf.common_pb2 import Session
from open_webui.env import SRC_LOG_LEVELS
from .base import BaseWisp
from .schemas import CommandRecord

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["WISP"])


class CommandHandler(BaseWisp):

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
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
            cmd_acl_id='',
            cmd_group_id=''
        )
        resp = self.stub.UploadCommand(req)
        if not resp.status.ok:
            error_message = f'Failed to upload command: {resp.status.err}'
            logger.error(error_message)
            raise WispError(error_message)
