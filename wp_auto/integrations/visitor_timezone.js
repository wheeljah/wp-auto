/*!
 * wp-auto Visitor Timezone Snippet (옵션 C)
 * -----------------------------------------
 * Post published time을 visitor의 로컬 timezone으로 자동 변환.
 *
 * 1차 출처 (timezone 영향):
 *   - https://webmasters.stackexchange.com/questions/131211/does-server-timezone-affect-seo
 *     "Major search engines don't care. The location where the files actually reside is entirely irrelevant to SEO."
 *   - https://crowdfavorite.com/insights/managing-times-and-dates-in-wordpress/
 *     "When in the WordPress ecosystem, use WordPress's time functions as opposed to system time."
 *   - https://www.bluehost.com/blog/time-zone-adjustment/
 *     "Always select a city-based timezone (e.g., 'America/New_York') instead of a UTC offset.
 *      City-based timezones automatically adjust for daylight saving time changes."
 *
 * SEO 영향: 0 (서버 timezone 무관, schema.org datePublished는 UTC로 별도 처리)
 * Privacy: Intl.DateTimeFormat()만 사용, 외부 API/cookie 없음 (GDPR 친화)
 *
 * 설치 방법 (GeneratePress 무료 + 1인 self-use, plugin 추가 최소화):
 *   1) WordPress.org에서 "Code Snippets" plugin 설치
 *      - URL: https://wordpress.org/plugins/code-snippets/
 *      - 설정: Add New → Name: "Visitor Timezone" → Code area에 이 전체 파일 내용 붙여넣기
 *      - Run everywhere 체크 → Save and Activate
 *   2) 또는 child theme의 functions.php에 추가
 *
 * 동작:
 *   - <time datetime="2026-08-04T05:00:00Z"> 또는 data-pubdate="2026-08-04T05:00:00Z" 요소를 찾아서
 *   - visitor의 timezone으로 변환한 후 텍스트 교체
 *   - <abbr title="Asia/Seoul"> 원본 시간</abbr> 형식으로 툴팁 제공 (optional)
 *
 * 변환 우선순위:
 *   1) <time datetime="..."> ISO 8601 datetime attribute (WordPress 표준)
 *   2) <span data-pubdate="..."> wp-auto chunked generator 호환
 */
(function () {
  "use strict";

  // visitor timezone (브라우저 Intl API)
  var visitorTz = (Intl && Intl.DateTimeFormat().resolvedOptions().timeZone) || "UTC";

  // 원본 표시 포맷 옵션
  var FORMAT_OPTIONS = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short"
  };

  /**
   * ISO 8601 datetime 문자열을 visitor timezone으로 변환.
   * @param {string} isoString - 예: "2026-08-04T05:00:00Z" 또는 "2026-08-04 05:00:00"
   * @returns {string|null} - 변환된 시간 문자열 또는 null (실패 시)
   */
  function formatInVisitorTime(isoString) {
    if (!isoString) return null;
    var normalized = String(isoString).trim().replace(" ", "T");
    // Z (UTC) suffix 없으면 그대로 사용 (워드프레스가 timezone offset 포함 안 한 경우)
    // 단 server-side가 Asia/Seoul 기준이면 visitor의 변환 결과는 ±9h 어긋남
    // → UTC 권장 (Rank Math JSON-LD datePublished는 이미 UTC)
    var date = new Date(normalized);
    if (isNaN(date.getTime())) return null;
    try {
      return new Intl.DateTimeFormat(undefined, FORMAT_OPTIONS).format(date);
    } catch (e) {
      // visitor locale이 intl 미지원 시 fallback
      return date.toUTCString();
    }
  }

  /**
   * 모든 변환 대상 element 찾아서 텍스트 교체.
   * - <time datetime="..."> (WordPress 표준)
   * - <span data-pubdate="..."> (wp-auto 호환)
   */
  function applyTimezoneToElements() {
    // 1) <time datetime="...">
    var timeEls = document.querySelectorAll("time[datetime]");
    timeEls.forEach(function (el) {
      var iso = el.getAttribute("datetime");
      var formatted = formatInVisitorTime(iso);
      if (formatted) {
        // 원본 시간은 abbr title로 보존, 표시 텍스트는 visitor 시간으로
        if (!el.querySelector("abbr")) {
          el.innerHTML = '<abbr title="' + visitorTz + '">' + formatted + "</abbr>";
        }
      }
    });

    // 2) <span data-pubdate="..."> (wp-auto cluster 날짜용)
    var pubdateEls = document.querySelectorAll("[data-pubdate]");
    pubdateEls.forEach(function (el) {
      var iso = el.getAttribute("data-pubdate");
      var formatted = formatInVisitorTime(iso);
      if (formatted) {
        el.textContent = formatted;
        el.setAttribute("title", "Your timezone: " + visitorTz);
      }
    });
  }

  /**
   * WP post published time 변환 헬퍼 (Cloudflare APO/CDN 환경 호환).
   * 일부 CDN은 HTML을 변형해서 selector 매칭 안 될 수 있어 fallback도 추가.
   */
  function findPublishedTimeFallback() {
    // entry-date published, .posted-on 등 워드프레스 표준 selector
    var selectors = [
      ".entry-date.published",
      ".posted-on .published",
      "article time[datetime]",
      "header time[datetime]"
    ];
    selectors.forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) {
        var iso = el.getAttribute("datetime") || el.getAttribute("title");
        var formatted = formatInVisitorTime(iso);
        if (formatted) {
          el.textContent = formatted;
        }
      }
    });
  }

  // DOMContentLoaded 후 실행 (GeneratePress는 SPA처럼 부분 갱신 안 하므로 충분)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      applyTimezoneToElements();
      findPublishedTimeFallback();
    });
  } else {
    applyTimezoneToElements();
    findPublishedTimeFallback();
  }

  // 외부에서 사용 가능하도록 export (디버깅 / 확장용)
  window.wpAutoVisitorTz = {
    visitorTz: visitorTz,
    formatInVisitorTime: formatInVisitorTime,
    reapply: applyTimezoneToElements
  };
})();
