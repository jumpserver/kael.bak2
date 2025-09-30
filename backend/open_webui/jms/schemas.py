import uuid
import datetime
from enum import auto, StrEnum
from pydantic import BaseModel
from typing import Optional, Literal

from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from jms.wisp.protobuf.common_pb2 import RiskLevel


class CommandRecord(BaseModel):
    input: Optional[str] = None
    output: Optional[str] = None
    risk_level: str = RiskLevel.Normal
