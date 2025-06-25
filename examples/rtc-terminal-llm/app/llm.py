from typing import List
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()


class HttpClientBase:

    RETURN_JSON = True

    @classmethod
    async def _method(cls, method: str, url: str, headers: dict = None, json_body: dict = None, params=None, timeout=5):

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url,
                                       params=params,
                                       json=json_body,
                                       headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=timeout)
                                       ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f'{url} 调用失败: {text}', raw_code=response.status)
                if cls.RETURN_JSON:
                    return await response.json()
                else:
                    return None

    @classmethod
    async def post(cls, url: str, headers: dict = None, json_body: dict = None, params=None, timeout=5):
        return await cls._method('POST', url=url, headers=headers, json_body=json_body, params=params, timeout=timeout)

class LLMClient(HttpClientBase):

    def __init__(self, api_url=None, api_key=None):
        self.api_url = api_url or os.environ.get("OPENAPI_BASE_URL")
        self.api_key = api_key or os.environ.get("OPENAPI_API_KEY")
    
    async def completions(self, model: str, messages: List[dict]):
        response = await self.post(self.api_url, json_body={"model": model, "messages": messages}, headers={"Authorization": f"Bearer {self.api_key}",
                                                                 "Content-Type": "application/json"}, timeout=120)
        result = response
        return result["choices"][0]["message"]["content"]
    

if __name__ == "__main__":
    import asyncio
    import time
    c = LLMClient()
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
    query = "你好呀"
    start_t = time.time()
    intent = asyncio.run(c.completions(model=os.environ.get("MODEL_NAME"), messages=[
        {"role": "system", "content": INTENT_RECOGNITION_SYSTEM_PROMPT},
        {"role": "user", "content": query},
        ]))
    
    end_t = time.time()
    print(f"意图识别为: {intent}, cost: { round((end_t - start_t), 2) }s")