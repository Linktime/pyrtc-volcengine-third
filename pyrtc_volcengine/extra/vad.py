import webrtcvad
import numpy as np
import noisereduce as nr


# --- 音频和 VAD 参数 (这些需要与你的 PyAudio 录音参数一致) ---
VAD_AGGRESSIVENESS = 3          # VAD 侵略性模式 (0-3，3 最激进)

# webrtcvad 期望的帧持续时间 (毫秒)，必须是 10, 20 或 30
VAD_FRAME_DURATION_MS = 10

# 判断为语音的最小帧比例。例如，0.5 表示至少一半的 VAD 帧是语音。
MIN_SPEECH_FRAME_RATIO = 0.3

# 获取 np.int16 类型的信息
int16_info = np.iinfo(np.int16)

# 最大绝对值是其最小值（负数）的绝对值，或者是最大正值 + 1
# 对于对称范围，通常是 abs(min_value)
MAX_INT16_ABS_VALUE_FROM_NUMPY = float(abs(int16_info.min))


def reduce_noise(audio_data: bytes, sample_rate: int):
    audio_array = np.frombuffer(audio_data, dtype=np.int16)

    # --- 降噪 ---
    # noisereduce 期望浮点数格式，通常范围在 -1.0 到 1.0 之间
    # 需要将 int16 转换为 float 并归一化
    audio_float = audio_array.astype(np.float32) / MAX_INT16_ABS_VALUE_FROM_NUMPY
    reduced_noise_audio_float = nr.reduce_noise(y=audio_float, sr=sample_rate)

    # 将降噪后的音频转换回 int16 for VAD (如果 VAD 接受 int16)
    # WebRTC VAD 通常直接接受原始的 int16 bytes
    reduced_noise_audio_int16 = (reduced_noise_audio_float * MAX_INT16_ABS_VALUE_FROM_NUMPY).astype(np.int16)
    reduced_noise_data = reduced_noise_audio_int16.tobytes()
    return reduced_noise_data


def contains_speech(raw_data: bytes, 
                    sample_rate: int, 
                    # frames_per_buffer: int,  # 不再直接使用 PyAudio 的 frames_per_buffer 来切分 VAD 帧
                    # channels: int,           # VAD 内部处理为单声道，此处主要用于计算 VAD 帧字节数
                    vad_frame_duration_ms: int = VAD_FRAME_DURATION_MS,
                    vad_aggressiveness: int = VAD_AGGRESSIVENESS,
                    min_speech_ratio: float = MIN_SPEECH_FRAME_RATIO,
                    sample_width_bytes: int = 2 # 获取每个样本的字节数 (对于 paInt16 是 2 字节)
                   ) -> bool:
    """
    判断给定的 raw_data (bytes) 中是否包含人声。
    raw_data 假定是单声道 16-bit PCM 数据。

    Args:
        raw_data (bytes): 从 PyAudio 流中读取的原始音频数据 (例如一个 chunk)。
        sample_rate (int): 音频的采样率。
        vad_frame_duration_ms (int): webrtcvad 期望的每帧持续时间 (10, 20, 或 30 ms)。
        vad_aggressiveness (int): VAD 的侵略性模式 (0-3)。
        min_speech_ratio (float): 判断为语音的最小语音帧比例。

    Returns:
        bool: 如果包含人声则返回 True，否则返回 False。
    """

    vad = webrtcvad.Vad(vad_aggressiveness)
    
    # 计算 webrtcvad 期望的单声道每帧字节数
    # webrtcvad 内部会将多声道数据转换为单声道进行处理，但输入帧的尺寸必须正确对应
    # 假设输入给 VAD 的数据已经是单声道，或者我们将数据视为单声道来切片
    bytes_per_vad_frame = int(sample_rate * vad_frame_duration_ms / 1000) * sample_width_bytes * 1 # * 1 for mono

    total_vad_frames = 0
    speech_vad_frames = 0

    # 将 raw_data 分割成 webrtcvad 所需的固定大小的帧
    for i in range(0, len(raw_data), bytes_per_vad_frame):
        frame_bytes = raw_data[i : i + bytes_per_vad_frame]
        
        # 确保帧是完整且有效的
        if len(frame_bytes) != bytes_per_vad_frame:
            # 跳过不完整的最后一帧，webrtcvad 会报错
            continue 

        total_vad_frames += 1
        try:
            # 传递当前小帧和正确的采样率给 VAD
            is_speech = vad.is_speech(frame_bytes, sample_rate)
            if is_speech:
                speech_vad_frames += 1
        except webrtcvad.Error as e:
            print(f"webrtcvad Error: {e} - Frame length: {len(frame_bytes)} bytes, Expected: {bytes_per_vad_frame} bytes. Check sample_rate and vad_frame_duration_ms.")
            return False # 遇到 VAD 错误，直接返回 False 或抛出异常

    # 如果 raw_data 太短，没有生成任何 VAD 帧
    if total_vad_frames == 0:
        return False

    # 计算语音帧的比例
    speech_ratio = speech_vad_frames / total_vad_frames

    # 判断是否达到包含人声的阈值
    return speech_ratio >= min_speech_ratio



def is_speech(raw_data: bytes, sample_rate: int):
    reduced_noise_data = reduce_noise(raw_data, sample_rate)
    return contains_speech(reduced_noise_data, sample_rate)
