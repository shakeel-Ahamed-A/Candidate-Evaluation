from __future__ import annotations
import json
import os
from abc import ABC, abstractmethod
from typing import Type, TypeVar
from dotenv import load_dotenv
from pydantic import BaseModel
T = TypeVar("T", bound=BaseModel)
load_dotenv()

class LLMBackend(ABC):
    @abstractmethod
    def structured(self, *, system: str, payload: dict, schema: Type[T]) -> T:
        raise NotImplementedError

class MockBackend(LLMBackend):
    def structured(self, *, system: str, payload: dict, schema: Type[T]) -> T:
        from .mock_data import generate_mock
        return generate_mock(schema=schema, system=system, payload=payload)

class OpenAIBackend(LLMBackend):
    def __init__(self, model: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("OpenAI mode requires: pip install -r requirements-openai.txt") from exc
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.5")

    def structured(self, *, system: str, payload: dict, schema: Type[T]) -> T:
        response = self.client.responses.parse(model=self.model, instructions=system, input=json.dumps(payload, ensure_ascii=False), text_format=schema)
        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            return parsed
        for item in getattr(response, "output", []):
            for content in getattr(item, "content", []):
                parsed = getattr(content, "parsed", None)
                if parsed is not None:
                    return parsed
        raise RuntimeError("No structured object returned by the model")

def make_backend(provider: str, model: str | None = None) -> LLMBackend:
    return MockBackend() if provider == "mock" else OpenAIBackend(model=model) if provider == "openai" else (_ for _ in ()).throw(ValueError(f"Unsupported provider: {provider}"))
