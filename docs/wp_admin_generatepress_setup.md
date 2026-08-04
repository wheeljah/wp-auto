# WP Admin GeneratePress 설치 가이드 (1인 self-use, 2026)

> 작성일: 2026-08-04
> 대상: 1인 self-use 워드프레스 운영자 (InfinityFree + 무료 스택)
> 모든 단계 1차 출처 기반

---

## 0. 시작 전 짚을 점

| 항목 | 위치 | 비고 |
|---|---|---|
| **GeneratePress (무료)** | **Appearance → Themes → Add New** | Theme 메뉴에서 설치 |
| GeneratePress Premium ($59/year) | Plugins → Add New → Upload Plugin | ZIP 직접 업로드, 유료 |
| **무료 보조 Plugin 7종** | Plugins → Add New → 검색 | Rank Math, WP Super Cache 등 |

> ⚠️ Softaculous로 WP 설치 시 기본 테마(예: Twenty Twenty-Five)가 활성화되어 있을 텐데, **그대로 두고** GeneratePress 활성화 시 자동 전환. 삭제 ❌, 비활성화만.

---

## 1. WP Admin 로그인 (1분)

### 1.1 URL

```
https://yoursite.epizy.com/wp-admin
```

> `yoursite.epizy.com`은 InfinityFree 가입 시 발급한 무료 서브도메인.

### 1.2 로그인 정보

- **Username**: Softaculous 설치 시 입력한 admin 이름 (`admin` ❌, 별도 이름 사용 권장)
- **Password**: 같은 시 입력한 비밀번호

> **로그인 안 될 때**:
> - InfinityFree Client Area → Account → Control Panel → Softaculous → 설치된 WP 옆 **🔑** 아이콘 (비밀번호 재설정)

### 1.3 첫 로그인 직후 화면

좌측 사이드바 메뉴:
- **Dashboard** (홈) / **Posts** (글) / **Media** (이미지) / **Pages** (페이지)
- **Comments** (댓글) / **Appearance** (테마) / **Plugins** (플러그인)
- **Users** / **Tools** / **Settings**

> 1차 출처: [Learn WordPress 공식 (Automattic)](https://learn.wordpress.org/lesson-plan/choosing-and-installing-themes/) — "Head over to Appearance -> Themes -> Add New"

---

## 2. WP 기본 설정 (3분, GeneratePress 설치 전 먼저!)

### 2.1 사이트 제목/태그라인

1. 좌측 **Settings → General**
2. **Site Title**: `워드프레스 수익화 블로그` (또는 본인 niche)
3. **Tagline**: `1인 운영, 무료로 시작하는 제휴마케팅 가이드` (140자 이내)
4. **Timezone**: `Asia/Seoul` (UTC+9, 운영자 기준 1차 출처)
5. **Date Format**: `Custom: F j, Y` (예: "August 4, 2026", 1차 출처: Bluehost 가이드)
6. **Time Format**: `g:i a` (예: "2:30 pm")
7. **Week Starts On**: `Monday`
8. **Save Changes**

> 1차 출처:
> - [Bluehost — Change WordPress Timezone](https://www.bluehost.com/blog/time-zone-adjustment/) — "For US audiences, formats like March 10, 2026 or 3/10/2026 are commonly used. For international audiences, formats such as 10 March 2026 or 10/03/2026 are often preferred."
> - [flexahosting — Timezone](https://flexahosting.nl/en/hosting/How-do-you-ensure-that-the-language-and-time-zone-in-WordPress-match-your-target-group-and-reports/) — "Set the timezone to your target audience's location."

### 2.2 Permalink (SEO 핵심!)

1. 좌측 **Settings → Permalinks**
2. **Post name** 선택 (예: `https://yoursite.com/best-usb-c-charger-2026/`)
   - ❌ `Plain` (`?p=123`) — SEO 불리
   - ❌ `Day and name` — 너무 길음
   - ✅ **Post name** — SEO 권장
3. **Save Changes**

### 2.3 Reading

1. **Settings → Reading**
2. **Your homepage displays**: **Your latest posts** (블로그 기본)
3. **Save Changes**

### 2.4 Discussion (댓글)

1. **Settings → Discussion**
2. ✅ **Allow comments** + ✅ **Comment must be manually approved** (스팸 방지)
3. **Save Changes**

---

## 3. GeneratePress (WordPress.org 무료) 설치 (2분)

### 3.1 단계 (1차 출처: [GeneratePress 공식 가이드](https://docs.generatepress.com/article/installing-generatepress/))

> 1차 출처 원문: "First, login to your WordPress Dashboard. Next, go to 'Appearance > Themes' in the menu on the left. Near the top, you'll see a 'Add New' button, click that button. In the 'Search themes' bar, type: generatepress. You'll see GeneratePress and some of our child themes appear. Click 'Install', and then activate."

**Step-by-step**:

1. 좌측 사이드바 → **Appearance** (마우스 hover)
2. 서브메뉴 → **Themes** 클릭
3. 상단 **Add New** 버튼 클릭
4. 우측 상단 **Search themes** 검색창에 `generatepress` 입력
5. 검색 결과에서 **GeneratePress** 찾기
   - ⚠️ **중요**: 개발자 이름이 **Tom Usborne** 인지 확인 (정품 마커, 1차 출처: [serveravatar 가이드](https://serveravatar.com/generatepress-theme-install-wordpress/))
6. **Install** 버튼 클릭 (10-30초)
7. 설치 완료 → 버튼이 **Activate**로 바뀜
8. **Activate** 클릭
9. 잠시 후 자동 화면 전환 → **GeneratePress가 활성 테마로 표시**

> **검증**: Appearance → Themes 페이지로 다시 가서 첫 번째 칸에 **GeneratePress** + "Active" 라벨 확인.

### 3.2 Customize 진입

1. Appearance → **Customize** (또는 상단 바의 "Customize" 버튼)
2. 좌측 Customizer 패널:
   - **Site Identity**: 로고, 사이트 제목, 태그라인, 파비콘
   - **Colors**: 배경/텍스트/링크 색상
   - **Typography**: 폰트 패밀리/크기
   - **Layout**: 컨테이너/사이드바/내비게이션 위치
   - **Menu**: 메뉴 구조 (나중에)
   - **Widgets**: 푸터/사이드바 위젯
   - **Homepage Settings**: 정적 페이지 여부

> ⚠️ **Customize는 Publish 눌러야 실제 저장.** X 누르면 미리보기만 보고 저장 안 됨.

### 3.3 GeneratePress 무료 기능 범위 (중요!)

> 1차 출처: [nexterwp 2026 review](https://nexterwp.com/blog/generatepress-theme-review/) — "The free theme gives you a minimal, accessible starting point. You get basic layout options (full-width, boxed, or contained content), a simple header with navigation, and a small set of Customizer controls for colors and typography."

**무료에 포함된 것** ✅:
- 기본 layout (full-width / boxed / contained)
- Customizer 기본 컨트롤 (color, typography 일부)
- 기본 header + navigation
- 빠른 페이지 속도 (<10KB footprint)

**무료에 없는 것** ❌ (Premium $59/year 필요):
- 고급 typography (Google Fonts 전체)
- 전체 color palette
- Theme Builder (custom header/footer)
- Conditional display rules
- Sticky Navigation, Off-Canvas Panel
- Site Library (60+ starter templates)
- WooCommerce 모듈

> 1인 self-use, 무료 시작 시: 무료 범위로 충분히 시작 가능.

---

## 4. 무료 보조 Plugin 7종 설치 (10분)

### 4.1 공통 설치 방법 (모든 Plugin 동일)

1. 좌측 **Plugins** → **Add New**
2. 우측 상단 **Search plugins** 검색창에 plugin 이름 입력
3. 검색 결과 → **Install Now** 클릭
4. **Activate** 클릭
5. 좌측 메뉴에 새 항목이 생김

### 4.2 Plugin 7종 (모두 무료)

| # | Plugin | 검색어 | 역할 | 설치 후 설정 |
|---|---|---|---|---|
| 1 | **Rank Math SEO** | `rank math seo` | Schema, sitemap, on-page | Wizard 자동 실행 |
| 2 | **WP Super Cache** | `wp super cache` | 페이지 캐싱 (LCP 개선) | Settings → Enable |
| 3 | **ShortPixel Image Optimizer** | `shortpixel` | 이미지 WebP (월 100장 무료) | API key 필요 |
| 4 | **UpdraftPlus** | `updraftplus` | 자동 백업 | 수동 백업 설정 |
| 5 | **Wordfence Security** | `wordfence` | 방화벽 + malware 스캔 | Default 활성 OK |
| 6 | **WPForms Lite** | `wpforms lite` | Contact form | 기본 form 1개 |
| 7 | **Really Simple SSL** | `really simple ssl` | HTTPS 강제 redirect | Activate → 1-click |

### 4.3 Rank Math Wizard (3분, 가장 중요)

1. Plugins → Add New → `rank math seo` → Install → Activate
2. 좌측 **Rank Math SEO → Dashboard** → Setup Wizard 자동 시작
3. 단계별:
   - **Account**: Skip (무료 tier)
   - **Site Type**: `Blog`
   - **Search Console**: Skip (나중에)
   - **SEO Settings**: Title/Description separator = `–` (dash)
   - **Sitemap**: Posts + Pages + Products 모두 ON
   - **Ready**: Finish

### 4.4 WP Super Cache (1분)

1. Plugins → Add New → `wp super cache` → Install → Activate
2. **Settings → WP Super Cache**
3. **Caching On (Recommended)** 선택 → **Save Changes**
4. **Advanced** 탭 → "Compress pages" 체크 → **Update Status**

### 4.5 ShortPixel API key (3분)

1. https://shortpixel.com/otp-api 접속 (또는 shortpixel.com → Free API)
2. Email 입력 → API key 받기 (이메일)
3. WordPress → **Settings → ShortPixel** → API key 입력
4. **Save and Validate**

> ⚠️ **API key는 별도 가입 필요** — InfinityFree 가입과 무관. 이메일 인증 한 번.

### 4.6 Wordfence (1분)

1. Plugins → Add New → `wordfence` → Install → Activate
2. **Wordfence → Firewall** → Default 활성 OK
3. **Wordfence → Scan** → "Start a Wordfence Scan" (선택)

### 4.7 WPForms Lite (1분)

1. Plugins → Add New → `wpforms lite` → Install → Activate
2. **WPForms → Add New**
3. 템플릿: **Simple Contact Form** 선택
4. Form Name: `Contact` → Embed → 새 Page 만들거나 기존 Page 선택 → **Publish**

### 4.8 Really Simple SSL (1분)

1. Plugins → Add New → `really simple ssl` → Install → Activate
2. **Go ahead, activate SSL** 클릭
3. 모든 HTTP → HTTPS 자동 redirect

### 4.9 (선택) Code Snippets — wp-auto Visitor Timezone용

> 1차 출처: [WordPress.org Code Snippets](https://wordpress.org/plugins/code-snippets/) — 가벼운 code injection plugin

1. Plugins → Add New → `code snippets` → Install → Activate
2. **Snippets → Add New**
3. **Title**: `wp-auto Visitor Timezone (옵션 C)`
4. **Code** 영역에 `wp_auto/integrations/visitor_timezone.js` 내용 붙여넣기
   - 파일 위치: `D:\Google_blog\wp-auto\wp_auto\integrations\visitor_timezone.js`
5. **Run everywhere** 체크
6. **Save and Activate**

> 옵션 C: Post published time을 visitor의 로컬 timezone으로 자동 변환. SEO 영향 0, GDPR 친화 (외부 API/cookie 없음).
> 1차 출처: [webmasters stackexchange](https://webmasters.stackexchange.com/questions/131211/does-server-timezone-affect-seo) — "Major search engines don't care."

---

## 5. 첫 글 작성 (테스트, 5분)

### 5.1 새 글

1. 좌측 **Posts → Add New**
2. 화면:
   - **Title**: `워드프레스 시작 — 첫 글입니다` (테스트)
   - **본문**: 본문 영역 클릭 → 텍스트 입력
   - **Permalink**: `first-post` 또는 자동
3. 우측 **Document → Categories**: 첫 category 만들기 (예: `테스트`)
4. 우측 **Document → Tags**: `테스트` (선택)
5. 우측 **Rank Math SEO** → Focus Keyword = `워드프레스` (테스트)
6. **Publish** 클릭 (우상단 파란 버튼)

### 5.2 확인

1. 새 탭 → `https://yoursite.epizy.com/first-post/`
2. GeneratePress 테마로 정상 표시 확인
3. 모바일 뷰포트 확인 (F12 → 모바일 아이콘)
4. **Visitor Timezone Snippet 활성화 시** post date 옆 시간 = visitor 로컬 시간

### 5.3 첫 글 휴지통 (테스트 후)

1. Posts → All Posts
2. 테스트 글 hover → **Trash** 클릭
3. 영구 삭제 = Trash → Empty Trash

---

## 6. 점검 체크리스트

설치 후 다음이 모두 OK 인지 확인:

- [ ] Appearance → Themes → 첫 번째가 GeneratePress + "Active" 라벨
- [ ] Plugins → 8개 활성 (Code Snippets 포함 시 9개)
- [ ] Settings → Permalinks → Post name
- [ ] Settings → General → Timezone = Asia/Seoul, Date Format = `F j, Y`
- [ ] 사이트 URL = `https://` (SSL 강제 redirect)
- [ ] 모바일 정상 표시
- [ ] (옵션) Visitor timezone 변환 작동

---

## 7. 자주 겪는 함정 (1인 self-use 베스트)

### 7.1 "GeneratePress 검색이 안 나와요"

- **원인 1**: 검색어 오타 → 정확히 `generatepress` 한 단어
- **원인 2**: WP 버전 너무 낮음 → Settings → About WordPress → 6.5+ 확인
- **원인 3**: 한국어 검색 → 영어만 사용
- **원인 4**: 인터넷 차단 → Cloudflare 우회

### 7.2 "Install 후 화면이 깨져요"

- **원인**: `wp-admin/upgrade.php` 자동 실행 누락
- **해결**: `https://yoursite.epizy.com/wp-admin/upgrade.php` 한 번 방문

### 7.3 "Softaculous 설치 후 404 에러"

- **원인**: Permalink 설정 안 함 → Settings → Permalinks → Post name → Save

### 7.4 "Plugin이 inactive 상태로만 보임"

- **원인**: PHP 버전 비호환 (1차 출처: [InfinityFree 2026](https://blog.webhostmost.com/infinityfree-review-2026/) — PHP 8.3 지원 OK)
- **해결**: 대부분 문제 없음. 진짜 비호환이면 **Plugins → Add New → "health check"** → Health Check Plugin

### 7.5 "Customize 저장이 안 돼요"

- **원인 1**: SSL 인증서 만료 → InfinityFree Control Panel → Free SSL Certificates → 갱신
- **원인 2**: PHP 메모리 부족 → wp-config.php에 `define('WP_MEMORY_LIMIT', '256M');` (InfinityFree 한계로 안 될 수 있음)

---

## 8. 다음 단계

W2-W3 작업:

1. **About / Contact / Privacy Policy / Affiliate Disclosure 4개 필수 페이지 작성**
2. **Google Search Console 등록** (W3)
3. **wp-auto로 1세트 pillar 발행** (W3, [REST API 자동 업로드 가이드](./wordpress_api_auto_publish.md) 참고)
4. **CJ Affiliate / Amazon Associates 가입** (W3, 페이지 10-15개 발행 후)

---

## 9. 1차 출처 (전체)

### GeneratePress 설치
- [GeneratePress 공식 설치 가이드](https://docs.generatepress.com/article/installing-generatepress/)
- [serveravatar GeneratePress 가이드](https://serveravatar.com/generatepress-theme-install-wordpress/)
- [Learn WordPress 공식 (Automattic)](https://learn.wordpress.org/lesson-plan/choosing-and-installing-themes/)
- [WP Engine Support — Plugins & Themes](https://wpengine.com/support/manage-plugins-and-themes-manually/)

### WordPress.org GeneratePress
- [GeneratePress (WordPress.org)](https://wordpress.org/themes/generatepress/) — "This theme is free"
- [nexterwp 2026 review](https://nexterwp.com/blog/generatepress-theme-review/) — "Free: Available on WordPress.org, unlimited sites"

### Timezone / Date format
- [Bluehost — Change WordPress Timezone](https://www.bluehost.com/blog/time-zone-adjustment/) — city-based timezone, date format
- [flexahosting — Timezone & Language](https://flexahosting.nl/en/hosting/How-do-you-ensure-that-the-language-and-time-zone-in-WordPress-match-your-target-group-and-reports/)
- [WordPress.com — Language & Timezone](https://wordpress.com/support/set-your-sites-language-and-timezone/)
- [crowdfavorite — Times & Dates in WP](https://crowdfavorite.com/insights/managing-times-and-dates-in-wordpress/)

### SEO / Server timezone
- [webmasters stackexchange — Does server timezone affect SEO?](https://webmasters.stackexchange.com/questions/131211/does-server-timezone-affect-seo) — "No. Major search engines don't care."

### Plugin
- [WordPress.org Code Snippets](https://wordpress.org/plugins/code-snippets/) — 가벼운 code injection
