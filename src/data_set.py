import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

schema = {
    "user.json": [
        {"name": "홍길동", "total_hours": 12}
    ],
    "fac.json": [
        {
            "facility_id": 471131180002,
            "facility_name": "가상활동센터",
            "location": "경상북도 구미시 대학로 61",
            "contact": "054-123-4567"
        }
    ],
    "act.json": [
        {
            "activity_id": 47113118000201,
            "facility_id": 471131180002,
            "title": "도시 미화 작업",
            "description": "OO시 길거리 쓰레기 줍기 활동",
            "location": "경상북도 OO시 OOOOOO",
            "service_hours": 2,
            "status": 1,
            "rating": 4.5
        }
    ],
    "rev.json": [
        {
            "review_id": 1,
            "activity_id": 47113118000201,
            "rating": 5,
            "text": "가상 리뷰",
            "created_at": "2026-09-12T17:40:00"
        }
    ]
}

for filename, data in schema.items():
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{filename} 생성 완료")