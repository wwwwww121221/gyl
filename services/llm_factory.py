from abc import ABC, abstractmethod
from typing import List, Optional, Any
import httpx
from core.config import settings
from schemas import ChatMessage, LLMResponse

class LLMProvider(ABC):
    @abstractmethod
    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [msg.dict() for msg in messages],
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return LLMResponse(content=content, raw_response=data)
            except Exception as e:
                return LLMResponse(content=f"Error: {str(e)}", raw_response=None)

class OllamaProvider(LLMProvider):
    """
    支持本地部署的 Ollama (DeepSeek, Llama3 等)
    """
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model

    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [msg.dict() for msg in messages],
            "stream": False,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/api/chat", json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                content = data["message"]["content"]
                return LLMResponse(content=content, raw_response=data)
            except Exception as e:
                return LLMResponse(content=f"Error connecting to local LLM: {str(e)}", raw_response=None)

# Factory
def get_llm_service() -> LLMProvider:
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.LLM_BASE_URL or "http://localhost:11434",
            model=settings.LLM_MODEL or "llama2"
        )
    elif provider in ["openai", "deepseek"]:
        # DeepSeek 兼容 OpenAI 格式，只需改 base_url
        return OpenAIProvider(
            api_key=settings.LLM_API_KEY or "dummy-key",
            base_url=settings.LLM_BASE_URL or "https://api.openai.com/v1",
            model=settings.LLM_MODEL or "gpt-3.5-turbo"
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
