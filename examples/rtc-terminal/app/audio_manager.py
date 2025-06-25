
from typing import Optional
from pydantic import BaseModel
import pyaudio


input_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 16000,
    "bit_size": pyaudio.paInt16,
    # "device_index": 3
}

output_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 24000,
    "bit_size": pyaudio.paFloat32,
    # "device_index": 2
}


class AudioConfig(BaseModel):
    """音频配置数据类"""
    format: str
    bit_size: int
    channels: int
    sample_rate: int
    chunk: int
    device_index: Optional[int] = None


class AudioDeviceManager:
    """音频设备管理类，处理音频输入输出"""

    def __init__(self, input_config: AudioConfig, output_config: AudioConfig):
        self.input_config = input_config
        self.output_config = output_config
        self.pyaudio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

    def open_input_stream(self) -> pyaudio.Stream:
        """打开音频输入流"""
        # p = pyaudio.PyAudio()
        self.input_stream = self.pyaudio.open(
            format=self.input_config.bit_size,
            channels=self.input_config.channels,
            rate=self.input_config.sample_rate,
            input=True,
            input_device_index=self.input_config.device_index,
            frames_per_buffer=self.input_config.chunk
        )
        return self.input_stream

    def open_output_stream(self) -> pyaudio.Stream:
        """打开音频输出流"""
        self.output_stream = self.pyaudio.open(
            format=self.output_config.bit_size,
            channels=self.output_config.channels,
            rate=self.output_config.sample_rate,
            output=True,
            output_device_index=self.output_config.device_index,
            frames_per_buffer=self.output_config.chunk,
        )
        return self.output_stream
    
    def cleanup(self) -> None:
        """清理音频设备资源"""
        for stream in [self.input_stream, self.output_stream]:
            if stream:
                stream.stop_stream()
                stream.close()
        self.pyaudio.terminate()


p = pyaudio.PyAudio()

# 列出所有可用的音频设备以找到它们的索引
info = p.get_host_api_info_by_index(0)
num_devices = info.get('deviceCount')
print("所有可用音频设备：")
for i in range(num_devices):
    device_info = p.get_device_info_by_host_api_device_index(0, i)
    print(f"ID {i}: {device_info.get('name')} (输入通道: {device_info.get('maxInputChannels')}, 输出通道: {device_info.get('maxOutputChannels')})")
