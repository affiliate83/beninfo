# BenefitInfo 프로젝트 가이드

## 프로젝트 개요
대한민국 정부 지원정책, 복지 혜택, 공공기관 채용 공고를 한 곳에서 검색·추천하는 워드프레스 기반 포털 사이트.

- **작업 디렉토리**: E:\projects\benefitinfo
- **사이트**: (도메인 미정 - 추후 업데이트)
- **벤치마킹**: govhelp.co.kr
- **담당**: affiliate83

## 기술 스택
- CMS: WordPress (PHP, functions.php, 커스텀 포스트 타입)
- 크롤러: Python 3.11+ (requests, BeautifulSoup4)
- 데이터 소스: 공공데이터포털 API (data.go.kr), 워크넷 API, 복지로 API
- 연동: WordPress REST API (Application Password 인증) 또는 WP All Import
- 스케줄러: GitHub Actions 또는 Windows Task Scheduler
- DB(크롤러): SQLite (중복 방지용, `data_source` 필드 기반)

## WordPress 데이터 구조
- **CPT:** `policy` (정부지원정책)
- **Taxonomy:**
  - `policy_category`: 청년, 복지, 주거, 고용, 창업, 교육, 보건의료, 문화생활, 농림어업
  - `policy_region`: 전국, 서울, 경기 등 17개 광역지자체
  - `policy_target`: 청년, 중장년, 장애인, 소상공인 등
- **ACF 핵심 필드:**
  - `application_start_date`, `application_end_date` (D-Day 계산)
  - `target_audience`, `benefit_summary`, `official_link`
  - `agency_name`, `support_scale`, `data_source`, `is_expired`

## 프로젝트 구조 (예정)
```
E:\projects\benefitinfo\
  crawler/
    main.py
    sources/       - welfare.py, jobs.py, startup.py
    poster/        - wordpress.py
    utils/         - dedup.py, logger.py
  .env             - WP 인증 정보 등 (Git 제외 필수)
  .gitignore
  requirements.txt
  PRD.md
  CLAUDE.md
```

## 코드 스타일 규칙
- 커밋 메시지는 한글로 작성 (예: feat: 복지로 API 크롤러 추가)
- .env 파일은 절대 Git에 커밋하지 말 것
- 크롤러 요청 간격 최소 2~5초 딜레이 유지 (robots.txt 준수)
- WP REST API 인증은 Application Password만 사용 (Basic Auth 플러그인 금지)
- 공공데이터 API 이용약관 준수, 원문 출처(`agency_name`, `official_link`) 반드시 포함

## 중복 방지 규칙
- `data_source` 필드(원본 공고 URL 또는 API 고유 ID)를 SQLite에 저장하여 중복 업로드 차단
- 동일 `data_source` 값이 이미 존재하면 새 포스트 생성하지 않고 내용만 업데이트 (UPSERT)

## 마감 처리 규칙
- `application_end_date` < 오늘 날짜인 경우 `is_expired = true` 자동 설정
- 만료 공고는 목록 페이지 기본 쿼리에서 제외 (`meta_query` 활용)
- 만료 공고는 삭제하지 않고 보관 (검색 엔진 링크 유지)

## 주요 명령어
```bash
pip install -r requirements.txt   # 크롤러 의존성 설치
python crawler/main.py            # 크롤러 수동 실행
python crawler/main.py --source welfare   # 특정 소스만 실행
```

## 수익화 전략
- **1단계 (애드센스 승인 전):** 제휴 마케팅 링크 (텐핑, 쿠팡 파트너스) - 정적 이미지+a태그 방식
- **2단계 (콘텐츠 50건+ 후):** 구글 애드센스 신청
- 제휴 링크에는 반드시 '광고' 또는 '제휴' 표기 (공정거래위원회 고시 준수)

## SEO 주의사항
- 각 공고 메타 타이틀: `{공고명} - {주관기관} | BenefitInfo` 형식
- 카테고리 허브 페이지에 수동 소개 텍스트 추가 필수 (자동 생성 콘텐츠만으로 애드센스 승인 불가)
- Open Graph 태그 및 Schema Markup (`GovernmentService` 타입) 적용

## 보안 주의사항
- 워드프레스 관리자 계정 2FA 적용 필수
- `/wp-json` REST API 엔드포인트 인증 없이 쓰기 불가 설정
- Wordfence Security 플러그인 설치

## 에러 처리
- API 호출 실패 시 최대 3회 재시도
- 크롤러 실행 로그는 `crawler/logs/` 디렉토리에 날짜별 저장 (30일 보관)
- 크롤링 실패 시 이메일 알림 (hyunchulj@gmail.com)