import queue
import asyncio
from typing import Dict, Any
import signal
import threading
import time

from pyrtc_volcengine.dialog_session import DialogSession
from pyrtc_volcengine.event_handlers import DEFAULT_HANDLERS
from pyrtc_volcengine.extra import vad
from .audio_manager import AudioConfig, AudioDeviceManager, input_audio_config, output_audio_config


class TerminalDialogSession(DialogSession):
    """对话会话管理类"""

    def __init__(self, ws_config: Dict[str, Any], handlers=DEFAULT_HANDLERS, context=None):
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
                self.output_stream.write(audio_data)
                
            except queue.Empty:
                # 队列为空时等待一小段时间
                time.sleep(0.1)

            except Exception as e:
                print(f"音频播放错误: {e}")
                time.sleep(0.1)

    def _keyboard_signal(self, sig, frame):
        print("receive keyboard Ctrl+C")
        self.is_recording = False
        self.is_playing = False
        self.context.is_running = False

    async def process_microphone_input(self) -> None:
        """处理麦克风输入"""
        stream = self.audio_device.open_input_stream()
        print("已打开麦克风，请讲话...")

        while True:
            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                if self.is_recording:
                    audio_data = stream.read(input_audio_config["chunk"], exception_on_overflow=False)
                    if vad.is_speech(audio_data, input_audio_config["sample_rate"]):
                        self.context.input_audio_queue.put(audio_data)
                await asyncio.sleep(0.01)  # 避免CPU过度使用
            except Exception as e:
                print(f"读取麦克风数据出错: {e}")
                await asyncio.sleep(0.1)  # 给系统一些恢复时间

    async def start(self) -> None:
        """启动对话会话"""
        try:
            asyncio.create_task(self.process_microphone_input())
            await super().start()
        finally:
            self.audio_device.cleanup()