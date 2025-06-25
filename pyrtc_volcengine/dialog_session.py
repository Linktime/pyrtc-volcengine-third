import uuid
from typing import Dict, Any, TypeVar, Generic
import queue
import asyncio

from .context import DialogContext
from .realtime_dialog_client import RealtimeDialogClient
from .event_handlers import AbstractHandler, DEFAULT_HANDLERS
from .constants.event import ServerEventEnum
from .logger import PYRTC_LOGGER


ContextT = TypeVar('_ContextT', bound=DialogContext)


class DialogSession(Generic[ContextT]):

    def __init__(self, config: Dict[str, Any], handlers: Dict[str, AbstractHandler]=DEFAULT_HANDLERS, context: DialogContext=None):
        self.handlers = handlers
        self.session_id = str(uuid.uuid4())
        self.client = RealtimeDialogClient(config=config, session_id=self.session_id)
        self.context = context or DialogContext()

    async def handle_server_response(self, response: Dict[str, Any]) -> None:
        if response == {}:
            return
        
        """处理服务器响应"""
        if response['message_type'] != "SERVER_ERROR":
            handler = self.handlers.get(response['event'])

            if handler:
                await handler.process(handler.build_generic_instance(response['payload_msg']), self.context)
            if response['event'] != ServerEventEnum.TTS_RESPONSE.value:
                PYRTC_LOGGER.info(response)

        else:
            PYRTC_LOGGER.error(f"语音模型服务器错误: {response}")
            raise Exception("语音模型服务器错误")
        
    async def send_loop(self):
        while self.context.is_running:
            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                audio_data = self.context.input_audio_queue.get_nowait()
                PYRTC_LOGGER.debug("发送语音片段")
                await self.client.task_request(audio_data)
                await asyncio.sleep(0.01)  # 避免CPU过度使用
            except queue.Empty:
                await asyncio.sleep(0.1)  # 无语音输入，等候
                continue

            except Exception as e:            
                await asyncio.sleep(0.1)  # 给系统一些恢复时间
                continue

            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                chat_data = self.context.input_chat_queue.get_nowait()
                PYRTC_LOGGER.debug("发送文本合成片段")
                await self.client.chat_request(chat_data)
                await asyncio.sleep(0.01)  # 避免CPU过度使用
            except queue.Empty:
                await asyncio.sleep(0.1)  # 无语音输入，等候
                continue

            except Exception as e:            
                await asyncio.sleep(0.1)  # 给系统一些恢复时间
                continue
        
    
    async def receive_loop(self):
        try:
            while self.context.is_running:
                response = await self.client.receive_server_response()
                await self.handle_server_response(response)
                if  self.context.is_session_finished is True:
                    break

        except asyncio.CancelledError:
            PYRTC_LOGGER.warning("实时语音websocket接收任务已取消")
        except Exception as e:
            PYRTC_LOGGER.debug(f"实时语音websocket接收消息错误: 返回值为: {response}")
            PYRTC_LOGGER.error(f"实时语音websocket接收消息错误: {e}", exc_info=True)

    async def start(self) -> None:
        """启动对话会话"""
        try:
            await self.client.connect()
            asyncio.create_task(self.send_loop())
            asyncio.create_task(self.receive_loop())

            while self.context.is_running:
                await asyncio.sleep(0.1)

            await self.client.finish_session()
            while not self.context.is_session_finished:
                await asyncio.sleep(0.1)
            await self.client.finish_connection()
            await asyncio.sleep(0.1)
            await self.client.close()
            PYRTC_LOGGER.info(f"实时语音会话请求 logid: {self.client.logid}")
        except Exception as e:
            PYRTC_LOGGER.error(f"实时语音会话错误: {e}")