# WordPress REST API 자동 업로드 가이드 (wp-auto)

> 작성일: 2026-08-04
> 범위: wp-auto로 생성한 콘텐츠를 InfinityFree/실 호스팅 WP에 자동 업로드
> 핵심: `WP_MOCK=true` → Mock SQLite DB, `WP_MOCK=false` → Real REST API (자동 전환)

---

## 0. TL;DR

```bash
# .env 한 줄만 바꾸면 끝
WP_MOCK=false
WP_SITE_URL=https://yoursite.epizy.com
WP_USER=your_admin_name
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

# 이후 모든 wp-auto 명령이 자동으로 실 WP에 publish
wp-auto publish-md oneoff/sample_l_input.md --status publish
wp-auto publish out/article.html --title "Best USB-C Charger 2026"
```

---

## 1. WP REST API가 가능한 일 (1차 출처)

> 1차 출처: [WordPress REST API 공식](https://developer.wordpress.org/rest-api/) — "The WordPress REST API provides API endpoints for WordPress data types that allow developers to interact with sites remotely by sending and receiving JSON objects."

wp-auto의 `RealWordPressClient`가 사용하는 endpoints:

| Endpoint | HTTP | 용도 | wp-auto 메서드 |
|---|---|---|---|
| `/wp/v2/posts` | GET | 글 목록 조회 | `list_posts()` |
| `/wp/v2/posts/{id}` | GET | 단일 글 조회 | `get_post()` |
| `/wp/v2/posts` | POST | **새 draft 작성** | `create_draft()` |
| `/wp/v2/posts/{id}` | POST | **글 수정/발행** | `update_post()` / `publish()` |
| `/wp/v2/posts/{id}` | POST (status=future) | **예약 발행** | `schedule_publish()` |
| `/wp/v2/media` | POST | **이미지 업로드** | `upload_image()` |
| `/wp/v2/categories` | GET | category 목록 | `list_categories()` |

> 즉, **wp-auto는 wp-admin UI에서 하는 모든 작업을 API로 자동화** 가능.

---

## 2. 인증: Application Password (1차 출처: WordPress 공식)

> 1차 출처: [WordPress.org REST API Authentication](https://developer.wordpress.org/rest-api/authentication/) — "Application Passwords is the recommended authentication method for the REST API."

### 2.1 Application Password 생성 (WP Admin, 1분)

1. WP Admin 로그인
2. 좌측 **Users → Profile** (본인 계정)
3. 하단 스크롤 → **Application Passwords** 섹션
4. **New Application Password Name**: `wp-auto` (식별용 이름)
5. **Add** 클릭
6. **생성된 24자 비밀번호 표시** (예: `xxxx xxxx xxxx xxxx xxxx xxxx`) — **공백 포함**
   - ⚠️ **이 화면을 닫으면 다시 못 봄!** 복사해서 안전한 곳에 저장
7. **wp-auto에서 사용** (아래 .env 설정)

> **왜 Application Password?**
> - 메인 계정 비밀번호 노출 안 함 (별도 토큰, 폐기 가능)
> - HTTPS Basic Auth로 안전 전송
> - WP 5.6+ 표준, plugin 불필요
> - 출처: [WP REST API Authentication 공식](https://developer.wordpress.org/rest-api/authentication/)

### 2.2 권한 확인

Application Password는 **사용자 권한을 그대로 따름**:
- **Administrator**: 모든 작업 가능 (publish 포함) — 1인 self-use에 적합
- **Editor**: publish 가능, settings/plugin 설치 불가
- **Author**: 본인 글만 publish
- **Contributor**: draft만 작성

> 1인 self-use = Administrator 권한 그대로 사용 OK.

---

## 3. .env 설정 (5분)

### 3.1 파일 위치

`D:\Google_blog\wp-auto\.env` (이미 존재 — WP_MOCK=true로 시작)

### 3.2 WP_MOCK=true (기존, Mock 모드, 기본값)

```bash
# Mock 모드 (1인 self-use 테스트/시연용)
WP_MOCK=true
DB_PATH=./data/wp_auto.db
```

- MockWordPressClient 사용 (SQLite DB)
- `wp-auto list-posts`로 70+ posts (시연 누적) 확인 가능
- 실제 WP 호출 안 함 (네트워크 의존 0)

### 3.3 WP_MOCK=false (Real 모드, 실 WP 발행)

```bash
# Real 모드 (실 WP에 자동 발행)
WP_MOCK=false
WP_SITE_URL=https://yoursite.epizy.com
WP_USER=your_admin_name
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

- RealWordPressClient 사용 (httpx + Application Password)
- 모든 wp-auto 명령이 실제 WP에 REST API 호출
- Mock DB는 더 이상 안 쓰임 (단, 시연 데이터 보존 위해 DB_PATH는 그대로 둬도 OK)

> **공백 포함 24자 비밀번호 주의**: `xxxx xxxx xxxx xxxx xxxx xxxx` 형식 그대로 복사. .env parser가 따옴표/공백 그대로 보존.

### 3.4 .env 자동 로드 (이미 구현됨)

> 1차 출처: `wp_auto/cli/main.py` `_load_dotenv()` — CLI 실행 시 자동 .env 로드

- `wp-auto` CLI 실행 시 자동 .env 읽음
- 시연 스크립트들도 직접 .env 로드 (예: `oneoff_chunked_k_affiliate.py` 참고)

---

## 4. 사용 예시 (실제 흐름)

### 4.1 직접 작성 markdown → publish

```bash
# markdown 파일 1개 = 1개 pillar + N chunks = N+1개 WP posts
wp-auto publish-md oneoff/sample_l_input.md --status publish
```

- frontmatter의 `slug`, `tags`, `categories` 자동 적용
- `--as-single` 또는 `--as-cluster` 모드 선택
- `--score-threshold 75` 통과 시 자동 publish, 실패 시 차단

### 4.2 기존 chunked-generator HTML → publish

```bash
# K 데모 시 chunked-generator로 만든 single.html을 직접 publish
wp-auto publish out/k_affiliate_single.html \
  --title "Best USB-C Fast Charger 2026" \
  --focus-keyword "USB-C charger" \
  --status publish
```

### 4.3 URL/PDF 입력 → outline → publish (v0.9 신규)

```bash
# 1) URL → outline 자동 생성
wp-auto research "Best USB-C fast charger 2026" \
  --source https://en.wikipedia.org/wiki/USB-C \
  --keyword "USB-C charger" \
  --intent "commercial investigation" \
  --language en \
  --out usb_charger.outline.json

# 2) outline → chunked HTML
# (chunked-generator 명령은 향후 통합; 현재는 Python script 필요)
.venv/Scripts/python.exe -c "
import asyncio
from wp_auto.ai.ollama_client import OllamaClient
from wp_auto.ai.content_generator import ContentGenerator
from wp_auto.ai.chunked_generator import ChunkedContentGenerator
import json
client = OllamaClient(model='qwen2.5:7b')
data = json.load(open('usb_charger.outline.json', encoding='utf-8'))
from wp_auto.ai.content_generator import Outline
outline = Outline(**data['outline'])
gen = ChunkedContentGenerator(client, inject_schema=True, inject_affiliate=True)
cluster = gen.generate_pillar_cluster(outline, language='en')
specs = cluster.to_wp_post_specs()
# save to file or print
print(json.dumps(specs, ensure_ascii=False, indent=2))
"

# 3) publish (HTML 또는 직접 loop)
wp-auto publish out/usb_charger.html --status publish
```

### 4.4 일괄 publish (여러 글)

```bash
# shell for-loop + publish
for f in out/articles/*.html; do
  title=$(basename "$f" .html | sed 's/-/ /g')
  wp-auto publish "$f" --title "$title" --status publish
done
```

### 4.5 예약 발행 (Phase 2 마케팅용)

```bash
# 2026-09-01 09:00 Asia/Seoul = 2026-09-01T00:00 UTC
wp-auto publish out/article.html \
  --status future \
  --at "2026-09-01T00:00"
```

> `--at` 형식: `YYYY-MM-DDTHH:MM` (Asia/Seoul → UTC 자동 변환 안 함, 사용자가 UTC 입력)

### 4.6 발행 결과 확인

```bash
# 최근 발행 글 10개
wp-auto list-posts --status publish --limit 10
```

출력 예시:
```
   ID  Status       Title                                              Created
---------------------------------------------------------------------------------------
   79  publish      워드프레스 수익화 블로그 1인 셀프 가이드 2026         2026-08-04 14:23
   78  publish      [Chunk] 8. 결론 — 1인 운영자의 단계별 로드맵         2026-08-04 14:23
   77  publish      [Chunk] 7. 자주 묻는 질문                              2026-08-04 14:23
   ...
```

---

## 5. Rate Limiting (안전장치)

> 1차 출처: [Real client 구현](https://github.com/wheeljah/wp-auto/blob/main/wp_auto/wp/real_client.py) — `RateLimiter(max_per_300s=100)` 5분 window

- wp-auto는 **5분당 100 요청** 자동 제한
- 평균 3초당 1요청 (WP 서버 부하 방지)
- WP 서버가 429 (Too Many Requests) 응답 시 자동 대기 후 재시도

> 1인 self-use 기준 일 100개 publish해도 문제 없음 (5분 window 100 req × 288 windows/일 = 28,800 req/day)

---

## 6. Troubleshooting

### 6.1 "401 Unauthorized"

- **원인 1**: Application Password 잘못 입력 (공백 누락, 24자 미만 등)
- **원인 2**: WP_SITE_URL에 trailing slash (`https://yoursite.com/` ❌) → rstrip("/") 자동 처리되지만 user 부분이 다를 수 있음
- **원인 3**: WP 사용자 이름 오타
- **해결**:
  1. .env에서 따옴표 없이 정확히 입력
  2. WP Admin에서 새 Application Password 생성 후 다시 시도

### 6.2 "403 Forbidden"

- **원인**: 사용자 권한 부족 (예: Contributor가 publish 시도)
- **해결**: Administrator 권한으로 로그인하거나, WP Admin에서 권한 변경

### 6.3 "404 Not Found"

- **원인**: Pretty permalink 비활성화 또는 REST API 비활성화
- **해결**:
  1. Settings → Permalinks → Post name 활성화
  2. wp-config.php에 `define('WP_JSON', true);` 추가 (보통 기본값)

### 6.4 "Connection timeout"

- **원인**: InfinityFree 무료 tier 느린 응답, 또는 WP 서버 점검 중
- **해결**: 
  - 5-10분 후 재시도
  - `.env`의 timeout 조정 (현재 30초, 필요시 wp_auto/wp/real_client.py 수정)

### 6.5 Mock과 Real 번갈아 쓰기

```bash
# Mock으로 시연/테스트
wp-auto list-posts          # Mock DB에서 70+ posts 표시

# .env에서 WP_MOCK=false로 바꾼 후
wp-auto publish out/x.html  # 실 WP에 publish
```

> **단, .env 변경 후 새 터미널에서 실행** (env 캐싱 방지)

### 6.6 Mock DB 초기화 (시연 누적 70+ posts 청소)

```bash
# 1) Mock 모드 (WP_MOCK=true)에서만
wp-auto clean-mock
# 또는
.venv/Scripts/python.exe -c "
from pathlib import Path
import sqlite3
db = Path('./data/wp_auto.db')
if db.exists():
    db.unlink()
    print('Mock DB deleted')
"
```

> Real 모드에서는 `wp-auto clean-mock` ❌ 사용 금지 (실 WP에 영향 없지만, WP_MOCK=true인 경우만 작동)

---

## 7. wp-auto 전체 publish 흐름 (mermaid)

```
[사용자]  →  [wp-auto CLI / Python]
   │
   ├── publish <html-file>
   ├── publish-md <md-file>
   ├── publish <id>  (기존 draft → publish)
   │
   ↓
[get_wp_client()]  ←  factory.py: .env 읽고 분기
   │
   ├── WP_MOCK=true    →  MockWordPressClient (SQLite)
   └── WP_MOCK=false   →  RealWordPressClient (httpx + WP REST API)
   │
   ↓
[WordPress]
   │
   ├── Mock:  ./data/wp_auto.db
   └── Real:  https://yoursite.com/wp-json/wp/v2/posts
```

---

## 8. 고급: WP Application Password 보안

### 8.1 폐기

- WP Admin → Users → Profile → **Application Passwords** 섹션
- 기존 `wp-auto` 옆 **Revoke** 클릭
- 새 password 생성 후 .env 업데이트

### 8.2 여러 Application Password

- 용도별로 분리 가능 (예: `wp-auto-cli`, `wp-auto-cron`)
- 각 token 개별 폐기 가능 (메인 비밀번호 안 건드림)

### 8.3 HTTPS only

- 1차 출처: [WP Application Password 공식](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/) — "Application Passwords require HTTPS, with the exception of local development environments."
- InfinityFree 무료 SSL (Let's Encrypt) 사용 중이면 OK
- HTTP로 호출 시 401 응답

---

## 9. End-to-end 데모

`oneoff_chunked_k_affiliate.py` (이미 v0.8 커밋됨, [GitHub](https://github.com/wheeljah/wp-auto/blob/main/oneoff_chunked_k_affiliate.py)):

```python
# Mock/Real 자동 전환
async def _pub_cluster():
    wp = get_wp_client()  # .env 기반
    ids = []
    for spec in cluster_specs:
        pid = await wp.create_draft(
            title=spec["title"],
            content=spec["content"],
            slug=spec["slug"],
            excerpt=spec["excerpt"],
            status="draft",
        )
        if status == "publish":
            await wp.publish(pid)
        ids.append(pid)
```

- WP_MOCK=true → 9개 posts가 SQLite에 저장 (K 데모: WP #65-70 cluster)
- WP_MOCK=false → 9개 posts가 실 WP에 publish

---

## 10. 1차 출처 (전체)

### WordPress REST API
- [WordPress REST API 공식 핸드북](https://developer.wordpress.org/rest-api/)
- [WordPress REST API Authentication](https://developer.wordpress.org/rest-api/authentication/) — Application Password
- [Application Passwords Integration Guide (make.wordpress.org)](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/) — HTTPS only

### wp-auto 구현
- [`wp_auto/wp/real_client.py` (GitHub)](https://github.com/wheeljah/wp-auto/blob/main/wp_auto/wp/real_client.py) — Real REST API client
- [`wp_auto/wp/factory.py` (GitHub)](https://github.com/wheeljah/wp-auto/blob/main/wp_auto/wp/factory.py) — .env 기반 Mock/Real 자동 전환
- [`wp_auto/cli/main.py` `_load_dotenv()`](https://github.com/wheeljah/wp-auto/blob/main/wp_auto/cli/main.py) — .env 자동 로드

### 시연/테스트
- [oneoff_chunked_k_affiliate.py (GitHub)](https://github.com/wheeljah/wp-auto/blob/main/oneoff_chunked_k_affiliate.py) — v0.8 K 데모 (Amazon affiliate, JSON-LD)
- [oneoff_demo_l_input_v9.py (GitHub)](https://github.com/wheeljah/wp-auto/blob/main/oneoff_demo_l_input_v9.py) — v0.9 L 데모 (URL/markdown 입력)

### 관련 가이드
- [monetization_blog_plan.md](./monetization_blog_plan.md) — 워드프레스 수익화 블로그 1차 출처 기반 코딩계획서
- [wp_admin_generatepress_setup.md](./wp_admin_generatepress_setup.md) — WP Admin GeneratePress 설치 가이드
- [affiliate_marketing_setup.md](./affiliate_marketing_setup.md) — 제휴마케팅 워드프레스 셀프호스팅 스택
