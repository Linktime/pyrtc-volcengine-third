# pyrtc-volcengine-third
字节跳动火山引擎实时语音大模型Python SDK，非官方


## 安装

1. 仅SDK
```
pip install pyrtc-volcengine-third
```

2. 包含简单的人声识别
```
pip install "pyrtc-volcengine-third[vad]"
```

## 用法

```
import asyncio
from pyrtc_volcengine import DialogSession

ws_connect_config = {
    # 具体配置参考官方文档
}

async def main() -> None:
    session = DialogSession(config.ws_connect_config)
    await session.start()

if __name__ == "__main__":
    asyncio.run(main())
 
```

### Example_1: rtc-terminal

实现的功能与官方示例 realtime_dialog 基本相同，增加了降噪和人声判断

在官方示例中，如果使用笔记本自带的输入输出设备进行外放时，录音会录制播放的声音造成无限循环对话，故实际生产使用时，有两种思路解决

#### 思路1: 硬件分离
播放声音时中断录制，除非手动停止播放和开启录音；同理，开启录制时自动停止播放

#### 思路2: 回声消除
录制时去除自身设备播放的重复音源数据，例如使用 Python-Acoustic-Echo-Cancellation-Library[https://github.com/Keyvanhardani/Python-Acoustic-Echo-Cancellation-Library]


### Example_2: rtc-terminal-llm

在 rtc-terminal 的基础上，增加了 *意图识别* 部分的逻辑，支持在意图识别中转联网搜索或使用工具获取信息，需要自己继承不同事件Handler，并定制逻辑


#### 1. ASREndedHandler

对应 ASRResponse 事件，返回对输入语音识别的文本结果，在这一步进行意图识别，并标记缓存闲聊结果

#### 2. TTSHandler(可选)

接收语音数据时，意图识别结束如果是闲聊可以直接播放，否则丢弃。主要是为了当意图识别早于 TTSResponse 事件结束，并且是闲聊结果，可以提前播放语音。
但由于内置语音通常比较短和快，更简单的做法则不做复杂判断，只加到缓存队列，在 TTSEndedHandler 中再判断是否播放或丢弃。

#### 3. TTSEndedHandler

对应 TTSEnded 事件，判断丢弃缓存还是播放

#### 4. ChatEndedHandler

闲聊的文本或 ChatTTSText 的文本，同样需要根据意图识别的结果判断是否要丢弃


在生产应用中，还需要加上更复杂的聊天记录以便于供 意图识别 和其他 Agent 使用
