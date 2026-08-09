# inbox/ — NotebookLM export 저장소

**NotebookLM에서 export한 Markdown 파일을 저장하는 곳** (로컬 only, Git commit 안 됨).

## 사용법

1. **NotebookLM에서 export**:
   - Studio → Blog Post → Download as Markdown
   - `~/Downloads/notebooklm-*.md`

2. **이 디렉토리로 복사**:
   ```powershell
   Copy-Item "$env:USERPROFILE\Downloads\notebooklm-*.md" "D:\Google_blog\wp-auto\inbox\"
   ```

3. **frontmatter 보강** (wp-auto 형식):
   ```markdown
   ---
   title: OpenAI GPT-6 발표: 추론 능력 10배 강화
   slug: openai-gpt-6-launch
   language: ko
   categories:
     - Tech & AI
   tags:
     - OpenAI
     - GPT-6
   date: 2026-08-09
   focus_keyword: OpenAI GPT-6
   hero_image: assets/images/openai_gpt6_hero.png
   hero_attribution: "by Alice via Pexels"
   ---
   ```

4. **publish-md 실행**:
   ```powershell
   cd D:\Google_blog\wp-auto
   .\.venv\Scripts\python.exe -m wp_auto publish-md inbox\<file>.md
   ```

## 자세한 워크플로우

[../docs/notebooklm_workflow.md](../docs/notebooklm_workflow.md) 참고.

## ⚠️ 주의

- `.gitignore`에 `inbox/` 추가됨 (로컬 only)
- publish 전 반드시 **NotebookLM이 1차 출처를 정확히 인용했는지** 검증 (NotebookLM도 100% 정확하지 않음)
- Hero image는 Nano Banana 또는 Pexels/Wikimedia에서 별도 다운로드 후 `assets/images/`에 저장
