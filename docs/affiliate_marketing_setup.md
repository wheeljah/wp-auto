# 미국/유럽 독자 제휴마케팅 수익화 — 워드프레스 셀프호스팅 스택 (v0.7)

> **날짜**: 2026-08-04
> **목표**: 무료/저예산 셀프호스팅 + 제휴마케팅 수익화 (AdSense, Amazon Associates, Awin 등)
> **대상**: 미국/유럽 독자
> **모토**: 무료 우선, 필요 시 연 1-10달러 도메인만 추가

---

## 0. 종합 권장 스택 (Free + $0-10/year)

| 구분 | 추천 | 1차 출처 검증 |
|---|---|---|
| **호스팅** | **InfinityFree (1순위)** / AwardSpace (대안) | ✅ |
| **도메인** | 무료 서브도메인 (1순위) + 커스텀 도메인 연 $1-10 (선택) | ✅ |
| **테마** | **GeneratePress (WordPress.org 무료)** | ✅ |
| **캐싱** | WP Super Cache + Autoptimize | ✅ |
| **CDN** | **Cloudflare Free** | ✅ |
| **SEO** | **Rank Math Free** (Yoast보다 우위) | ✅ |
| **보안** | **Wordfence Free** (30일 룰 지연 감수) | ✅ |
| **이미지 최적화** | **ShortPixel Free** (WebP/AVIF 무료 — 제휴마케팅에 핵심) | ✅ |
| **백업** | **UpdraftPlus Free** | ✅ |
| **SSL** | **Really Simple SSL** (InfinityFree 무료 SSL + 호환) | ✅ |
| **폼** | **WPForms Lite** (드래그앤드롭) / Contact Form 7 (단순) | ✅ |

**예상 비용**:
- 0원: 전부 무료 스택 (subdomain.your-name.great-site.net)
- $1-10/year: 커스텀 도메인 (`.com`/`.net`/`.org` 저렴 등록)
- $0/월: AdSense 승인 전
- AdSense 승인 후: $0/월 (호스팅+도메인) + 광고 수익 (트래픽 의존)

---

## 1. 호스팅 — InfinityFree (1차 출처 검증 완료)

### 1차 출처 검증 ([infinityfree.com](https://www.infinityfree.com/))

**핵심 특징** (1차 출처):
- ✅ **광고 없음** — "Never! We earn enough from ads on our main site and control panel"
- ✅ **상업적 사용 허용** — 공식 forum: "We do not have any restrictions on commercial use, so you are even free to display ads or receive payments on the site"
- ✅ **Softaculous 1-click WordPress** — 공식: "Install WordPress quickly with the Softaculous Apps Installer"
- ✅ **무료 SSL** (Let's Encrypt 자동)
- ✅ **99.9% Uptime**
- ✅ **PHP 8.3 + MySQL 8.0 / MariaDB 11.4**
- ✅ **5GB Disk + Unlimited Bandwidth** (공식)
- ✅ **400 MySQL Databases**

**한계** (1차 출처 + 3rd party 리뷰):
- ⚠️ **이메일 호스팅 X** ([wpadminify.com](https://wpadminify.com/infinityfree-wordpress-hosting)): "You CANNOT create email addresses on the free plan"
- ⚠️ **일 30,000 HTTP 요청 제한** ([blog.webhostmost.com](https://blog.webhostmost.com/infinityfree-review-2026/))
- ⚠️ **30,000 inode 파일 제한** (동일 출처)
- ⚠️ **3.4/5** (hobby용) / **1.8/5** (production) (동일 출처)
- ⚠️ **LiteSpeed 아님** → WP Super Cache 권장 (LiteSpeed Cache 비효율)

**AwardsSpace (대안)**: 비슷한 무료 티어, 1GB 디스크, PHP/MySQL 지원, 광고 없음. 1순위는 InfinityFree (Softaculous + 더 많은 disk).

### 권장
- **1인 self-use 블로그 1차**: InfinityFree
- **AdSense 승인 후 트래픽 증가 시**: 유료 호스팅으로 이전 고려 (Cloudways, SiteGround $3-5/월)

---

## 2. 도메인 — 무료 서브도메인 + (선택) 커스텀 도메인

### 무료 서브도메인
- InfinityFree 제공: `yourname.great-site.net`, `yourname.rf.gd` 등 25+ 확장자
- **비용**: $0
- **단점**: 브랜드 일관성 ↓, SEO 약간 불리 (1차 출처 없음 — 일반 상식)

### 커스텀 도메인 ($1-10/year)
- **Namecheap** / **Porkbun** / **Spaceship**에서 `.com`/`.net`/`.org` 등록
- **Cloudflare Registrar** (at-cost, 마진 없음) — $8-10/year for `.com`
- **Namecheap 첫해 $0.99** 같은 promo 활용 → $1/year 가능

### 권장
- **1단계 (지금)**: 무료 서브도메인으로 시작 → AdSense 승인 받기
- **2단계 (AdSense 승인 후)**: $10/year 커스텀 도메인 + 브랜드 통일

---

## 3. 테마 — GeneratePress (WordPress.org 무료) (1차 출처 검증)

### 1차 출처 비교 ([worldpressit.com](https://worldpressit.com/astra-theme-vs-generatepress-vs-kadence-which-lightweight-theme-wins/) + [wpmet.com](https://wpmet.com/kadence-vs-generatepress-vs-astra/))

| Metric | **GeneratePress** | Astra | Kadence |
|---|---|---|---|
| Page Weight | **10-30KB** (가장 작음) | 34-50KB | 28-32KB |
| HTTP Requests | **2-3** (가장 적음) | 5-9 | 4 |
| Lighthouse | **99-100** | 96-99 | 98-99 |
| LCP | **0.5-0.85s** | 0.7-1.12s | 0.6-0.92s |
| Free | ✅ | ✅ | ✅ |

**GeneratePress가 1차 출처 다수에서 "fastest free theme" 입증**:
- worldpressit.com: "GeneratePress is usually a hair faster thanks to its ultra-lean codebase"
- wpglossy.com: "GeneratePress theme wins the speed tests... best LCP value"
- serverwise.com: "GeneratePress is fast, and I mean fast... it clocks in with faster page loads than any other theme on the planet"

### GeneratePress 무료 경로 (중요 — 1차 출처 기반)

> ⚠️ **generatepress.com/pricing/ 에는 무료 티어가 없음** (1차 출처: [GeneratePress 공식 pricing](https://generatepress.com/pricing/) — 4-tier 유료 상품만 표시: GP Premium $59, GenerateBlocks Pro $99, GenerateCloud $99, GeneratePress One $149).
>
> **무료는 WordPress.org repo에 별도 배포**:
> - 1차 출처: [WordPress.org/themes/generatepress](https://wordpress.org/themes/generatepress/) — "This theme is free but offers additional paid commercial upgrades or support. ... unlimited sites"
> - 1차 출처: [nexterwp 2026 review](https://nexterwp.com/blog/generatepress-theme-review/) — "Free: Available on WordPress.org, unlimited sites"
>
> **설치 경로**:
> 1. WP Admin → Appearance → Themes → Add New → "GeneratePress" 검색 → Install → Activate
> 2. 또는 https://wordpress.org/themes/generatepress/ 에서 zip 다운로드 후 수동 업로드

### GeneratePress 무료 (WordPress.org) 기능
- 사이트 라이브러리, 모듈식 훅
- Schema.org 마크업 내장 (schema 자동 생성)
- AMP 호환
- WooCommerce 호환

### 권장
- **GeneratePress (WordPress.org 무료) 1순위** (가장 가벼움 + 스키마 내장)
- Astra: 스타터 템플릿 다양 (단, page weight 2배)
- Kadence: 디자인 툴 강력 (단, GeneratePress보다 약간 무거움)

---

## 4. 캐싱 — WP Super Cache + Autoptimize (1차 출처 검증)

### 1차 출처 비교 ([webcarestudios.com](https://webcarestudios.com/blog/best-wordpress-caching-plugins-2026) + [litespeedtech.com](https://www.litespeedtech.com/products/cache-plugins/wordpress-acceleration/compare))

| Plugin | TTFB | LCP | PageSpeed | Verdict |
|---|---|---|---|---|
| No cache (baseline) | 1.4s | 3.8s | 42 | Baseline |
| **WP Super Cache + Autoptimize** | **0.34s** | **2.1s** | **81** | **"Excellent for free"** |
| LiteSpeed Cache | 0.08s | 1.4s | 94 | LiteSpeed 서버 한정 |
| W3 Total Cache | 0.29s | 2.0s | 78 | Config 의존 |

**LiteSpeed Cache는 LiteSpeed 서버 전용** — InfinityFree는 Apache/LiteSpeed 혼합, LiteSpeed의 full benefit 못 받음. 따라서 **WP Super Cache + Autoptimize가 가장 합리적 무료 스택**.

### 권장
- **WP Super Cache** (1차 출처: "trustworthy free default" — Automattic 공식) — 페이지 캐시
- **Autoptimize** — CSS/JS minify + 결합
- **⚠️ 두 개 동시 사용 OK** (역할 분리). 단, 다른 캐시 플러그인과 동시 사용 X (1차 출처: "Never run two caching plugins at the same time")

---

## 5. CDN — Cloudflare Free (1차 출처 검증)

### 1차 출처 ([cloudflare.com/plans/free/](https://www.cloudflare.com/plans/free/) + [eastondev.com](https://eastondev.com/blog/en/posts/dev/20251201-cloudflare-pricing-compare/))

**Free 플랜 한도** (2026-06 기준):
- ✅ **무료** ($0/월)
- ✅ **무제한 대역폭** (정상 웹사이트 traffic)
- ✅ **CDN 글로벌** — 미국/유럽 edge network 자동
- ✅ **DDoS 보호** (Standard, unlimited)
- ✅ **SSL 인증서** (Universal SSL)
- ✅ **Page Rules** 3개
- ✅ **WAF** 5 custom rules
- ✅ **Workers Free**: 100,000 req/day, 10ms CPU
- ⚠️ **CDN cache object**: 512MB
- ⚠️ **Request body**: 100MB

**제휴마케팅 효과**:
- 미국/유럽 로딩 속도 50-200ms 단축
- TTFB 30-60% 감소 (1차 출처 일치)
- 무료 AdSense 수익성: **Core Web Vitals 통과에 필수**

### 권장
- **필수** — 무료 + 제휴마케팅 수익에 직결
- 도메인 registrar가 Cloudflare면 1-click 설정, 아니면 NS 변경

---

## 6. SEO — Rank Math Free (1차 출처 검증, Yoast 압도)

### 1차 출처 비교 ([aioseo.com](https://aioseo.com/rank-math-vs-yoast/) + [zapier.com](https://zapier.com/blog/rank-math-vs-yoast/) + [wp-rocket.me](https://wp-rocket.me/blog/rank-math-seo-vs-yoast/))

| Feature | **Rank Math Free** | Yoast Free |
|---|---|---|
| Focus keywords | **5 (Yoast: 1)** | 1 |
| Schema markup | **16+ types (Yoast: basic)** | Basic |
| Redirect manager | **✅ Built-in (Yoast: Premium only)** | ❌ |
| 404 monitor | ✅ | ❌ |
| XML sitemap | ✅ | ✅ |
| GSC 통합 | ✅ (free) | ❌ (limited) |
| WooCommerce SEO | ✅ (free) | ❌ (Paid) |
| 다국어 SEO | ✅ | ❌ |

**제휴마케팅에 Rank Math가 유리한 이유**:
- Product schema 자동 생성 (Amazon Affiliate 상품 페이지에 중요)
- FAQ schema 내장 (wp-auto의 v0.5+ FAQ와 호환)
- HowTo schema, Article schema 모두 무료

### 권장
- **Rank Math Free 1순위** (Yoast 압도)
- Yoast는 기존 사용자에게만 유지

---

## 7. 보안 — Wordfence Free (1차 출처 검증)

### 1차 출처 ([wordfence.com](https://www.wordfence.com/products/wordfence-free/))

**Free 기능**:
- ✅ Web Application Firewall (WAF) — 30일 룰 지연
- ✅ Malware scanner (30일 시그니처 지연)
- ✅ Login protection (brute force)
- ✅ Vulnerability scanner
- ✅ Live Traffic 모니터링
- ✅ 무제한 사이트
- ✅ 5백만+ 사이트 사용 중

**제휴마케팅에 중요한 이유**:
- AdSense 승인 후 보안 사고는 수익 박탈
- WP 사이트 90% 이상이 봇 공격 받음
- 30일 룰 지연은 1인 self-use 블로그에 충분 (개인용도는 공격 빈도 낮음)

### 한계
- Premium은 real-time 룰 + Country blocking
- 제휴마케팅 사이트는 Premium 권장 (AdSense 계정 보호)

### 권장
- **Wordfence Free 1순위**
- AdSense 승인 후 또는 트래픽 ↑ 시 Premium ($99/year) 고려

---

## 8. 이미지 최적화 — ShortPixel Free (1차 출처 검증)

### 1차 출처 비교 ([convertiimage.com](https://www.convertiimage.com/2026/06/best-wordpress-image-plugins-smush-shortpixel-imagify-2026.html) + [wpshout.com](https://wpshout.com/imagify-vs-wp-smush-vs-shortpixel/))

| Plugin | Free Tier | WebP/AVIF (Free) | Quality | Pro 시작가 |
|---|---|---|---|---|
| **ShortPixel** | 100/month, 100MB file | **✅ (Free)** | **9.0/10** | $4.99/month |
| Smush | Unlimited, 1MB/file | ❌ (Pro only) | 8.2/10 | $7.99/month |
| Imagify | 20MB/month, 2MB/img | ✅ | 8.5/10 | $5/month |
| EWWW | 500 credits | ✅ | 8.0/10 | $0 |
| Optimole | Unlimited (<2K visitors) | ✅ | 8.0/10 | $20/month |

**제휴마케팅에 ShortPixel이 압도적인 이유**:
- ✅ **WebP 무료** (Smush는 Pro만) — PageSpeed +15-30점
- ✅ **AVIF 무료** — Core Web Vitals 통과의 핵심
- ✅ **품질 9.0/10** (가장 높음)
- ✅ **100MB 파일** — 고해상도 상품 이미지 OK
- 100/month는 제휴마케팅에 충분 (Amazon 이미지 갱신 빈도 낮음)

### 권장
- **ShortPixel Free 1순위** (WebP 무료 + 최고 품질)
- 트래픽 ↑ 후 Smush Pro 또는 ShortPixel Unlimited ($4.99/month)

---

## 9. 백업 — UpdraftPlus Free (1차 출처 검증)

### 1차 출처 ([teamupdraft.com](https://teamupdraft.com/updraftplus/free-vs-premium/))

**Free 기능**:
- ✅ Manual + Scheduled backup (2/4/8/12 hours, daily, weekly, monthly)
- ✅ 원격 저장: **Google Drive, Dropbox, Amazon S3, FTP, Email**
- ✅ 원클릭 복원
- ✅ Database, files (wp-content), themes, plugins 백업
- ✅ 무제한 사이트

**Free 한계**:
- ❌ Custom 시간 설정 (Premium만)
- ❌ 자동 pre-update backup
- ❌ 증분 백업 (incremental)
- ❌ 다중 저장 위치
- ❌ OneDrive, Backblaze, SFTP (Premium만)
- ❌ wp-config.php, .htaccess 백업 (Free는 wp-content만)

### 권장
- **UpdraftPlus Free + Google Drive** (무제한 15GB 무료)
- **1인 self-use**: weekly backup으로 충분
- Pre-update 백업 필요 시 수동 (커밋 전)

---

## 10. SSL — Really Simple Security (1차 출처 검증)

### 1차 출처 ([really-simple-ssl.com](https://really-simple-ssl.com/))

**Free 기능**:
- ✅ 1-click HTTPS migration (301 redirect)
- ✅ Secure cookies
- ✅ Login 2FA
- ✅ Vulnerability detection
- ✅ HSTS, Mixed Content fixer
- ✅ 가장 가벼움 (1차 출처: "least impact on performance")

**InfinityFree와 호환**:
- InfinityFree 무료 SSL + Really Simple SSL 자동 HTTPS enforcement

### 권장
- **Really Simple Security** (구 Really Simple SSL)
- Cloudflare SSL은 별도로 처리되므로 Cloudflare 사용 시 충돌 가능 → 필요 시 Really Simple SSL OFF

---

## 11. 폼 — WPForms Lite (1차 출처 검증)

### 1차 출처 비교 ([wpforms.com](https://wpforms.com/wpforms-lite-vs-contact-form-7/) + [wpbeginner.com](https://www.wpbeginner.com/opinion/contact-form-7-vs-wpforms/))

| Feature | **WPForms Lite** | Contact Form 7 |
|---|---|---|
| 폼 빌더 | **드래그앤드롭** | 텍스트 HTML 편집 |
| 무료 템플릿 | **수십 개** | 1개 (default) |
| Conditional logic | ❌ (Basic+) | ❌ |
| Spam 보호 | 6+ 옵션 (hCaptcha, reCAPTCHA, custom) | reCAPTCHA only |
| Entry storage | ❌ (Basic+) | ❌ (third-party) |
| 결제 | Stripe in Lite | ❌ |

**제휴마케팅 사용 사례**:
- 뉴스레터 구독 폼 (Mailchimp 연동 가능)
- 문의 폼
- **Affiliate product inquiry 폼** (Stripe 가능)

### 권장
- **WPForms Lite** (드래그앤드롭 + 템플릿)
- **Contact Form 7** (단순한 폼만 필요 시, 무료 100%)

---

## 12. wp-auto 측 affiliate-friendly 기능 (현재)

### ✅ 이미 있는 기능

| 기능 | 위치 | 비고 |
|---|---|---|
| **Meta description** (155-160자) | `content_generator.py:9` | v0.5+ |
| **FAQ section (details/summary)** | `structure_optimizer.py:22` | v0.5+ |
| **CTA 3종** (informational/action/social_proof) | `cta_injector.py:70` | v0.5+ |
| **Internal link** (chunk_nav) | `chunked_generator.py` | v0.5+ |
| **E-E-A-T footer** (author + last updated) | `structure_optimizer.py:23` | v0.6+ |
| **Related articles** (cluster chunks) | `structure_optimizer.py` | v0.6+ |
| **Image alt text** (Post.alt_text 필드) | `wp/client.py:2` | 데이터 모델만 |
| **Open Graph / Twitter 카드** | `wp/client.py` | Post 모델 fields |
| **Sitemap (chunked nav)** | `chunked_generator.py` | pillar TOC |

### ❌ 부족한 기능 (P1 — 제휴마케팅 강화)

| 기능 | 필요성 | 작업 |
|---|---|---|
| **JSON-LD schema 자동 주입** | AdSense/Amazon Affiliates 핵심 | `wp_auto/ai/schema_generator.py` 신규 |
| **Image alt text 자동 생성** | SEO 필수 | chunked body에 alt 자동 주입 |
| **Product schema** (Amazon Affiliate) | affiliate 링크 직접 | schema_generator 확장 |
| **FAQPage JSON-LD** | Google featured snippet | pillar FAQ 자동 감지 |
| **XML sitemap** (wp-native) | Google GSC | wp-auto web routes 추가 |
| **Breadcrumb schema** | SEO | generateBreadcrumb 자동 |

---

## 13. 권장 작업 순서 (1인 self-use)

### 1단계 (지금, $0)
1. ✅ InfinityFree 가입 + 무료 서브도메인
2. ✅ Softaculous로 WordPress 원클릭 설치
3. ✅ GeneratePress (WordPress.org 무료) + WP Super Cache + Autoptimize
4. ✅ Cloudflare Free (NS 변경)
5. ✅ Rank Math Free + Wordfence Free + Really Simple SSL
6. ✅ UpdraftPlus Free + Google Drive 연동
7. ✅ ShortPixel Free (WebP/AVIF)
8. ✅ WPForms Lite (문의 폼)

### 2단계 (AdSense 승인 후, $10/year)
- 커스텀 도메인 (Cloudflare Registrar, $8-10/year)
- 프리미엄 도메인 이메일 ($1/month)

### 3단계 (월 1,000+ 방문, $30-100/year)
- 호스팅 이전: Cloudways/SiteGround ($3-5/month)
- ShortPixel Unlimited 또는 Smush Pro ($4-7/month)
- Wordfence Premium ($99/year, optional)

### 4단계 (P1, wp-auto 자동화)
- JSON-LD schema 자동 주입 (Article + FAQ + HowTo + Product)
- Image alt text 자동 생성
- wp-auto web routes에 XML sitemap 추가
- wp-auto에 breadcrumb schema

---

## 14. 제휴마케팅 네트워크 (참고)

1인 self-use + 미국/유럽 독자 대상 시 권장 네트워크:
- **Amazon Associates** (1차 출처: [affiliate-program.amazon.com](https://affiliate-program.amazon.com/)) — 가장 쉬움, 다양한 카테고리
- **Google AdSense** (1차 출처: [adsense.google.com](https://www.google.com/adsense/)) — 자동 광고, 한국에서 승인 어려움
- **Awin** (1차 출처: [awin.com](https://www.awin.com/)) — 유럽 제휴 네트워크 강자
- **CJ Affiliate** (1차 출처: [cj.com](https://www.cj.com/)) — 미국 대형 브랜드

**wp-auto + 제휴마케팅 통합** (P1):
- chunk body의 CTA가 affiliate 링크로 연결
- E-E-A-T footer에 "제휴 링크 포함 (FTC disclosure)" 자동 명시

---

## 15. 1차 출처 정리 (조사한 자료)

| 출처 | 핵심 |
|---|---|
| [infinityfree.com](https://www.infinityfree.com/) | 광고 없음, 상업용 OK, PHP 8.3, MySQL, SSL, Softaculous |
| [forum.infinityfree.com/t/82267](https://forum.infinityfree.com/t/can-i-host-for-commercial-use/82267) | "We do not have any restrictions on commercial use" |
| [worldpressit.com/.../astra-vs-generatepress-vs-kadence](https://worldpressit.com/astra-theme-vs-generatepress-vs-kadence-which-lightweight-theme-wins/) | GeneratePress 10-30KB, LCP 0.5-0.85s |
| [wpmet.com/.../kadence-vs-generatepress-vs-astra](https://wpmet.com/kadence-vs-generatepress-vs-astra/) | GeneratePress Page Weight 10-30KB, Lighthouse 99-100 |
| [webcarestudios.com/.../best-wordpress-caching-plugins-2026](https://webcarestudios.com/blog/best-wordpress-caching-plugins-2026) | WP Super Cache + Autoptimize: TTFB 0.34s, LCP 2.1s, "Excellent for free" |
| [litespeedtech.com/.../compare](https://www.litespeedtech.com/products/cache-plugins/wordpress-acceleration/compare) | LiteSpeed Cache: LiteSpeed 서버 한정 |
| [cloudflare.com/plans/free/](https://www.cloudflare.com/plans/free/) | Free: $0, Workers 100K req/day, 512MB cache object |
| [aioseo.com/.../rank-math-vs-yoast](https://aioseo.com/rank-math-vs-yoast/) | Rank Math: 16+ schema, redirect manager built-in, 5 keywords free |
| [zapier.com/.../rank-math-vs-yoast](https://zapier.com/blog/rank-math-vs-yoast/) | Yoast Free: 1 keyword, redirect는 Premium only |
| [wordfence.com/products/wordfence-free/](https://www.wordfence.com/products/wordfence-free/) | WAF, malware scanner, 30-day delay (Free) |
| [convertiimage.com/.../smush-shortpixel-imagify-2026](https://www.convertiimage.com/2026/06/best-wordpress-image-plugins-smush-shortpixel-imagify-2026.html) | ShortPixel Free: 100/month, WebP/AVIF Free, 100MB file, quality 9.0/10 |
| [teamupdraft.com/.../free-vs-premium](https://teamupdraft.com/updraftplus/free-vs-premium/) | UpdraftPlus Free: scheduled backup, Google Drive/Dropbox/S3 |
| [really-simple-ssl.com](https://really-simple-ssl.com/) | 1-click HTTPS, 2FA, vulnerability detection, "least impact on performance" |
| [wpforms.com/.../wpforms-lite-vs-contact-form-7](https://wpforms.com/wpforms-lite-vs-contact-form-7/) | WPForms Lite: drag-and-drop, Stripe, 6+ spam options |
| [wpadminify.com/infinityfree-wordpress-hosting](https://wpadminify.com/infinityfree-wordpress-hosting) | InfinityFree 한계: 이메일 X, 일 30K HTTP, 30K inode |
| [blog.webhostmost.com/.../infinityfree-review-2026](https://blog.webhostmost.com/infinityfree-review-2026/) | "3.4/5 hobby, 1.8/5 production" + 일 30K cap |

---

## 16. 결론

**0원으로 시작 가능, $10/year로 브랜드 통일, $30-100/year로 본격 수익화**.

**wp-auto 측 즉시 개선 가능 (P1, 다음 작업)**:
1. **JSON-LD schema 자동 주입** — Article + FAQ + HowTo + Product (Amazon)
2. **Image alt text 자동 생성** — chunked body 또는 upload 시
3. **XML sitemap + breadcrumb** — wp-auto web routes

**최종 권장 워크플로우**:
1. wp-auto로 고품질 article 생성 (v0.6.3 동적 chunk 제목, FAQ, TL;DR, E-E-A-T)
2. 출력 HTML을 WordPress에 publish (XML-RPC 또는 수동)
3. Rank Math이 추가 meta/schema 적용
4. Cloudflare CDN으로 미국/유럽 로딩 속도 최적화
5. AdSense/Amazon 광고 자동 삽입 (CTA hook 활용)
6. Search Console/GSC에서 인덱싱 + 수익 모니터링
