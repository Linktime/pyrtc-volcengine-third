from enum import Enum
import queue
import os
import asyncio
from typing import Dict, Any
import signal
import threading
import time
from dataclasses import dataclass

from pyrtc_volcengine.dialog_session import DialogSession
from pyrtc_volcengine.event_handlers import DEFAULT_HANDLERS, ASREndedHandler, TTSEndedHandler, ChatEndedHandler, TTSHandler
from pyrtc_volcengine.context import DialogContext
from pyrtc_volcengine.entities import ChatTTSTextRequest
from pyrtc_volcengine.logger import PYRTC_LOGGER
from pyrtc_volcengine.extra import vad
from .audio_manager import AudioConfig, AudioDeviceManager, input_audio_config, output_audio_config
from .llm import LLMClient


LLM = LLMClient()


class IntentEnum(Enum):

    CHAT = "chat"
    QUERY = "query"


@dataclass
class LLMDialogContext(DialogContext):
    last_intent = "chat"
    is_cached_empty = False

    asr_event_for_tts_queue = queue.Queue()
    asr_event_for_chat_queue = queue.Queue()
    asr_event_for_ttsing_queue = queue.Queue()


class LLMASREndedHandler(ASREndedHandler):

    INTENT_RECOGNITION_SYSTEM_PROMPT = """
# 任务
根据用户输入判断用户问题类型，任何信息都需要通过查询，仅打招呼、衔接过度的谈话属于闲聊

# 意图分类
- chat: 闲聊
- query: 查询信息，无法通过常识回答，需要进行检索信息，例如查询天气

# 返回格式
- 返回意图英文名称
- 不要输出多余信息
- 不要反问
"""

    async def process(self, payload, context: LLMDialogContext):
        asr_content = await super().process(payload, context)

        context.is_cached_empty = False

        intent_event = asyncio.Event()
        context.asr_event_for_tts_queue.put(intent_event)
        context.asr_event_for_chat_queue.put(intent_event)
        context.asr_event_for_ttsing_queue.put(intent_event)

        start_t = time.time()
        intent = await LLM.completions(model=os.environ.get("MODEL_NAME"), messages=[
            {"role": "system", "content": self.INTENT_RECOGNITION_SYSTEM_PROMPT},
            {"role": "user", "content": asr_content},
            ])
        
        end_t = time.time()
        PYRTC_LOGGER.debug(f"意图识别为: {intent}, cost: { round((end_t - start_t), 2) }s")
        context.last_intent = intent

        intent_event.set()

        if intent == IntentEnum.QUERY.value:
            # 此处可以自由发挥，etc 调用方法、LLM 等
            # 2025/6/24 经测试，此处至少包含首尾两个包才行，不能仅一个包

            chat_request = ChatTTSTextRequest(start=True, content="上海的天气是34摄氏度", end=False)
            context.input_chat_queue.put(chat_request.model_dump())

            chat_request = ChatTTSTextRequest(start=False, content="", end=True)
            context.input_chat_queue.put(chat_request.model_dump())
        
        else:
            return


class LLMTTSHandler(TTSHandler):

    async def process(self, payload, context: LLMDialogContext):
        try:
            asr_event = context.asr_event_for_ttsing_queue.get_nowait()
            
            if asr_event.is_set():
                # 如果 TTS 流结束晚于 意图识别，则判断是否可以提前播放语音
                if context.last_intent == IntentEnum.CHAT.value:
                    while True:
                        try:
                            cached = context.output_audio_cache_queue.get_nowait()
                            context.output_audio_queue.put(cached)
                        except queue.Empty:
                            break

                    await super().process(payload, context)
            else:

                # 意图识别结束前先放在缓存中
                context.output_audio_cache_queue.put(payload)

        except queue.Empty:
            # 没有 asr 事件时，判断缓存还未接收完则舍弃
            if context.last_intent == IntentEnum.QUERY.value and not context.is_cached_empty:
                return
            else:
                await super().process(payload, context)


class LLMTTSEndedHandler(TTSEndedHandler):

    async def process(self, payload, context: LLMDialogContext):
        try:
            asr_event = context.asr_event_for_tts_queue.get_nowait()
            await asr_event.wait()

            # 有 ASRResponse 事件时，会伴随返回一个闲聊语音和文本，因此需要进行一次意图识别，决定是否丢弃闲聊缓存
            if context.last_intent == IntentEnum.CHAT.value:
                await super().process(payload, context)
            else:
                # 丢弃闲聊缓存
                context.output_audio_cache_queue.empty()
                context.is_cached_empty = True

        except queue.Empty:
            # 没有 asr 事件时，应当是 ChatTTSText 请求返回的 ChatResponse，直接播放
            await super().process(payload, context)


class LLMChatEndedHandler(ChatEndedHandler):

    async def process(self, payload, context: LLMDialogContext):
        try:
            asr_event = context.asr_event_for_chat_queue.get_nowait()
            await asr_event.wait()

            # 有 ASRResponse 事件时，会伴随返回一个闲聊语音和文本，因此需要进行一次意图识别，决定是否丢弃闲聊缓存
            if context.last_intent == IntentEnum.CHAT.value:
                await super().process(payload, context)
            else:
                # 丢弃闲聊缓存
                context.output_chat_cache_queue.empty()

        except queue.Empty:
            await super().process(payload, context)

# 浅拷贝并更换handler
LLM_DIALOG_HANDLERS = dict(DEFAULT_HANDLERS)
LLM_DIALOG_HANDLERS.update({
    LLMASREndedHandler.EVENT_TYPE.value: LLMASREndedHandler(),
    LLMTTSHandler.EVENT_TYPE.value: LLMTTSHandler(),
    LLMTTSEndedHandler.EVENT_TYPE.value: LLMTTSEndedHandler(),
    LLMChatEndedHandler.EVENT_TYPE.value: LLMChatEndedHandler()
})


class LLMDialogSession(DialogSession):
    """对话会话管理类"""

    def __init__(self, ws_config: Dict[str, Any], handlers=LLM_DIALOG_HANDLERS, context: LLMDialogContext=None):
        context = context or LLMDialogContext()

        super().__init__(ws_config, handlers=handlers, context=context)
        self.audio_device = AudioDeviceManager(
            AudioConfig(**input_audio_config),
            AudioConfig(**output_audio_config)
        )

        signal.signal(signal.SIGINT, self._keyboard_signal)
        
        self.output_stream = self.audio_device.open_output_stream()
        
        # 启动播放线程
        self.is_recording = True
        self.is_playing = True

        self.player_thread = threading.Thread(target=self._audio_player_thread)
        self.player_thread.daemon = True
        self.player_thread.start()

    def _audio_player_thread(self):
        """音频播放线程"""
        while self.is_playing:
            try:
                # 从队列获取音频数据
                audio_data = self.context.output_audio_queue.get_nowait()

                if audio_data is not None:
                    self.output_stream.write(audio_data)
                
            except queue.Empty:
                # 队列为空时等待一小段时间
                time.sleep(0.1)

            except Exception as e:
                PYRTC_LOGGER.error(f"音频播放错误: {e}")
                time.sleep(0.1)

    def _keyboard_signal(self, sig, frame):
        print("receive keyboard Ctrl+C")
        self.is_recording = False
        self.is_playing = False
        self.context.is_running = False

    async def process_microphone_input(self) -> None:
        """处理麦克风输入"""
        stream = self.audio_device.open_input_stream()
        PYRTC_LOGGER.info("已打开麦克风，请讲话...")

        while True:
            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                if self.is_recording:
                    audio_data = stream.read(input_audio_config["chunk"], exception_on_overflow=False)

                    # 人声检测
                    if vad.is_speech(audio_data, input_audio_config["sample_rate"]):
                        self.context.input_audio_queue.put(audio_data)

                await asyncio.sleep(0.01)  # 避免CPU过度使用
            except Exception as e:
                PYRTC_LOGGER.error(f"读取麦克风数据出错: {e}", exc_info=True)
                await asyncio.sleep(0.1)  # 给系统一些恢复时间

    async def start(self) -> None:
        """启动对话会话"""
        try:
            asyncio.create_task(self.process_microphone_input())
            await super().start()
        finally:
            self.audio_device.cleanup()