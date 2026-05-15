# BenefitInfo 프로젝트 가이드

## 프로젝트 개요
정부지원금·복지혜택 통합 정보 플랫폼. 공공데이터포털 API로 복지정책·구인정보를 자동 수집하여 워드프레스에 발행. 구글 애드센스 심사 중.

- **작업 디렉토리**: E:\projects\benefitinfo
- **사이트**: beninfo.kr (WordPress)
- **담당**: affiliate83

## 기술 스택
- CMS: WordPress (PHP, functions.php, 커스텀 포스트 타입)
- 크롤러: Python 3.11+ (requests, lxml, python-dotenv)
- AI 풍부화: Claude Haiku (claude-haiku-4-5-20251001) — 신규 글에만 적용
- 연동: WordPress REST API (Application Password 인증)
- 스케줄러: GitHub Actions (매일 KST 10시)
- DB(중복방지): SQLite (dedup.db)

## 실제 프로젝트 구조
```
E:\projects\benefitinfo\
  crawler/
    main.py                    - 크롤러 진입점 (enrichment 중복 체크 이후에만 호출)
    sources/
      national_welfare.py      - 중앙부처 복지서비스 API (data.go.kr)
      local_welfare.py         - 지자체 복지서비스 API (data.go.kr)
      senuri_jobs.py           - 시니어/청년 구인정보 API (한국노인인력개발원)
    poster/
      wordpress.py             - WP REST API 발행 모듈
    utils/
      dedup.py                 - SQLite 중복 체크
      logger.py                - 로깅
      enricher.py              - Claude Haiku AI 풍부화 (enrich_job, enrich_policy)
      region.py                - 주소 → policy_region 매핑
  theme/                       - WordPress 테마 파일 (서버에 직접 업로드)
    functions.php
    taxonomy-policy_category.php
    single-policy.php
    archive-policy.php
  backfill_regions.py          - 기존 포스트 policy_region 소급 적용 스크립트
  enrich_existing_posts.py     - 기존 포스트 AI 풍부화 소급 적용 (DAILY_LIMIT=50)
  .env                         - WP 인증 정보 (Git 제외 필수)
  requirements.txt
```

## WordPress 데이터 구조
- **CPT:** `policy`
- **Taxonomy:**
  - `policy_category`: 복지, 고용, 청년, 주거, 창업, 교육, 보건의료, 문화생활, 농림어업
  - `policy_region`: 서울, 경기, 인천, 부산, 대구, 광주, 대전, 울산, 세종, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주 (17개 광역)
- **ACF 핵심 필드:** `application_end_date`, `target_audience`, `benefit_summary`, `official_link`, `agency_name`, `support_scale`, `is_expired`

## 코드 스타일 규칙
- 커밋 메시지는 한글로 작성
- .env 파일은 절대 Git에 커밋하지 말 것
- 크롤러 요청 간격 최소 2~3초 딜레이 유지
- WP REST API 인증은 Application Password만 사용

## AI 풍부화 구조 (중요)
- Claude Haiku로 글당 AI 콘텐츠(지원대상, 신청방법, FAQ) 생성
- **enrichment는 main.py에서 중복 체크 통과한 신규 글에만 호출** (비용 절감)
  - 소스 파일(senuri_jobs.py, national_welfare.py 등)에서는 enrichment 호출하지 않음
  - main.py의 `_enrich(item)` 함수가 source_type에 따라 dispatch
- `SKIP_ENRICHMENT=1` 환경변수 설정 시 enrichment 완전 비활성화
- 기존 포스트 소급 적용: `enrich_existing_posts.py` (하루 50건, faq-item 없는 글만)

## GitHub Actions 워크플로
```yaml
# .github/workflows/crawl.yml
# 매일 KST 10시 실행
# python -m crawler.main --source senuri --pages 3
# python crawler/enrich_existing_posts.py
```

## 주요 명령어
```bash
pip install -r requirements.txt                         # 의존성 설치
python -m crawler.main                                  # 전체 소스 수집
python -m crawler.main --source senuri --pages 3        # senuri만 3페이지
python -m crawler.main --dry-run                        # 테스트 (WP 발행 안 함)
python crawler/enrich_existing_posts.py                 # 기존 글 소급 풍부화
python backfill_regions.py --dry-run                    # 지역 소급 테스트
```

## 수익화 전략
- **현재**: 구글 애드센스 심사 중
- **대안**: React Native + Expo 앱으로 AdMob 수익화 (noinjob 앱 완성 후 동일 구조로 개발)

## 테마 파일 배포
테마 파일은 WordPress 서버에 직접 업로드 필요 (WP File Manager 또는 SFTP).
수정 후 서버에 올리는 것 잊지 말 것.

## 공공데이터 API 정보
- **인증키**: data.go.kr 마이페이지 (환경변수 `DATA_GO_KR_API_KEY`)
- **중앙부처 복지서비스**: `https://apis.data.go.kr/B554287/NationalWelfareInformationsV001`
- **지자체 복지서비스**: `https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations`
- **시니어 구인정보**: `https://apis.data.go.kr/B552474/SenuriService`

## 주의사항
- 공공데이터 출처 표기 필수
- 테마 수정 시 functions.php, single-policy.php, taxonomy-policy_category.php, archive-policy.php 4개 파일 서버 업로드 필요
- `enrich_existing_posts.py`는 GitHub Actions에서 매일 50건씩 실행 중 (기존 글 소급 완료 후 자동 종료)