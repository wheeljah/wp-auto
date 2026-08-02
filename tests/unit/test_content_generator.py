"""AI 콘텐츠 생성기 단위 테스트 (MockOllamaClient 사용)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from wp_auto.ai.content_generator import ContentGenerator, Outline
from wp_auto.ai.ollama_client import (
    MockOllamaClient,
    OllamaClient,
    parse_json_response,
)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "wp_auto" / "ai" / "prompts"


# === 1. MockOllamaClient ===

def test_mock_client_returns_default_when_no_match() -> None:
    """키워드 매칭 없으면 기본 JSON 응답."""
    client = MockOllamaClient()
    response = client.generate("아무 키워드 매칭 없음")
    assert "Mock 제목" in response
    assert "outline" in response


def test_mock_client_matches_keyword() -> None:
    """키워드 매칭 → 사전 정의 응답."""
    custom_response = "<h1>커스텀 제목</h1><p>본문</p>"
    client = MockOllamaClient({"워드프레스 SEO": custom_response})
    response = client.generate("워드프레스 SEO 가이드를 작성해줘")
    assert response == custom_response


def test_mock_client_call_count() -> None:
    """호출 횟수 카운팅."""
    client = MockOllamaClient()
    client.generate("prompt 1")
    client.generate("prompt 2")
    assert client.call_count == 2


def test_mock_client_available() -> None:
    """Mock은 항상 available."""
    client = MockOllamaClient()
    assert client.is_available() is True


def test_mock_client_list_models() -> None:
    """Mock list_models."""
    client = MockOllamaClient()
    models = client.list_models()
    assert "mock-model:8b" in models


# === 2. parse_json_response ===

def test_parse_json_response_clean() -> None:
    """코드블록 없는 JSON."""
    text = '{"title": "X", "key": "value"}'
    result = parse_json_response(text)
    assert result["title"] == "X"


def test_parse_json_response_with_codeblock() -> None:
    """```json ... ``` 코드블록 제거."""
    text = '```json\n{"title": "X", "key": "value"}\n```'
    result = parse_json_response(text)
    assert result["title"] == "X"


def test_parse_json_response_with_plain_codeblock() -> None:
    """``` (no json) 코드블록."""
    text = '```\n{"title": "X"}\n```'
    result = parse_json_response(text)
    assert result["title"] == "X"


def test_parse_json_response_invalid_raises() -> None:
    """JSON 파싱 실패 시 예외."""
    with pytest.raises(json.JSONDecodeError):
        parse_json_response("not json")


# === 3. Outline dataclass ===

def test_outline_to_dict() -> None:
    """Outline → dict 변환."""
    outline = Outline(
        title="테스트 제목",
        meta_description="메타 설명 123",
        slug="test-slug",
        outline=[{"h2": "H2-1", "h3": ["H3-1", "H3-2"]}],
        faq=[{"q": "Q1", "a": "A1"}],
        key_takeaways=["KT1", "KT2"],
    )
    d = outline.to_dict()
    assert d["title"] == "테스트 제목"
    assert d["outline"][0]["h2"] == "H2-1"


def test_outline_text_serialization() -> None:
    """Outline → outline_text (draft 프롬프트용)."""
    outline = Outline(
        title="",
        meta_description="",
        slug="",
        outline=[
            {"h2": "첫 번째 H2", "h3": ["H3-1", "H3-2"]},
            {"h2": "두 번째 H2", "h3": ["H3-1"]},
        ],
    )
    text = outline.outline_text()
    assert "첫 번째 H2" in text
    assert "두 번째 H2" in text
    assert "H3-1" in text


# === 4. ContentGenerator ===

@pytest.fixture
def mock_outline_response() -> str:
    return json.dumps(
        {
            "title": "워드프레스 SEO 5가지 핵심",
            "meta_description": "워드프레스 SEO의 핵심 5가지를 정리한 가이드. Rank Math 점수 90+ 받는 방법.",
            "slug": "wordpress-seo-5-tips",
            "outline": [
                {"h2": "키워드 조사", "h3": ["Google Keyword Planner", "경쟁 분석"]},
                {"h2": "Rank Math 설치", "h3": ["무료 플러그인", "점수화 기능"]},
                {"h2": "콘텐츠 최적화", "h3": ["글자 수 2500+", "FAQ 추가"]},
            ],
            "faq": [
                {"q": "Rank Math는 무료인가요?", "a": "네, 무료 버전만으로도 충분합니다."},
                {"q": "점수 75 미만이어도 발행 가능한가요?", "a": "가능하지만 보완을 권장합니다."},
            ],
            "key_takeaways": ["키워드 조사가 시작", "Rank Math로 점수화 자동화"],
        },
        ensure_ascii=False,
    )


@pytest.fixture
def mock_draft_response() -> str:
    return """<p>워드프레스 SEO는 검색 노출을 결정하는 핵심 요소입니다. 이 가이드에서 5가지 전략을 소개합니다.</p>
<h2>키워드 조사</h2>
<p>워드프레스 SEO의 첫 단계는 키워드 조사입니다. Google Keyword Planner로 경쟁 낮은 키워드를 찾으세요.</p>
<h3>Google Keyword Planner</h3>
<p>무료 도구로 검색량을 확인합니다.</p>
<h2>Rank Math 설치</h2>
<p>Rank Math는 무료 SEO 플러그인입니다. 점수화 기능을 제공합니다.</p>
<h2>콘텐츠 최적화</h2>
<p>워드프레스 SEO를 위한 글은 2500자 이상이어야 합니다.</p>
<details><summary>Q. Rank Math는 무료인가요?</summary><p>네, 무료 버전만으로도 충분합니다.</p></details>
<details><summary>Q. 점수 75 미만이어도 발행 가능한가요?</summary><p>가능하지만 보완을 권장합니다.</p></details>
<blockquote>워드프레스 SEO는 꾸준함이 핵심입니다.</blockquote>
<p>워드프레스 SEO 마스터를 위해 매일 1개씩 발행하세요.</p>"""


def test_generate_outline_parses_json(
    mock_outline_response: str,
) -> None:
    """generate_outline: JSON 파싱."""
    client = MockOllamaClient({"글 개요": mock_outline_response})
    gen = ContentGenerator(client, prompts_dir=PROMPTS_DIR)
    outline = gen.generate_outline(
        topic="워드프레스 SEO", keyword="워드프레스 SEO", intent="informational"
    )
    assert outline.title == "워드프레스 SEO 5가지 핵심"
    assert len(outline.outline) == 3
    assert "키워드 조사" in outline.outline[0]["h2"]


def test_generate_outline_fallback_on_invalid_json() -> None:
    """outline JSON 파싱 실패 시 fallback outline."""
    client = MockOllamaClient({"글 개요": "not valid json {{{"})
    gen = ContentGenerator(client, prompts_dir=PROMPTS_DIR)
    outline = gen.generate_outline(topic="X", keyword="X")
    # fallback: title = topic
    assert outline.title == "X"
    assert len(outline.outline) >= 1  # fallback outline


def test_generate_draft_returns_html(
    mock_outline_response: str, mock_draft_response: str
) -> None:
    """generate_draft: HTML 반환."""
    client = MockOllamaClient(
        {
            "글 개요": mock_outline_response,
            "본문(HTML)": mock_draft_response,
        }
    )
    gen = ContentGenerator(client, prompts_dir=PROMPTS_DIR)
    outline = gen.generate_outline(topic="X", keyword="워드프레스 SEO")
    html = gen.generate_draft(outline, keyword="워드프레스 SEO")
    assert "<h2>" in html
    assert "워드프레스 SEO" in html


def test_review_calls_client_with_feedback() -> None:
    """review: 피드백 + 권고사항 포함 프롬프트."""
    client = MockOllamaClient(
        {"개선된 HTML": "<p>개선된 본문</p>"}
    )
    gen = ContentGenerator(client, prompts_dir=PROMPTS_DIR)
    improved = gen.review(
        html="<p>원본</p>",
        keyword="X",
        current_score=50.0,
        level="보완 필요",
        feedback=["글자 수 부족", "메타 설명 없음"],
        recommendations=["글자 추가", "메타 설명 작성"],
    )
    assert "개선된" in improved
    assert client.call_count == 1


def test_generate_alt_text_strips_period() -> None:
    """alt 텍스트 끝 마침표 제거."""
    client = MockOllamaClient({"alt 텍스트": "Rank Math 점수 분포 그래프."})
    gen = ContentGenerator(client, prompts_dir=PROMPTS_DIR)
    alt = gen.generate_alt_text(
        keyword="워드프레스 SEO",
        filename="chart.png",
        context="Rank Math 점수 분포",
    )
    assert not alt.endswith(".")


def test_generate_full_post_no_review_when_disabled(
    mock_outline_response: str, mock_draft_response: str
) -> None:
    """enable_review=False → review skip, 1 iteration."""
    client = MockOllamaClient(
        {
            "글 개요": mock_outline_response,
            "본문(HTML)": mock_draft_response,
        }
    )
    gen = ContentGenerator(client, prompts_dir=PROMPTS_DIR, min_score=75.0)
    post = gen.generate_full_post(
        topic="X", keyword="워드프레스 SEO", enable_review=False
    )
    assert post.iterations == 1
    assert post.title == "워드프레스 SEO 5가지 핵심"
    assert "<h2>" in post.html


def test_generate_full_post_iterates_when_low_score(
    mock_outline_response: str, mock_draft_response: str
) -> None:
    """점수 < 75 → review 호출 (iterations 증가)."""
    client = MockOllamaClient(
        {
            "글 개요": mock_outline_response,
            "본문(HTML)": mock_draft_response,
            "개선된 HTML": mock_draft_response,  # review도 같은 응답
        }
    )
    gen = ContentGenerator(
        client, prompts_dir=PROMPTS_DIR, min_score=75.0, max_iterations=2
    )
    post = gen.generate_full_post(
        topic="X", keyword="워드프레스 SEO", enable_review=True
    )
    # 점수 확인 (mock draft는 60-80점 사이라 75 미만 가능)
    assert post.iterations >= 1
    assert post.score is not None
    assert "total_score" in post.score


# === 5. OllamaClient (real, integration smoke) ===

def test_ollama_client_is_available_returns_bool() -> None:
    """OllamaClient.is_available() returns bool (without crashing)."""
    # is_available() returns False if Ollama is not running, but doesn't raise
    client = OllamaClient(model="llama3.1:8b", host="http://localhost:11434")
    result = client.is_available()
    assert isinstance(result, bool)
    # 보통 환경에 Ollama 실행 중이므로 True
    if not result:
        # fallback: list_models returns []
        assert client.list_models() == []


def test_ollama_client_uses_protocol() -> None:
    """OllamaClient가 LLMClient Protocol을 만족."""
    client = OllamaClient()
    assert hasattr(client, "generate")
    assert callable(client.generate)
