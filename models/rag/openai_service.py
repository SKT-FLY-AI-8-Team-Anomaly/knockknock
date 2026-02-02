"""
OpenAI Integration for RAG
Handles embeddings and LLM responses
"""

import aiohttp
from typing import Any, Optional
from rag_core import IEmbeddingService


class OpenAIService(IEmbeddingService):
    """OpenAI service for embeddings and chat completions"""
    
    def __init__(
        self,
        api_key: str,
        embedding_model: str = "text-embedding-3-small",
        chat_model: str = "gpt-4-turbo"
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.base_url = "https://api.openai.com/v1"
    
    async def _openai_fetch(
        self,
        path: str,
        body: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a request to OpenAI API"""
        url = f"{self.base_url}/{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenAI request failed: {response.status} {error_text}"
                    )
                return await response.json()
    
    async def create_embedding(self, input_text: str) -> list[float]:
        """Create embeddings for text"""
        payload = {
            "model": self.embedding_model,
            "input": input_text,
        }
        
        result = await self._openai_fetch("embeddings", payload)
        
        try:
            vector = result["data"][0]["embedding"]
            if not isinstance(vector, list):
                raise ValueError("Invalid embedding response from OpenAI")
            return vector
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Invalid embedding response structure: {e}")
    
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        rag_context: Optional[str] = None
    ) -> str:
        """Generate a chat response"""
        messages = [
            {
                "role": "system",
                "content": system_prompt
                + (f"\n\n참고 문서:\n{rag_context}" if rag_context else ""),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]
        
        payload = {
            "model": self.chat_model,
            "messages": messages,
        }
        
        response = await self._openai_fetch("chat/completions", payload)
        
        try:
            reply = response["choices"][0]["message"]["content"]
            return reply
        except (KeyError, IndexError) as e:
            return "답변을 생성하지 못했습니다."
