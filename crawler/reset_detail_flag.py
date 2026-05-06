"""
기존에 수집된 national_welfare 포스트의 detail_fetched 플래그를 0으로 초기화.
update_details.py 가 aplyEndDt(신청종료일) 를 추가 저장하도록 수정된 후
기존 ~390건에도 날짜가 채워지도록 재처리를 유도하기 위해 1회 실행한다.
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dedup.db")


def reset():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "UPDATE seen SET detail_fetched=0 WHERE source_type='national_welfare'"
        )
        conn.commit()
        print(f"초기화 완료: {cur.rowcount}건 → detail_fetched=0")


if __name__ == "__main__":
    reset()