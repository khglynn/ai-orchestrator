from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class ModelResponse:
    """Standardized response from AI models"""
    model_name: str
    response: str
    metadata: Dict[str, Any]
    error: Optional[str] = None


class BaseModel(ABC):
    """Abstract base class for AI model integrations"""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
    
    @abstractmethod
    async def query(self, prompt: str, **kwargs) -> ModelResponse:
        """Query the model with a prompt"""
        pass
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def query_with_retry(self, prompt: str, **kwargs) -> ModelResponse:
        """Query with automatic retry logic"""
        return await self.query(prompt, **kwargs)
