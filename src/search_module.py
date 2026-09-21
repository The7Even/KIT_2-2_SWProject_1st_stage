import os
from collections.abc import Callable

from .region_code_client import RegionCodeApiError, RegionCodeClient
from .json_repository import JsonRepository, JsonRepositoryError

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "act.json")


class SearchModule:
    def __init__(
        self,
        data_path: str = DATA_FILE,
        repository: JsonRepository | None = None,
        region_client: RegionCodeClient | None = None,
        region_resolver: Callable[[str], list[dict[str, str]]] | None = None,
    ):
        self.data_path = data_path
        self.repository = repository or JsonRepository()
        self.region_client = region_client
        self.region_resolver = region_resolver

    def _load_activities(self) -> list[dict]:
        """act.json 파일에서 활동 데이터를 로드합니다."""
        try:
            return self.repository.load_records(
                self.data_path,
                required_fields=("title", "location"),
            )
        except JsonRepositoryError as e:
            print(f"[오류] 데이터 로드 실패: {e}")
            return []

    def search_act(
        self,
        search_query: str = "",
        region_code: str | None = None,
    ) -> list[dict]:
        """
        활동명·장소 또는 행정구역 코드 기반으로 봉사활동을 검색합니다.
        (설계서 VI. 2. IF-001 규격 준수)
        """
        if not isinstance(search_query, str):
            print("[오류] 검색어는 문자열이어야 합니다. (E_INPUT_NOT_FOUND)")
            return []

        activities = self._load_activities()
        query = search_query.strip()
        if region_code is not None and not isinstance(region_code, str):
            print("[오류] 지역 코드는 문자열이어야 합니다. (E_INPUT_NOT_FOUND)")
            return []
        normalized_region_code = region_code.strip() if region_code is not None else None

        if region_code is not None and not normalized_region_code:
            print("[오류] 지역 코드는 비어 있을 수 없습니다. (E_INPUT_NOT_FOUND)")
            return []

        # 테스트 계획: 공백 입력 시 전체 목록 반환
        if not query and not normalized_region_code:
            return activities

        # 활동명(title) 또는 장소(location)에 검색어가 포함된 항목 필터링
        filtered_results = [
            act for act in activities
            if (
                not query
                or query.casefold() in str(act.get("title", "")).casefold()
                or query.casefold() in str(act.get("location", "")).casefold()
            )
            and (
                not normalized_region_code
                or str(act.get("region_code", "")) == normalized_region_code
            )
        ]

        # 테스트 계획 및 오류 코드: 검색 결과가 없을 경우
        if not filtered_results:
            target = query or normalized_region_code
            print(f"[안내] '{target}'에 대한 검색 결과가 없습니다. (E_NO_RESULT)")
            return []

        return filtered_results

    def search_by_region(self, region_name: str) -> list[dict]:
        """지역명으로 코드를 조회한 뒤 지역 코드 기반으로 활동을 검색합니다."""
        if not isinstance(region_name, str) or not region_name.strip():
            print("[오류] 지역명을 입력해 주세요. (E_INPUT_NOT_FOUND)")
            return []

        try:
            if self.region_resolver is not None:
                regions = self.region_resolver(region_name)
            elif self.region_client is not None:
                regions = self.region_client.find_regions(region_name)
            else:
                raise RegionCodeApiError(
                    "지역 코드 조회기가 설정되지 않았습니다."
                )
        except RegionCodeApiError as error:
            print(f"[오류] 지역 코드 조회 실패: {error}")
            return []

        codes = {
            str(region.get("code"))
            for region in regions
            if isinstance(region, dict) and region.get("code") is not None
        }
        if not codes:
            print(f"[안내] '{region_name.strip()}'에 대한 지역 코드가 없습니다. (E_NO_RESULT)")
            return []

        activities = self._load_activities()
        results = [
            activity
            for activity in activities
            if str(activity.get("region_code", "")) in codes
        ]
        if not results:
            print(f"[안내] '{region_name.strip()}' 지역 활동이 없습니다. (E_NO_RESULT)")
        return results