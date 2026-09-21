"""행정구역 코드 API 연동을 위한 어댑터."""

import os
from typing import Any

import requests


class RegionCodeApiError(Exception):
    """행정구역 코드 API 요청 또는 응답 처리 오류입니다."""


class RegionCodeClient:
    """외부 행정구역 코드 API를 프로젝트 내부 형식으로 변환합니다.

    API별 응답 차이는 ``ADMIN_CODE_ITEMS_FIELD``, ``ADMIN_CODE_FIELD``,
    ``ADMIN_CODE_NAME_FIELD`` 환경변수로 조정할 수 있습니다.
    """

    def __init__(
        self,
        base_url: str | None = None,
        service_key: str | None = None,
        timeout: float = 5.0,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url or os.getenv("ADMIN_CODE_API_URL")
        self.service_key = service_key or os.getenv("ADMIN_CODE_API_KEY")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.query_parameter = os.getenv("ADMIN_CODE_QUERY_PARAM", "query")
        self.key_parameter = os.getenv("ADMIN_CODE_KEY_PARAM", "serviceKey")
        self.items_field = os.getenv("ADMIN_CODE_ITEMS_FIELD", "data")
        self.code_field = os.getenv("ADMIN_CODE_FIELD", "code")
        self.name_field = os.getenv("ADMIN_CODE_NAME_FIELD", "name")

    def find_regions(self, region_name: str) -> list[dict[str, str]]:
        """지역명으로 API를 조회하고 ``code``·``name`` 목록을 반환합니다."""
        if not isinstance(region_name, str):
            raise RegionCodeApiError("지역명은 문자열이어야 합니다.")
        query = region_name.strip()
        if not query:
            raise RegionCodeApiError("지역명은 비어 있을 수 없습니다.")
        if not self.base_url:
            raise RegionCodeApiError("ADMIN_CODE_API_URL이 설정되지 않았습니다.")

        params: dict[str, str] = {self.query_parameter: query}
        if self.service_key:
            params[self.key_parameter] = self.service_key

        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise RegionCodeApiError("행정구역 코드 API 요청에 실패했습니다.") from error

        records = self._extract_records(payload)
        regions: list[dict[str, str]] = []
        for record in records:
            code = record.get(self.code_field)
            name = record.get(self.name_field)
            if code is None or name is None:
                continue
            regions.append({"code": str(code), "name": str(name)})
        return regions

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            records = payload.get(self.items_field)
            if records is None and isinstance(payload.get("items"), list):
                records = payload["items"]
        else:
            records = None

        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise RegionCodeApiError(
                f"API 응답에서 '{self.items_field}' 형식의 지역 목록을 찾을 수 없습니다."
            )
        return records
