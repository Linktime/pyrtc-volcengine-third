from abc import ABC, abstractmethod
from typing import Dict, Any, Type, get_type_hints, get_args, get_origin
import typing
import sys
import inspect
import queue
from pydantic import BaseModel
from .constants.event import ServerEventEnum
from .context import DialogContext
from .entities import T, Generic, ASRResponsePayload, ChatResponsePayload, SessionFailedPayload


def get_all_namespaces():
    """收集所有已导入模块的命名空间"""
    all_ns = {}
    
    # 首先添加 typing 模块的所有内容
    all_ns.update(typing.__dict__)
    
    # 添加当前全局命名空间
    all_ns.update(globals())
    
    # 遍历所有已导入模块
    for name, module in sys.modules.items():
        if module is not None:
            try:
                all_ns.update(module.__dict__)
            except AttributeError:
                # 有些模块可能没有 __dict__
                pass
    
    return all_ns



class AbstractHandler(ABC, Generic[T]):

    EVENT_TYPE: ServerEventEnum

    @abstractmethod
    async def process(payload: T, context: DialogContext):
        ...

    def build_generic_instance(self, init_params: dict) -> Any:
        """
        根据params自动实例化T对应类的实例
        
        Args:
            params: 参数字典
            
        Returns:
            T类型的实例
        """
        # 获取T的实际类型
        generic_type = self._get_generic_type(0)
        
        if generic_type is None:
            raise TypeError("无法确定泛型的具体类型")
        
        # 检查是否为基本类型
        if generic_type in (int, float, str, bool):
            # 对于基本类型，尝试直接转换
            if len(init_params) == 1 and next(iter(init_params.keys())) == "value":
                return generic_type(init_params["value"])
            return generic_type(next(iter(init_params.values())))
        elif generic_type in (bytes, ):
            return generic_type(init_params)
        
        # 检查是否为可实例化的类
        elif inspect.isclass(generic_type):
            # 获取初始化方法所需的参数
            
            validate_init_params = {}
            
            if issubclass(generic_type, BaseModel):
                for param_name, param in generic_type.model_fields.items():
                    if param_name != 'self' and param_name in init_params:
                        validate_init_params[param_name] = init_params[param_name]
            else:
                sig = inspect.signature(generic_type.__init__)
                # 过滤掉params中不在__init__参数列表中的键
                for param_name, param in sig.parameters.items():
                    if param_name != 'self' and param_name in init_params:
                        validate_init_params[param_name] = init_params[param_name]
            
            # 实例化并返回
            return generic_type(**validate_init_params)
        else:
            # 如果无法处理，则抛出异常
            # raise TypeError(f"无法为类型 {generic_type} 构建实例")
            return init_params
    
    def _get_generic_type(self, t_index: int) -> Type:
        """
        获取InputT的实际类型
        
        Returns:
            InputT的具体类型
        """
        # 方法1：通过子类型注解获取
        globalns = get_all_namespaces()

        hints = get_type_hints(self.__class__, globalns=globalns)
        if 'process' in hints:
            process_sig = hints['process']
            if get_origin(process_sig) is not None:
                # 获取process方法的输入参数类型
                args = get_args(process_sig)
                if args and len(args) > 0:
                    return args[t_index]
        
        # 方法2：通过泛型参数获取
        class_bases = self.__class__.__orig_bases__
        for base in class_bases:
            type_args = get_args(base)
            if type_args and len(type_args) > 0:
                return type_args[t_index]
        
        return None


class SessionFinishedHandler(AbstractHandler[Dict]):

    EVENT_TYPE = ServerEventEnum.SESSION_FINISHED

    async def process(self, payload, context):
        context.is_session_finished = True


class SessionFailedHandler(AbstractHandler[SessionFailedPayload]):

    EVENT_TYPE = ServerEventEnum.SESSION_FAILED

    async def process(self, payload, context):
        context.is_session_finished = True


class ASRInfoHandler(AbstractHandler[Dict]):

    EVENT_TYPE = ServerEventEnum.ASR_INFO

    async def process(self, payload, context):
        context.input_audio_queue.empty()
        context.input_chat_queue.empty()


class ASRResponseHandler(AbstractHandler[ASRResponsePayload]):

    EVENT_TYPE = ServerEventEnum.ASR_RESPONSE

    async def process(self, payload, context):
        results = payload.results
        if results and results[0].is_interim is False:
            context.asr_queue.put(results[0].text)


class ASREndedHandler(AbstractHandler[Dict]):
    EVENT_TYPE = ServerEventEnum.ASR_ENDED

    async def process(self, payload, context):
        return context.asr_queue.get()


class TTSHandler(AbstractHandler[bytes]):

    EVENT_TYPE = ServerEventEnum.TTS_RESPONSE

    async def process(self, payload, context: DialogContext):
        context.output_audio_queue.put(payload)
    

class TTSEndedHandler(AbstractHandler[Dict]):

    EVENT_TYPE = ServerEventEnum.TTS_ENDED

    async def process(self, payload, context: DialogContext):
        while True:
            try:
                cached = context.output_audio_cache_queue.get_nowait()
                context.output_audio_queue.put(cached)
            except queue.Empty:
                break
    

class ChatResponseHandler(AbstractHandler[ChatResponsePayload]):

    EVENT_TYPE = ServerEventEnum.CHAT_RESPONSE

    async def process(self, payload, context: DialogContext):
        content = payload.content
        context.output_chat_cache_queue.put(content)


class ChatEndedHandler(AbstractHandler[Dict]):

    EVENT_TYPE = ServerEventEnum.CHAT_ENDED

    async def process(self, payload, context):
        content = context.output_chat_cache_queue.get()
        context.output_chat_queue.put(content)
    

DEFAULT_HANDLERS = {
    SessionFinishedHandler.EVENT_TYPE.value: SessionFinishedHandler(),
    SessionFailedHandler.EVENT_TYPE.value: SessionFailedHandler(),
    ASRInfoHandler.EVENT_TYPE.value: ASRInfoHandler(),
    ASRResponseHandler.EVENT_TYPE.value: ASRResponseHandler(),
    ASREndedHandler.EVENT_TYPE.value: ASREndedHandler(),
    TTSHandler.EVENT_TYPE.value: TTSHandler(),
    TTSEndedHandler.EVENT_TYPE.value: TTSEndedHandler(),
    ChatResponseHandler.EVENT_TYPE.value: ChatResponseHandler(),
    ChatEndedHandler.EVENT_TYPE.value: ChatEndedHandler()
}
