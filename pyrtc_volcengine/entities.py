from typing import List, Generic, TypeVar, Dict, Literal, Optional
from pydantic import BaseModel

T = TypeVar('_T')

class Response(BaseModel, Generic[T]):
    message_type: str
    event: int
    session_id: str | bytes
    payload_msg: T
    payload_size: int


class ConnectionFailedPayload(BaseModel):
    error: str


class SessionStartedPayload(BaseModel):
    dialog_id: str


class SessionFailedPayload(BaseModel):
    error: str


class TTSSentenceStartPayload(BaseModel):
    enable_v3_loudness_balance: bool
    model_type: str
    tts_task_id: str
    tts_type: Literal['audit_content_risky', 'chat_tts_text', 'default']
    v3_loundness_params: str


class ASRExtra(BaseModel):
    interrupt_score: float
    is_pvad: bool
    model_version: str
    origin_text: str
    req_payload: Dict
    source: str
    vad_backtrack_silence_time_ms: Optional[float] = None


class ASRResult(BaseModel):
    alternatives: List
    text: str
    start_time: float
    end_time: float
    index: int
    is_interim: bool
    is_vad_timeout: bool


class ASRResponsePayload(BaseModel):
    extra: ASRExtra
    results: List[ASRResult]


class ChatResponsePayload(BaseModel):
    content: str


class ChatTTSTextRequest(BaseModel):
    start: bool
    content: str
    end: bool
