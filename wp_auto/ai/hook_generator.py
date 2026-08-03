"""Hook 생성기 — 4종 hook (질문/통계/스토리/반전) 자동 생성.

체류시간(dwell time)과 클릭률(CTR)을 높이는 첫 1-2문장 hook을
LLM이 4종 후보로 생성 → 그 중 best 선택 또는 다양성 보장.

사용법:
    from wp_auto.ai.ollama_client import OllamaClient
    from wp_auto.ai.hook_generator import HookGenerator

    client = OllamaClient(model="qwen2.5:3b")
    gen = HookGenerator(client, language="ko")

    # 4종 hook 후보
    hooks = gen.generate_hooks(topic="...", keyword="...")

    # best 1개
    best = gen.select_best(hooks, criterion="engagement")
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from wp_auto.ai.ollama_client import LLMClient, parse_json_response
from wp_auto.ai.content_generator import SYSTEM_PROMPTS

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

HOOK_TYPES = ("question", "stat", "story", "reversal")


@dataclass
class Hook:
    """1개 hook 후보."""

    type: str           # question | stat | story | reversal
    text: str           # 실제 hook 문장 (1-2문장)
    rationale: str = "" # 왜 효과적인지 (1문장)

    def to_dict(self) -> dict:
        return {"type": self.type, "text": self.text, "rationale": self.rationale}


class HookGenerator:
    """4종 hook (question/stat/story/reversal) 후보 생성 + best 선택."""

    def __init__(
        self,
        client: LLMClient,
        prompts_dir: Path = PROMPTS_DIR,
        language: str = "ko",
    ) -> None:
        self.client = client
        self.prompts_dir = prompts_dir
        self.language = language
        self._templates: dict[str, str] = {
            lang: (prompts_dir / lang / "hooks.txt").read_text(encoding="utf-8")
            for lang in SUPPORTED_LANGUAGES
        }
        logger.info("HookGenerator initialized: language={}", language)

    def _system_prompt(self) -> str:
        return SYSTEM_PROMPTS.get(self.language, SYSTEM_PROMPTS["ko"])

    def generate_hooks(
        self,
        topic: str,
        keyword: str = "",
        context: str = "",
        temperature: float = 0.7,
    ) -> list[Hook]:
        """4종 hook 후보 생성.

        Args:
            topic: 글 주제
            keyword: 메인 키워드 (없으면 topic 사용)
            context: 추가 컨텍스트 (선택)
            temperature: LLM 샘플링 온도

        Returns:
            Hook 리스트 (4종)
        """
        if self.language not in self._templates:
            raise ValueError(f"Unsupported language: {self.language}")
        prompt = self._templates[self.language].format(
            topic=topic,
            keyword=keyword or topic,
            context=context or "(none)",
        ).replace("__HOOKS_MARKER__", "")  # mock 매칭용 marker 제거
        logger.info("generate_hooks: lang={} topic='{}'", self.language, topic[:40])
        response = self.client.generate(
            prompt,
            system=self._system_prompt(),
            temperature=temperature,
            max_tokens=800,
        )
        try:
            data = parse_json_response(response)
            items = data.get("hooks", [])
            if not items:
                # JSON은 valid지만 "hooks" 키가 없거나 비어있으면 fallback
                raise ValueError("empty hooks list in response")
            hooks = [
                Hook(
                    type=it.get("type", "question"),
                    text=it.get("text", "").strip(),
                    rationale=it.get("rationale", "").strip(),
                )
                for it in items
            ]
            # type 보정
            for h in hooks:
                if h.type not in HOOK_TYPES:
                    h.type = "question"
            return hooks
        except Exception as e:
            logger.error("HookGenerator JSON parse failed: {}", e)
            # fallback: 단일 question hook
            return [
                Hook(
                    type="question",
                    text=f"{topic}에 대해 얼마나 알고 계신가요?",
                    rationale="fallback",
                )
            ]

    def select_best(
        self,
        hooks: list[Hook],
        criterion: str = "engagement",
    ) -> Hook:
        """여러 hook 중 best 1개 선택.

        Args:
            hooks: 후보 hook 리스트
            criterion: "engagement" (length × specificity 휴리스틱)
                       또는 "diversity" (랜덤)

        Returns:
            선택된 Hook
        """
        if not hooks:
            raise ValueError("Empty hook list")
        if criterion == "diversity":
            import random
            return random.choice(hooks)
        # engagement: 길이 80-200자 + '?' 또는 숫자 포함 시 가산
        def score(h: Hook) -> float:
            s = 0.0
            t = h.text
            if 50 <= len(t) <= 200:
                s += 5.0
            if "?" in t or any(c.isdigit() for c in t):
                s += 3.0
            if h.rationale and len(h.rationale) > 10:
                s += 1.0
            return s
        return max(hooks, key=score)

    def generate_best_hook(
        self,
        topic: str,
        keyword: str = "",
        context: str = "",
    ) -> Hook:
        """generate_hooks + select_best 한 번에."""
        hooks = self.generate_hooks(topic=topic, keyword=keyword, context=context)
        return self.select_best(hooks)


__all__ = ["Hook", "HookGenerator", "HOOK_TYPES"]
