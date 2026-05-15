_REGION_MAP = [
    ('서울',   '서울', 'seoul'),
    ('부산',   '부산', 'busan'),
    ('대구',   '대구', 'daegu'),
    ('인천',   '인천', 'incheon'),
    ('광주',   '광주', 'gwangju'),
    ('대전',   '대전', 'daejeon'),
    ('울산',   '울산', 'ulsan'),
    ('세종',   '세종', 'sejong'),
    ('경기',   '경기', 'gyeonggi'),
    ('강원',   '강원', 'gangwon'),
    ('충청북', '충북', 'chungbuk'),
    ('충북',   '충북', 'chungbuk'),
    ('충청남', '충남', 'chungnam'),
    ('충남',   '충남', 'chungnam'),
    ('전라북', '전북', 'jeonbuk'),
    ('전북',   '전북', 'jeonbuk'),
    ('전라남', '전남', 'jeonnam'),
    ('전남',   '전남', 'jeonnam'),
    ('경상북', '경북', 'gyeongbuk'),
    ('경북',   '경북', 'gyeongbuk'),
    ('경상남', '경남', 'gyeongnam'),
    ('경남',   '경남', 'gyeongnam'),
    ('제주',   '제주', 'jeju'),
]


def extract_region(address: str) -> tuple[str, str] | None:
    """주소 문자열에서 (표시명, slug) 반환. 미식별 시 None."""
    if not address:
        return None
    for keyword, name, slug in _REGION_MAP:
        if keyword in address:
            return (name, slug)
    return None