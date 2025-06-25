from .base_enum import BaseEnum


class ServerEventEnum(BaseEnum):
    """
    https://www.volcengine.com/docs/6561/1594356#%E6%9C%8D%E5%8A%A1%E7%AB%AF%E4%BA%8B%E4%BB%B6
    """
    CONNECTION_STARTED = (50, "ConnectionStarted", "建立连接成功")
    CONNECTION_FAILED = (51, "ConnectionFailed", "建立连接失败")
    CONNECTION_FINISHED = 52, "ConnectionFinished", "连接结束"
    SESSION_STARTED = 150, "SessionStarted", "会话启动"
    SESSION_FINISHED = 152, "SessionFinished", "会话结束"
    SESSION_FAILED = 153, "SessionFailed", "会话失败"
    TTS_SENTENCE_START = 350, "TTSSentenceStart", "合成音频的起始事件"
    TTS_SENTENCE_END = 351, "TTSSentenceEnd", "合成音频的分句结束事件"
    TTS_RESPONSE = 352, "TTSResponse", "返回模型生成的音频数据"
    TTS_ENDED = 359, "TTSEnded", "模型一轮音频合成结束事件"
    ASR_INFO = 450, "ASRInfo", "模型识别出音频流中的首字返回的事件，用于打断客户端的播报"
    ASR_RESPONSE = 451, "ASRResponse", "模型识别出用户说话的文本内容"
    ASR_ENDED = 459, "ASREnded", "模型认为用户说话结束的事件"
    CHAT_RESPONSE = 550, "ChatResponse", "模型回复的文本内容"
    CHAT_ENDED = 559, "ChatEnded", "模型回复文本结束事件"


class ClientEventEnum(BaseEnum):
    """
    https://www.volcengine.com/docs/6561/1594356#%E6%9C%8D%E5%8A%A1%E7%AB%AF%E4%BA%8B%E4%BB%B6
    """
    START_CONNECTION = (1, "StartConnection", "Websocket 阶段申明创建连接")
    FINISH_CONNECTION = (2, "FinishConnection", "断开websocket连接，后面需要重新发起websocket连接")
    START_SESSION = 100, "StartSession", "Websocket 阶段申明创建会话"
    FINISH_SESSION = 102, "FinishSession", "客户端声明结束会话，后面可以复用websocket连接"
    TASK_REQUEST = 200, "TaskRequest", "客户端上传音频"
    SAY_HELLO = 300, "SayHello", "客户端提交打招呼文本"
    CHAT_TTS_TEXT = 500, "ChatTTSText", "用户query之后，模型会生成闲聊结果。如果客户判断用户query不需要闲聊结果，可以指定文本合成音频"
