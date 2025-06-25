import queue
from dataclasses import dataclass

@dataclass
class DialogContext:
    is_running = True
    is_session_finished = False

    input_audio_queue = queue.Queue()
    asr_queue = queue.Queue()

    output_audio_cache_queue = queue.Queue()
    output_audio_queue = queue.Queue()

    input_chat_queue = queue.Queue()

    output_chat_cache_queue = queue.Queue()
    output_chat_queue = queue.Queue()
