"""HookGenerator 단위 테스트."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from wp_auto.ai.hook_generator import (
    HOOK_TYPES,
    Hook,
    HookGenerator,
)
from wp_auto.ai.ollama_client import MockOllamaClient


def make_mock_client() -> MockOllamaClient:
    """4종 hook JSON 응답."""
    return MockOllamaClient({
        "주제:": json.dumps({
            "hooks": [
                {"type": "question", "text": "왜 X는 Y일까?", "rationale": "호기심 자극"},
                {"type": "stat", "text": "X%의 사용자가 Y를 모른다.", "rationale": "구체적 수치"},
                {"type": "story", "text": "어느 날 A는 B를 발견했다.", "rationale": "스토리텔링"},
                {"type": "reversal", "text": "X라고 알려진 Y의 진실은 Z다.", "rationale": "상식 뒤집기"},
            ]
        }, ensure_ascii=False)
    })


@pytest.fixture
def mock_client() -> MockOllamaClient:
    return make_mock_client()


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

def test_hook_dataclass() -> None:
    h = Hook(type="question", text="왜?", rationale="호기심")
    assert h.type == "question"
    assert h.text == "왜?"
    assert h.rationale == "호기심"


def test_hook_to_dict() -> None:
    h = Hook(type="stat", text="50%가 모른다")
    d = h.to_dict()
    assert d["type"] == "stat"
    assert d["text"] == "50%가 모른다"
    assert d["rationale"] == ""


# ---------------------------------------------------------------------------
# HookGenerator
# ---------------------------------------------------------------------------

def test_generate_hooks_returns_4_types(mock_client: MockOllamaClient) -> None:
    gen = HookGenerator(mock_client, language="ko")
    hooks = gen.generate_hooks(topic="워드프레스 SEO", keyword="워드프레스 SEO")
    assert len(hooks) == 4
    types_returned = {h.type for h in hooks}
    assert types_returned == set(HOOK_TYPES)


def test_generate_hooks_invalid_json_falls_back(mock_client: MockOllamaClient) -> None:
    client = MockOllamaClient({"주제:": "not valid json"})
    gen = HookGenerator(client, language="ko")
    hooks = gen.generate_hooks(topic="X")
    # fallback: 1개 question hook
    assert len(hooks) == 1
    assert hooks[0].type == "question"


def test_generate_hooks_unsupported_language_raises(mock_client: MockOllamaClient) -> None:
    gen = HookGenerator(mock_client, language="ja")  # 일본어는 미지원
    with pytest.raises(ValueError, match="Unsupported language"):
        gen.generate_hooks(topic="X")


def test_select_best_engagement_score(mock_client: MockOllamaClient) -> None:
    gen = HookGenerator(mock_client, language="ko")
    hooks = gen.generate_hooks(topic="X")
    best = gen.select_best(hooks, criterion="engagement")
    # stat hook이 "?" 또는 숫자 포함 + 적정 길이 → 가산점
    # story ("어느 날 A는 B를 발견했다")도 적정 길이
    assert best in hooks
    assert best.type in HOOK_TYPES


def test_select_best_diversity_returns_random(mock_client: MockOllamaClient) -> None:
    gen = HookGenerator(mock_client, language="ko")
    hooks = gen.generate_hooks(topic="X")
    best = gen.select_best(hooks, criterion="diversity")
    assert best in hooks


def test_select_best_empty_raises() -> None:
    gen = HookGenerator(make_mock_client(), language="ko")
    with pytest.raises(ValueError, match="Empty"):
        gen.select_best([])


def test_generate_best_hook_one_step(mock_client: MockOllamaClient) -> None:
    gen = HookGenerator(mock_client, language="ko")
    best = gen.generate_best_hook(topic="워드프레스 SEO")
    assert isinstance(best, Hook)
    assert best.type in HOOK_TYPES
    assert len(best.text) > 5


def test_english_hook_returns_english_only(mock_client: MockOllamaClient) -> None:
    """영문 prompt → 영문 hook (language isolation)."""
    en_client = MockOllamaClient({
        "Topic:": json.dumps({
            "hooks": [
                {"type": "question", "text": "Why is X?", "rationale": "curiosity"},
                {"type": "stat", "text": "X% don't know Y.", "rationale": "concrete"},
                {"type": "story", "text": "Once upon a time.", "rationale": "story"},
                {"type": "reversal", "text": "Truth is Z.", "rationale": "flip"},
            ]
        })
    })
    gen = HookGenerator(en_client, language="en")
    hooks = gen.generate_hooks(topic="WordPress SEO", keyword="SEO")
    assert len(hooks) == 4
    for h in hooks:
        # 한글 미포함 확인
        assert not any("\uac00" <= c <= "\ud7af" for c in h.text)
