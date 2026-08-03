"""Ollama 로컬 LLM 클라이언트 (무료, 온디바이스).

기본 사용법:
    from wp_auto.ai.ollama_client import OllamaClient
    client = OllamaClient(model="llama3.1:8b")
    response = client.generate("한국어 블로그 글...")
    print(response)

추상화:
    - OllamaClient: 실제 Ollama HTTP API 호출
    - MockOllamaClient: 테스트용 fixture 응답
"""

from __future__ import annotations

import json
from typing import Protocol

import httpx
from loguru import logger


class LLMClient(Protocol):
    """LLM 클라이언트 인터페이스 (Ollama / OpenAI / Mock 호환)."""

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """프롬프트 → 응답 텍스트 (str)."""
        ...


class OllamaClient:
    """Ollama 로컬 LLM 클라이언트.

    기본 endpoint: http://localhost:11434 (Ollama 기본)
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        host: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        logger.info("OllamaClient initialized: model={}, host={}", model, self.host)

    def is_available(self) -> bool:
        """Ollama 서버가 응답하는지 확인."""
        try:
            resp = self._client.get(f"{self.host}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    def list_models(self) -> list[str]:
        """설치된 모델 목록."""
        try:
            resp = self._client.get(f"{self.host}/api/tags", timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except httpx.RequestError as e:
            logger.error("list_models failed: {}", e)
            return []

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """단일 generate 호출 (비스트리밍).

        Ollama /api/generate 사용. response 필드만 반환.
        """
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                # Force CPU: GTX 1050 (Pascal, compute 6.1) PTX incompatible with
                # ollama 0.32.5's CUDA 12.6 build. Vulkan falls back to GPU but causes
                # slow VRAM swap on 2GB. num_gpu=0 forces pure CPU.
                "num_gpu": 0,
            },
        }
        if system:
            payload["system"] = system

        try:
            resp = self._client.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self._client.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            response = data.get("response", "")
            logger.debug(
                "ollama generate: model={} len={} tokens={}",
                self.model,
                len(response),
                data.get("eval_count", 0),
            )
            return response
        except httpx.RequestError as e:
            logger.error("ollama generate failed: {}", e)
            raise


class MockOllamaClient:
    """테스트/오프라인용 mock 클라이언트. 사전 정의된 응답 반환.

    사용법:
        client = MockOllamaClient({
            "한국어 블로그": "<h1>제목</h1><p>본문</p>",
        })
        response = client.generate("한국어 블로그")
    """

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.call_count = 0
        logger.debug("MockOllamaClient initialized")

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        self.call_count += 1
        # prompt prefix 매칭
        for keyword, response in self.responses.items():
            if keyword in prompt:
                logger.debug("MockOllama: matched '{}' → response len={}", keyword, len(response))
                return response
        # 기본 응답
        default = (
            '{"title": "Mock 제목", "meta_description": "Mock 메타 설명", '
            '"slug": "mock-slug", "outline": [{"h2": "Mock H2", "h3": ["H3-1"]}], '
            '"faq": [{"q": "Mock Q", "a": "Mock A"}], "key_takeaways": ["Mock takeaway"]}'
        )
        logger.debug("MockOllama: default response (prompt did not match any keyword)")
        return default

    def is_available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["mock-model:8b"]


def parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON 추출 (코드블록 wrapping 처리)."""
    text = text.strip()
    # ```json ... ``` 또는 ``` ... ``` 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄 (```json 또는 ```) 제거
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # 마지막 ``` 제거
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


__all__ = [
    "LLMClient",
    "OllamaClient",
    "MockOllamaClient",
    "parse_json_response",
]
