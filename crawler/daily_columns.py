"""
하루 2편씩 칼럼 자동 생성·발행 (GitHub Actions 스케줄용)
기존 제목과 중복되면 스킵
"""
import os
import re
import time
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()

WP_URL        = os.getenv('WP_URL', '').rstrip('/')
WP_USER       = os.getenv('WP_USERNAME', '')
WP_APP_PASS   = os.getenv('WP_APP_PASSWORD', '')
PEXELS_KEY    = os.getenv('PEXELS_API_KEY', '')
ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY', '')

AUTH           = (WP_USER, WP_APP_PASS)
PEXELS_HEADERS = {'Authorization': PEXELS_KEY}
client         = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

COLUMN_CATEGORY_SLUG = 'column'
DAILY_LIMIT          = 2

TOPICS = [
    ("아동수당 신청 방법과 지급 기준 – 0~8세 자녀 있다면 필독", "child allowance benefit family", "육아·아동"),
    ("첫만남이용권 200만원 사용법 – 어디서 어떻게 쓰나요?", "newborn baby welcome voucher", "육아·아동"),
    ("산모신생아 건강관리사 서비스 – 출산 후 돌봄 신청하기", "postpartum care newborn mother", "육아·아동"),
    ("기저귀·분유 바우처 신청 방법 – 저소득 가정 무료 지원", "baby diaper formula voucher", "육아·아동"),
    ("임산부 친환경 농산물 지원 – 꾸러미 신청 방법 총정리", "pregnant woman organic food support", "육아·아동"),
    ("고위험 임산부 의료비 지원 – 입원비 90%까지 지원", "high risk pregnancy medical support", "육아·아동"),
    ("미숙아·선천성 이상아 의료비 지원 완전 가이드", "premature baby medical support", "육아·아동"),
    ("1인 가구 정부 지원 혜택 총정리 – 혼자 살면 더 챙겨야 할 것들", "single person household welfare", "복지"),
    ("청년 1인 가구 특별 지원 – 주거·생활비·심리 상담 총정리", "young single household support", "청년"),
    ("경력단절 여성 취업 지원 – 새일센터 100% 활용법", "career break women employment", "고용"),
    ("경력단절 여성 직업훈련 프로그램 – 무료 교육 받는 방법", "career interrupted women training", "고용"),
    ("여성 창업 지원 프로그램 – 여성기업 전용 자금·교육", "women entrepreneur startup support", "창업"),
    ("남성 육아휴직 급여 – 6+6 제도 완벽 정리 (2026년)", "paternity leave benefit father", "육아·아동"),
    ("배우자 출산휴가 급여 – 신청 방법과 지급 금액", "spouse maternity leave benefit", "육아·아동"),
    ("고용보험 미적용자 출산급여 – 프리랜서·자영업자도 받는다", "self employed maternity benefit", "육아·아동"),
    ("예술인 고용보험 혜택 – 프리랜서 예술가 꼭 알아야 할 것", "artist freelancer employment insurance", "고용"),
    ("특수형태근로자 산재보험 – 배달·대리운전 종사자 신청법", "special employment accident insurance", "고용"),
    ("산업재해 보상 신청 방법 – 일하다 다쳤을 때 절차", "industrial accident compensation claim", "고용"),
    ("프리랜서 세금 절약법 – 종합소득세 신고 완전 가이드", "freelancer tax saving income tax", "고용"),
    ("플랫폼 노동자 권리와 지원 – 배달·대리 종사자 복지", "platform gig worker rights support", "고용"),
    ("중장년 내일센터 활용법 – 40·50대 재취업 무료 지원", "middle aged reemployment support center", "고용"),
    ("연말정산 환급금 최대화 방법 – 놓치기 쉬운 공제 항목", "year end tax refund deduction", "금융"),
    ("건강보험료 환급금 받는 법 – 내가 더 낸 돈 돌려받기", "health insurance refund overpayment", "복지"),
    ("근로장려금 vs 자녀장려금 – 차이점과 동시 신청 방법", "earned income tax credit comparison", "금융"),
    ("종합소득세 신고 방법 – 직장인·사업자 쉽게 따라하기", "comprehensive income tax filing guide", "금융"),
    ("청년 주택드림 청약통장 – 가입 조건과 혜택 완전 정리", "youth housing dream savings account", "주거"),
    ("공공임대주택 입주 방법 – 신청부터 당첨까지 A to Z", "public rental housing application", "주거"),
    ("행복주택 신청 자격과 방법 – 청년·신혼부부 필독", "happy housing youth newlywed", "주거"),
    ("국민임대주택 vs 영구임대주택 – 차이점과 신청 방법", "national rental housing comparison", "주거"),
    ("전세사기 피해자 지원 – 정부 긴급 지원 방법 총정리", "jeonse fraud victim support", "주거"),
    ("반값 등록금 국가장학금 완전 정리 – 소득분위별 지원금액", "national scholarship tuition half", "교육"),
    ("취업 후 상환 학자금 대출 – 졸업 후 갚는 스마트한 방법", "income contingent student loan", "교육"),
    ("특성화고·마이스터고 졸업생 취업 지원 – 정부 혜택 모음", "vocational high school graduate support", "교육"),
    ("학교 밖 청소년 지원 서비스 – 검정고시부터 취업까지", "out of school youth support", "교육"),
    ("장애아동 재활치료 지원 – 발달재활서비스 신청 방법", "disabled child rehabilitation support", "장애"),
    ("언어발달 지원 서비스 – 아이 말 늦을 때 무료로 받는 법", "language development support child", "교육"),
    ("치매 조기검진 무료 받는 방법 – 전국 치매안심센터 이용", "dementia early screening free center", "의료"),
    ("치매 가족 지원 서비스 – 쉬어가기 프로그램·돌봄비 지원", "dementia family caregiver support", "의료"),
    ("정신장애인 지역사회 통합 지원 – 정신건강복지센터 서비스", "mental disorder community support", "의료"),
    ("알코올 중독 치료 지원 – 무료 상담과 입원 지원 방법", "alcohol addiction treatment support", "의료"),
    ("국가유공자 지원 혜택 총정리 – 의료·교육·취업 우대", "national merit veteran benefit", "복지"),
    ("참전유공자 지원 혜택 – 수당·의료·복지 서비스 총정리", "veteran war service benefit", "복지"),
    ("보호종료아동 자립 지원 – 시설 퇴소 후 받을 수 있는 혜택", "foster care aged out youth support", "복지"),
    ("가정폭력 피해자 지원 – 쉼터·법률·의료 지원 총정리", "domestic violence victim support", "복지"),
    ("범죄 피해자 지원 제도 – 국가에서 받는 위로금과 서비스", "crime victim state support compensation", "복지"),
    ("자활사업 참여 방법 – 일하면서 복지도 받는 제도 안내", "self sufficiency program welfare work", "복지"),
    ("기초수급자 탈수급 지원 – 자립하면 더 받는 혜택들", "welfare recipient independence support", "복지"),
    ("독거노인 맞춤돌봄 서비스 – 방문·전화·ICT 안전 확인", "elderly living alone care service", "복지"),
    ("노인 실종 예방 서비스 – 배회감지기·지문 사전등록", "elderly wandering prevention GPS", "복지"),
    ("결혼이민자 사회통합 지원 – 한국어 교육·취업 연계", "marriage immigrant social integration", "다문화"),
    ("이주여성 폭력피해 지원 – 쉼터·통역·법률 도움받기", "immigrant women violence support", "다문화"),
    ("사회적 기업 창업 지원 – 인건비·경영 지원 받는 방법", "social enterprise startup support", "창업"),
    ("협동조합 설립 방법과 정부 지원 – 함께 창업하기", "cooperative startup government support", "창업"),
    ("소년원 출원 청소년 취업 지원 – 재기를 위한 정부 프로그램", "juvenile rehabilitation employment", "청년"),
    ("청년 심리지원 서비스 – 무료 상담 받는 방법 총정리", "youth mental health free counseling", "청년"),
    ("청년 고립·은둔 지원 – 사회 복귀를 위한 정부 프로그램", "youth recluse isolation support", "청년"),
    ("장애인 주택 개조 지원 – 무장애 편의시설 설치비 지원", "disabled housing modification support", "장애"),
    ("장애인 이동 편의 지원 – 특별교통수단·이동지원센터", "disabled transportation mobility support", "장애"),
    ("시각장애인 지원 서비스 – 점자도서·안내인·보조기기", "visually impaired support service", "장애"),
    ("청각장애인 지원 서비스 – 수어통역·보청기·자막 지원", "hearing impaired support service", "장애"),
    ("중증 장애인 자립생활 지원 – 활동지원사 이용 방법", "severe disability independent living", "장애"),
    ("근로자 휴가비 지원 – 국내 여행 바우처 신청 방법", "worker vacation voucher domestic travel", "생활"),
    ("스포츠강좌이용권 신청법 – 수영·헬스·요가 반값에 배우기", "sports lesson voucher discount", "생활"),
    ("청소년 문화예술 지원 – 무료 체험과 바우처 활용법", "youth culture arts free voucher", "교육"),
    ("교육급여 바우처 사용법 – 학용품·온라인강의 구매하기", "education voucher school supplies", "교육"),
    ("저소득층 에너지효율 개선 지원 – 단열·창호 교체 무료", "low income energy efficiency home", "주거"),
    ("농촌 빈집 활용 귀농·귀촌 지원 – 정착금·주택 수리비", "rural empty house relocation support", "주거"),
    ("귀농·귀촌 창업 지원 – 농업 창업 자금과 교육 프로그램", "rural farming startup support fund", "창업"),
    ("어선원 재해보상 – 바다에서 일하다 다쳤을 때 받는 지원", "fisherman accident compensation", "고용"),
    ("임업인 지원 프로그램 – 산림 관련 정부 보조금 총정리", "forestry worker government support", "복지"),
    ("도시 청년 농촌 정착 지원 – 월 80만원 지원받는 방법", "urban youth rural settlement support", "청년"),
    ("푸드뱅크 이용 방법 – 저소득층 식품 무료 지원 신청", "food bank low income free food", "복지"),
    ("무료 법률 구조 서비스 – 소송비용 없이 권리 찾기", "free legal aid service lawsuit", "복지"),
    ("소비자 피해 구제 방법 – 환불·보상 신청 절차 총정리", "consumer damage relief refund", "생활"),
    ("채무 탕감 프로그램 – 장기연체자 빚 줄이는 방법", "debt relief long term overdue", "금융"),
    ("개인파산 신청 방법 – 빚이 너무 많을 때 해결책", "personal bankruptcy application guide", "금융"),
    ("햇살론유스 신청 방법 – 청년 저신용자 생활비 대출", "youth sunshine loan low credit", "금융"),
    ("소액생계비 대출 신청법 – 급할 때 100만원 빌리는 방법", "emergency small loan living cost", "금융"),
    ("전세보증금 반환 보증보험 – 떼일 걱정 없이 전세 사는 법", "jeonse deposit guarantee insurance", "주거"),
    ("주택 화재보험 정부 지원 – 저소득층 무료 가입 방법", "home fire insurance government support", "주거"),
    ("가스안전 점검 서비스 – 무료 점검 신청하는 방법", "gas safety inspection free service", "생활"),
    ("수도요금 감면 – 기초수급자·장애인 할인 신청법", "water bill discount welfare", "복지"),
    ("TV 수신료 면제 신청 – 장애인·기초수급자 대상", "TV license fee waiver welfare", "복지"),
    ("자동차세 감면 – 장애인·국가유공자 차량 혜택", "vehicle tax reduction disability veteran", "금융"),
    ("취득세·재산세 감면 – 생애 첫 주택 구입 세금 혜택", "property tax reduction first home buyer", "금융"),
    ("교통카드 복지 할인 – 장애인·노인·기초수급자 혜택", "transit card welfare discount elderly", "복지"),
    ("보육교사 처우 개선 지원 – 수당·교육비 지원 받는 법", "childcare teacher support allowance", "교육"),
    ("요양보호사 처우 개선 – 월급·휴가·안전 지원 혜택", "care worker treatment improvement", "고용"),
    ("사회복지사 역량 강화 지원 – 교육·자격증·처우 개선", "social worker capacity support", "고용"),
    ("응급 의료비 지원 – 갑자기 큰 병원비 생겼을 때", "emergency medical expense support", "의료"),
    ("희귀·난치성 질환 산정특례 – 의료비 90% 감면받기", "rare disease medical deduction", "의료"),
    ("입원 환자 간병비 지원 – 간병 걱정 덜어주는 서비스", "hospital patient caregiver support", "의료"),
    ("노인 인플루엔자 무료 예방접종 – 접종 방법과 장소", "elderly flu vaccination free", "의료"),
    ("금연 지원 서비스 – 니코틴 패치·상담 무료 받기", "smoking cessation free support patch", "의료"),
    ("비만 치료 지원 – 국가 건강검진 사후 관리 프로그램", "obesity treatment health checkup", "의료"),
    ("구강 검진 무료 받기 – 건강보험 연 1회 지원 혜택", "dental checkup free health insurance", "의료"),
    ("정기 건강검진 종류와 대상 – 내가 받을 수 있는 검진", "regular health checkup type benefit", "의료"),
    ("암 검진 무료 받는 방법 – 5대 암 국가 지원 총정리", "cancer screening free national", "의료"),
]


def get_existing_titles() -> set:
    titles, page = set(), 1
    print(f'  WP_URL={WP_URL}')
    print(f'  WP_USER={WP_USER[:4]}***' if WP_USER else '  WP_USER=(없음)')
    res = requests.get(
        f'{WP_URL}/wp-json/wp/v2/categories',
        auth=AUTH,
        params={'slug': COLUMN_CATEGORY_SLUG, 'per_page': 1},
        timeout=10,
    )
    print(f'  카테고리 조회 상태: {res.status_code}')
    if res.status_code != 200 or not res.text.strip():
        print(f'  응답 본문: {res.text[:200]}')
        return titles
    cats = res.json()
    if not cats:
        return titles
    cat_id = cats[0]['id']

    while True:
        res = requests.get(
            f'{WP_URL}/wp-json/wp/v2/posts',
            auth=AUTH,
            params={'categories': cat_id, 'per_page': 100, 'page': page, '_fields': 'id,title'},
            timeout=15,
        )
        if res.status_code != 200:
            break
        batch = res.json()
        if not batch:
            break
        for p in batch:
            titles.add(p['title']['rendered'])
        page += 1
    return titles


def get_category_id(slug: str) -> int | None:
    res = requests.get(
        f'{WP_URL}/wp-json/wp/v2/categories',
        auth=AUTH,
        params={'slug': slug, 'per_page': 1},
        timeout=10,
    )
    cats = res.json()
    return cats[0]['id'] if cats else None


def generate_article(title: str) -> str:
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=2500,
        messages=[{
            'role': 'user',
            'content': f'''다음 제목으로 한국 정부지원금·복지 정보 사이트(beninfo.kr) 독자를 위한 실용적인 칼럼을 작성해주세요.

제목: {title}

조건:
- 1,200자 이상
- 마크다운 형식 (## 소제목 3~5개, **강조** 사용)
- 구체적인 금액, 신청 방법, 자격 조건 등 실용 정보 포함
- 쉽고 친근한 문체
- 제목은 포함하지 말고 본문만 작성
- 출처 표기나 "AI가 작성" 문구 절대 불가'''
        }]
    )
    return message.content[0].text


def markdown_to_html(text: str) -> str:
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        if block.startswith('<h'):
            paragraphs.append(block)
        elif block.startswith(('- ', '* ')):
            items = [f'<li>{line[2:].strip()}</li>'
                     for line in block.split('\n')
                     if line.strip().startswith(('- ', '* '))]
            paragraphs.append('<ul>' + ''.join(items) + '</ul>')
        else:
            paragraphs.append(f'<p>{block}</p>')
    return '\n'.join(paragraphs)


def get_pexels_image(query: str) -> dict | None:
    if not PEXELS_KEY:
        return None
    try:
        res = requests.get(
            'https://api.pexels.com/v1/search',
            headers=PEXELS_HEADERS,
            params={'query': query, 'per_page': 5, 'orientation': 'landscape'},
            timeout=10,
        )
        photos = res.json().get('photos', [])
        return photos[0] if photos else None
    except Exception as e:
        print(f'  [Pexels] 오류: {e}')
    return None


def upload_image(image_url: str, filename: str, alt_text: str) -> int | None:
    try:
        img_data = requests.get(image_url, timeout=15).content
        res = requests.post(
            f'{WP_URL}/wp-json/wp/v2/media',
            auth=AUTH,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'image/jpeg',
            },
            data=img_data,
            timeout=30,
        )
        if res.status_code == 201:
            media_id = res.json().get('id')
            requests.post(
                f'{WP_URL}/wp-json/wp/v2/media/{media_id}',
                auth=AUTH,
                json={'alt_text': alt_text, 'caption': 'Photo by Pexels'},
                timeout=10,
            )
            return media_id
    except Exception as e:
        print(f'  [WP] 이미지 업로드 오류: {e}')
    return None


def publish_post(title: str, content: str, cat_id: int, media_id: int | None) -> int | None:
    data = {
        'title':      title,
        'content':    content,
        'status':     'publish',
        'categories': [cat_id],
    }
    if media_id:
        data['featured_media'] = media_id
    try:
        res = requests.post(
            f'{WP_URL}/wp-json/wp/v2/posts',
            auth=AUTH,
            json=data,
            timeout=20,
        )
        if res.status_code == 201:
            return res.json().get('id')
        print(f'  [WP] 발행 실패 {res.status_code}: {res.text[:100]}')
    except Exception as e:
        print(f'  [WP] 발행 오류: {e}')
    return None


def main():
    print('기존 칼럼 제목 로딩...')
    existing = get_existing_titles()
    print(f'기존 칼럼 수: {len(existing)}개')

    cat_id = get_category_id(COLUMN_CATEGORY_SLUG)
    if not cat_id:
        print('칼럼 카테고리를 찾을 수 없습니다.')
        return

    new_topics = [(t, q) for t, q, _ in TOPICS if t not in existing]
    print(f'발행 가능한 새 주제: {len(new_topics)}개')

    targets = new_topics[:DAILY_LIMIT]
    print(f'오늘 발행할 글: {len(targets)}개\n')

    if not targets:
        print('발행할 새 주제가 없습니다.')
        return

    for i, (title, pexels_query) in enumerate(targets, 1):
        print(f'[{i}/{len(targets)}] {title[:50]}')

        try:
            content_md   = generate_article(title)
            content_html = markdown_to_html(content_md)
            print(f'  글 생성 완료 ({len(content_md)}자)')
        except Exception as e:
            print(f'  글 생성 실패: {e}')
            time.sleep(5)
            continue

        photo    = get_pexels_image(pexels_query)
        media_id = None
        if photo:
            media_id = upload_image(photo['src']['large'], f'col_daily_{i}.jpg', title)
            if media_id:
                print(f'  이미지 업로드 완료 (ID: {media_id})')

        post_id = publish_post(title, content_html, cat_id, media_id)
        if post_id:
            print(f'  발행 완료 (포스트 ID: {post_id})')
        else:
            print('  발행 실패')

        time.sleep(3)

    print('\n오늘 작업 완료!')


if __name__ == '__main__':
    main()
