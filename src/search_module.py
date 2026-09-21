import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "act.json")


class SearchModule:
    def __init__(self, data_path: str = DATA_FILE):
        self.data_path = data_path

    def _load_activities(self) -> list[dict]:
        """act.json 파일에서 활동 데이터를 로드합니다."""
        if not os.path.exists(self.data_path):
            print(f"[경고] 데이터 파일이 존재하지 않습니다: {self.data_path}")
            return []

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[오류] 데이터 로드 실패: {e}")
            return []

    def search_act(self, search_query: str) -> list[dict]:
        """
        활동명 또는 활동 장소 기반으로 봉사활동을 검색합니다.
        (설계서 VI. 2. IF-001 규격 준수)
        """
        activities = self._load_activities()
        query = search_query.strip()

        # 테스트 계획: 공백 입력 시 전체 목록 반환
        if not query:
            return activities

        # 활동명(title) 또는 장소(location)에 검색어가 포함된 항목 필터링
        filtered_results = [
            act for act in activities
            if query.lower() in act.get("title", "").lower()
               or query.lower() in act.get("location", "").lower()
        ]

        # 테스트 계획 및 오류 코드: 검색 결과가 없을 경우
        if not filtered_results:
            print(f"[안내] '{query}'에 대한 검색 결과가 없습니다. (E_NO_RESULT)")
            return []

        return filtered_results