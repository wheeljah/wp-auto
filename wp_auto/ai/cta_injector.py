"""CTA (Call-to-Action) 생성기 + HTML injection.

글의 끝(또는 중간)에 들어갈 3종 CTA (informational/action/social_proof) 자동 생성.
HTML에 자연스러운 box로 삽입 (CSS inline).

사용법:
    from wp_auto.ai.cta_injector import CTAInjector

    injector = CTAInjector(client, language="ko")
    ctas = injector.generate_ctas(topic="...", summary="...")
    html_with_cta = injector.inject_into_html(body_html, cta=ctas[0], position="end")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from wp_auto.ai.ollama_client import LLMClient, parse_json_response
from wp_auto.ai.content_generator import SYSTEM_PROMPTS

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

CTA_TYPES = ("informational", "action", "social_proof")
CTA_POSITIONS = ("chunk_end", "pillar_end", "mid_article")


@dataclass
class CTA:
    """1개 CTA 후보."""

    type: str           # informational | action | social_proof
    text: str           # 실제 CTA 문장
    placement_hint: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "text": self.text,
            "placement_hint": self.placement_hint,
        }


# CSS: 표준 CTA 박스 (가독성 ↑, 클릭 유도)
CTA_CSS_TEMPLATE = """
<div class="wp-auto-cta" style="
  margin: 24px 0;
  padding: 16px 20px;
  border-left: 4px solid {color};
  background: {bg_color};
  border-radius: 4px;
  font-size: 15px;
  line-height: 1.6;
  color: #1a1a1a;
">
  <div style="font-weight:600;color:{color};margin-bottom:6px;">{label}</div>
  <div>{text}</div>
</div>
"""

CTA_TYPE_META: dict[str, dict[str, str]] = {
    "ko": {
        "informational": {"label": "📚 더 알아보기", "color": "#2563eb", "bg_color": "#eff6ff"},
        "action": {"label": "🚀 지금 시작", "color": "#dc2626", "bg_color": "#fef2f2"},
        "social_proof": {"label": "👥 함께해요", "color": "#059669", "bg_color": "#ecfdf5"},
    },
    "en": {
        "informational": {"label": "📚 Learn more", "color": "#2563eb", "bg_color": "#eff6ff"},
        "action": {"label": "🚀 Get started", "color": "#dc2626", "bg_color": "#fef2f2"},
        "social_proof": {"label": "👥 Join us", "color": "#059669", "bg_color": "#ecfdf5"},
    },
}


class CTAInjector:
    """3종 CTA 생성 + HTML injection."""

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
            lang: (prompts_dir / lang / "cta.txt").read_text(encoding="utf-8")
            for lang in SUPPORTED_LANGUAGES
        }
        logger.info("CTAInjector initialized: language={}", language)

    def _system_prompt(self) -> str:
        return SYSTEM_PROMPTS.get(self.language, SYSTEM_PROMPTS["ko"])

    def generate_ctas(
        self,
        topic: str,
        summary: str = "",
        keyword: str = "",
        position: str = "chunk_end",
        temperature: float = 0.6,
    ) -> list[CTA]:
        """3종 CTA 후보 생성.

        Args:
            topic: 글 주제
            summary: 글의 핵심 요약 (없으면 topic 사용)
            keyword: 메인 키워드
            position: chunk_end | pillar_end | mid_article
            temperature: LLM 샘플링

        Returns:
            CTA 리스트 (3종)
        """
        if self.language not in self._templates:
            raise ValueError(f"Unsupported language: {self.language}")
        prompt = self._templates[self.language].format(
            topic=topic,
            keyword=keyword or topic,
            summary=summary or topic,
            position=position,
        ).replace("__CTA_MARKER__", "")  # mock 매칭용 marker 제거
        logger.info(
            "generate_ctas: lang={} topic='{}' position={}",
            self.language, topic[:40], position,
        )
        response = self.client.generate(
            prompt,
            system=self._system_prompt(),
            temperature=temperature,
            max_tokens=600,
        )
        try:
            data = parse_json_response(response)
            items = data.get("ctas", [])
            if not items:
                raise ValueError("empty ctas list in response")
            ctas = [
                CTA(
                    type=it.get("type", "informational"),
                    text=it.get("text", "").strip(),
                    placement_hint=it.get("placement_hint", "").strip(),
                )
                for it in items
            ]
            for c in ctas:
                if c.type not in CTA_TYPES:
                    c.type = "informational"
            return ctas
        except Exception as e:
            logger.error("CTAInjector JSON parse failed: {}", e)
            return [
                CTA(
                    type="informational",
                    text=f"이 주제의 더 많은 정보는 공식 문서를 참고하세요.",
                )
            ]

    def to_html(self, cta: CTA) -> str:
        """CTA 1개 → HTML 박스 (CSS inline)."""
        meta = CTA_TYPE_META.get(self.language, CTA_TYPE_META["ko"])
        m = meta.get(cta.type, meta["informational"])
        return CTA_CSS_TEMPLATE.format(
            color=m["color"],
            bg_color=m["bg_color"],
            label=m["label"],
            text=cta.text,
        )

    def inject_into_html(
        self,
        body_html: str,
        cta: CTA,
        position: str = "end",
    ) -> str:
        """body HTML에 CTA 주입.

        Args:
            body_html: 원본 HTML
            cta: 삽입할 CTA
            position: "end" (HTML 끝) | "after_first_h2" (첫 H2 뒤)

        Returns:
            CTA가 삽입된 HTML
        """
        cta_html = self.to_html(cta)
        if position == "after_first_h2":
            # 첫 <h2> 뒤에 삽입
            import re
            m = re.search(r'(<h2[^>]*>.*?</h2>)', body_html, flags=re.DOTALL)
            if m:
                return body_html[: m.end()] + "\n" + cta_html + body_html[m.end():]
        # default: end
        return body_html.rstrip() + "\n\n" + cta_html

    def select_best(
        self,
        ctas: list[CTA],
        criterion: str = "engagement",
    ) -> CTA:
        """여러 CTA 중 best 1개 선택.

        Args:
            ctas: 후보
            criterion: "engagement" | "diversity"
        """
        if not ctas:
            raise ValueError("Empty CTA list")
        if criterion == "diversity":
            import random
            return random.choice(ctas)
        # engagement: 길이 30-150 + 강한 동사 포함
        def score(c: CTA) -> float:
            t = c.text
            s = 0.0
            if 30 <= len(t) <= 150:
                s += 5.0
            # 강한 동사
            for verb in ("시작", "다운", "받으", "해보", "참여", "구독", "start", "try", "join", "download", "subscribe"):
                if verb.lower() in t.lower():
                    s += 2.0
                    break
            if c.placement_hint:
                s += 0.5
            return s
        return max(ctas, key=score)


__all__ = ["CTA", "CTAInjector", "CTA_TYPES", "CTA_POSITIONS"]
