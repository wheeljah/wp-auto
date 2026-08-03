"""CTAInjector 단위 테스트."""
from __future__ import annotations

import json

import pytest

from wp_auto.ai.cta_injector import (
    CTA,
    CTAInjector,
    CTA_TYPES,
)
from wp_auto.ai.ollama_client import MockOllamaClient


def make_mock_client() -> MockOllamaClient:
    """3종 CTA JSON 응답."""
    return MockOllamaClient({
        "주제:": json.dumps({
            "ctas": [
                {"type": "informational", "text": "더 알아보기", "placement_hint": "본문 끝"},
                {"type": "action", "text": "지금 시작하기", "placement_hint": "CTA 버튼"},
                {"type": "social_proof", "text": "커뮤니티 참여", "placement_hint": "푸터"},
            ]
        }, ensure_ascii=False)
    })


@pytest.fixture
def mock_client() -> MockOllamaClient:
    return make_mock_client()


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

def test_cta_dataclass() -> None:
    c = CTA(type="action", text="지금 시작", placement_hint="버튼")
    assert c.type == "action"
    assert c.text == "지금 시작"
    assert c.placement_hint == "버튼"


def test_cta_to_dict() -> None:
    c = CTA(type="informational", text="더 보기")
    d = c.to_dict()
    assert d == {"type": "informational", "text": "더 보기", "placement_hint": ""}


# ---------------------------------------------------------------------------
# CTAInjector
# ---------------------------------------------------------------------------

def test_generate_ctas_returns_3_types(mock_client: MockOllamaClient) -> None:
    gen = CTAInjector(mock_client, language="ko")
    ctas = gen.generate_ctas(topic="X", summary="요약")
    assert len(ctas) == 3
    types = {c.type for c in ctas}
    assert types == set(CTA_TYPES)


def test_generate_ctas_unsupported_language_raises(mock_client: MockOllamaClient) -> None:
    gen = CTAInjector(mock_client, language="ja")
    with pytest.raises(ValueError, match="Unsupported language"):
        gen.generate_ctas(topic="X")


def test_generate_ctas_invalid_json_falls_back(mock_client: MockOllamaClient) -> None:
    client = MockOllamaClient({"주제:": "not json"})
    gen = CTAInjector(client, language="ko")
    ctas = gen.generate_ctas(topic="X")
    assert len(ctas) == 1
    assert ctas[0].type == "informational"


def test_to_html_contains_cta_class(mock_client: MockOllamaClient) -> None:
    gen = CTAInjector(mock_client, language="ko")
    cta = CTA(type="action", text="지금 시작!")
    html = gen.to_html(cta)
    assert "wp-auto-cta" in html
    assert "지금 시작!" in html
    assert "🚀" in html or "label" in html  # label 또는 emoji


def test_inject_into_html_end(mock_client: MockOllamaClient) -> None:
    gen = CTAInjector(mock_client, language="ko")
    cta = CTA(type="action", text="시작!")
    body = "<p>본문</p>"
    result = gen.inject_into_html(body, cta, position="end")
    assert result.startswith("<p>본문</p>")
    assert "wp-auto-cta" in result
    assert "시작!" in result


def test_inject_into_html_after_first_h2(mock_client: MockOllamaClient) -> None:
    gen = CTAInjector(mock_client, language="ko")
    cta = CTA(type="informational", text="더 보기")
    body = "<h2>제목</h2><p>본문</p>"
    result = gen.inject_into_html(body, cta, position="after_first_h2")
    # CTA가 첫 H2 뒤에 삽입
    h2_pos = result.index("</h2>")
    cta_pos = result.index("wp-auto-cta")
    assert cta_pos > h2_pos


def test_inject_into_html_after_first_h2_no_h2_falls_back_to_end(
    mock_client: MockOllamaClient,
) -> None:
    """H2 없으면 end로 fallback."""
    gen = CTAInjector(mock_client, language="ko")
    cta = CTA(type="action", text="시작")
    body = "<p>본문</p>"  # H2 없음
    result = gen.inject_into_html(body, cta, position="after_first_h2")
    # end로 fallback: CTA 박스가 body 끝에 붙음
    assert "wp-auto-cta" in result
    assert "시작" in result
    # body 본문이 CTA 앞에 있어야 함
    assert result.index("<p>본문</p>") < result.index("wp-auto-cta")


def test_select_best_engagement(mock_client: MockOllamaClient) -> None:
    gen = CTAInjector(mock_client, language="ko")
    ctas = gen.generate_ctas(topic="X")
    best = gen.select_best(ctas, criterion="engagement")
    # "지금 시작하기" (action, 강한 동사) → best일 가능성 ↑ (하지만 보장 X)
    assert best in ctas


def test_select_best_empty_raises() -> None:
    gen = CTAInjector(make_mock_client(), language="ko")
    with pytest.raises(ValueError, match="Empty"):
        gen.select_best([])


def test_english_cta_language_isolation() -> None:
    """영문 prompt → 영문 CTA."""
    en_client = MockOllamaClient({
        "Topic:": json.dumps({
            "ctas": [
                {"type": "informational", "text": "Learn more here.", "placement_hint": "end"},
                {"type": "action", "text": "Get started now.", "placement_hint": "button"},
                {"type": "social_proof", "text": "Join the community.", "placement_hint": "footer"},
            ]
        })
    })
    gen = CTAInjector(en_client, language="en")
    ctas = gen.generate_ctas(topic="WordPress SEO")
    assert len(ctas) == 3
    for c in ctas:
        assert not any("\uac00" <= ch <= "\ud7af" for ch in c.text)
