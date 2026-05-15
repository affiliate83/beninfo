import os
import re
import anthropic
from crawler.utils.logger import get_logger

logger = get_logger("enricher")

# wptexturize 백틱 변환 이중 안전망
_FENCE_RE = re.compile(r'```[^\n`]*\n?|&#8220;`[a-z]*\s*', re.IGNORECASE)

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        _client = anthropic.Anthropic(api_key=key)
    return _client


def _sanitize(html: str) -> str:
    """200자 이상 연속 비공백 문자(base64, 깨진 인코딩 등) 제거"""
    return re.sub(r'\S{200,}', '', html)


def _call(prompt: str, max_tokens: int = 800) -> str:
    client = _get_client()
    if client is None:
        return ""
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = _FENCE_RE.sub("", msg.content[0].text).strip()
        return _sanitize(raw)
    except Exception as e:
        logger.warning("Claude API 실패: %s", e)
        return ""


def enrich_policy(data: dict) -> str:
    """복지/정책 포스트 AI 풍부화. 실패 시 빈 문자열 반환."""
    if os.getenv("SKIP_ENRICHMENT"):
        return ""
    title    = data.get("title", "")
    summary  = data.get("summary") or data.get("benefit_summary", "")
    target   = data.get("target_audience", "")
    agency   = data.get("agency_name", "")
    criteria = data.get("select_criteria", "")

    if not title:
        return ""

    prompt = f"""다음 정부지원정책 정보를 바탕으로 시민이 이해하기 쉬운 콘텐츠를 HTML로 작성하세요.

[정책명] {title}
[담당기관] {agency}
[요약] {summary}
[지원대상] {target}
[선정기준] {criteria}

아래 섹션을 순서대로 HTML로만 출력하세요 (다른 텍스트, 인트로 문장 없이):

<h2>이 정책이란?</h2>
(2~3문장으로 정책 목적과 혜택을 쉽게 설명)

<h2>지원 대상</h2>
<ul>
(구체적인 지원 대상을 bullet로 3~5개)
</ul>

<h2>신청 방법</h2>
<ol>
(신청 단계를 번호 목록으로 3~5단계)
</ol>

<h2>자주 묻는 질문</h2>
<div class='faq-item'><h3 class='faq-q'>Q. 질문1</h3><p class='faq-a'>A. 답변1</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 질문2</h3><p class='faq-a'>A. 답변2</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 질문3</h3><p class='faq-a'>A. 답변3</p></div>

규칙: HTML 속성은 작은따옴표. 코드 펜스(```) 절대 사용 금지. 쉬운 한국어."""

    return _call(prompt)


def enrich_job(data: dict) -> str:
    """채용공고 AI 풍부화. 실패 시 빈 문자열 반환."""
    if os.getenv("SKIP_ENRICHMENT"):
        return ""
    title    = data.get("title", "")
    company  = data.get("agency_name", "")
    summary  = data.get("benefit_summary", "")
    target   = data.get("target_audience", "")
    emp_type = data.get("support_scale", "")

    if not title:
        return ""

    prompt = f"""다음 채용공고 정보를 바탕으로 구직자에게 유용한 콘텐츠를 HTML로 작성하세요.

[공고명] {title}
[기관명] {company}
[고용형태] {emp_type}
[지원자격] {target}
[기타정보] {summary}

아래 섹션을 순서대로 HTML로만 출력하세요 (다른 텍스트, 인트로 문장 없이):

<h2>공고 소개</h2>
(이 채용공고의 특징과 지원 시 유리한 점을 2~3문장으로 설명)

<h2>지원 자격</h2>
<ul>
(지원 자격 조건을 bullet로 3~5개, 정보가 없으면 일반적인 해당 직종 요건 기재)
</ul>

<h2>지원 방법 및 유의사항</h2>
<ol>
(지원 단계와 주의사항을 번호 목록으로 3~4단계)
</ol>

<h2>자주 묻는 질문</h2>
<div class='faq-item'><h3 class='faq-q'>Q. 질문1</h3><p class='faq-a'>A. 답변1</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 질문2</h3><p class='faq-a'>A. 답변2</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 질문3</h3><p class='faq-a'>A. 답변3</p></div>

규칙: HTML 속성은 작은따옴표. 코드 펜스(```) 절대 사용 금지. 쉬운 한국어."""

    return _call(prompt)