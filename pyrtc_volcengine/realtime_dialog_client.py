import websockets
import gzip
import json

from typing import Dict, Any

from .constants.event import ClientEventEnum
from .logger import PYRTC_LOGGER
from .protocol import JSON, parse_response, generate_header, CLIENT_AUDIO_ONLY_REQUEST, NO_SERIALIZATION, CLIENT_FULL_REQUEST


class RealtimeDialogClient:
    def __init__(self, config: Dict[str, Any], session_id: str):
        self.config = config["ws_connect_config"]
        self.start_session_config = config["start_session_req"]
        self.logid = ""
        self.session_id = session_id
        self.ws = None

    async def _send(self, event: int, payload: str | bytes, headers: bytearray=None, session_id: str=None):
        if headers is None:
            headers = generate_header()

        request = headers
        request.extend(event.to_bytes(4, 'big'))

        if session_id is not None:
            request.extend((len(session_id)).to_bytes(4, 'big'))
            request.extend(str.encode(session_id))

        if isinstance(payload, str):
            payload = str.encode(payload, encoding="utf-8")
        
        payload_compress = gzip.compress(payload)
        request.extend((len(payload_compress)).to_bytes(4, 'big'))
        request.extend(payload_compress)
        await self.ws.send(request)

    async def connect(self) -> None:
        """建立WebSocket连接"""
        PYRTC_LOGGER.debug(f"url: {self.config['base_url']}, headers: {self.config['headers']}")
        self.ws = await websockets.connect(
            self.config['base_url'],
            additional_headers=self.config['headers'],
            ping_interval=None
        )
        self.logid = self.ws.response.headers.get("X-Tt-Logid")
        PYRTC_LOGGER.debug(f"dialog server response logid: {self.logid}")

        # StartConnection request
        await self._send(ClientEventEnum.START_CONNECTION.value, "{}")
        response = await self.ws.recv()
        PYRTC_LOGGER.debug(f"StartConnection response: {parse_response(response)}")

        # StartSession request
        request_params = self.start_session_config
        await self._send(ClientEventEnum.START_SESSION.value, json.dumps(request_params, ensure_ascii=False), session_id=self.session_id)
        response = await self.ws.recv()
        PYRTC_LOGGER.debug(f"StartSession response: {parse_response(response)}")

    async def task_request(self, audio: bytes) -> None:
        task_request = generate_header(message_type=CLIENT_AUDIO_ONLY_REQUEST,
                                     serial_method=NO_SERIALIZATION)
        await self._send(ClientEventEnum.TASK_REQUEST.value, audio, task_request, session_id=self.session_id)

    async def chat_request(self, payload: dict) -> None:
        chat_request = generate_header(message_type=CLIENT_FULL_REQUEST,
                                    serial_method=JSON)
        await self._send(ClientEventEnum.CHAT_TTS_TEXT.value, json.dumps(payload, ensure_ascii=False), chat_request, session_id=self.session_id)

    async def receive_server_response(self) -> Dict[str, Any]:
        try:
            response = await self.ws.recv()
            data = parse_response(response)
            return data
        except Exception as e:
            raise Exception(f"Failed to receive message: {e}")

    async def finish_session(self):
        await self._send(ClientEventEnum.FINISH_SESSION.value, "{}")


    async def finish_connection(self):
        await self._send(ClientEventEnum.FINISH_CONNECTION.value, "{}")
        response = await self.ws.recv()
        PYRTC_LOGGER.debug(f"FinishConnection response: {parse_response(response)}")

    async def close(self) -> None:
        """关闭WebSocket连接"""
        if self.ws:
            PYRTC_LOGGER.debug("Closing WebSocket connection...")
            await self.ws.close()
