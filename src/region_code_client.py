"""행정구역 코드 API 연동을 위한 어댑터."""

import os
import csv
from pathlib import Path
from typing import Any

import requests


DEFAULT_ADMIN_CODE_URL = (
    "https://api.odcloud.kr/api/15123287/v1/"
    "uddi:d6c67241-a722-48c4-8041-d66ff243cf57"
)
DEFAULT_REGION_CSV = Path(__file__).parent / "data" / "법정동코드_20260813.csv"


class RegionCodeApiError(Exception):
    """행정구역 코드 API 요청 또는 응답 처리 오류입니다."""


class LocalRegionCodeClient:
    """로컬 법정동코드 CSV에서 주소에 맞는 지역 코드를 찾습니다."""

    def __init__(
        self,
        csv_path: str | os.PathLike[str] = DEFAULT_REGION_CSV,
        encoding: str = "cp949",
    ):
        self.csv_path = Path(csv_path)
        self.encoding = encoding
        self._records: list[dict[str, str]] | None = None

    def list_provinces(self) -> list[dict[str, str]]:
        return [
            {"code": record["code"], "name": record["name"]}
            for record in self._load_records()
            if record["level"] == "province"
        ]

    def list_cities(self, province_code: str) -> list[dict[str, str]]:
        records = self._load_records()
        city_records = [
            record
            for record in records
            if record["level"] == "city"
            and record["parent_code"] == province_code
        ]
        parent_names = {
            record["name"]
            for record in city_records
            if any(
                child["level"] == "city"
                and child["name"].startswith(record["name"] + " ")
                for child in city_records
            )
        }
        # 시 아래에 구가 있으면 상위 시는 선택지에서 제외하고 구를 노출합니다.
        visible_records = [
            record for record in city_records if record["name"] not in parent_names
        ]
        return [
            {"code": record["code"], "name": record["name"]}
            for record in visible_records
        ]

    def list_districts(self, city_code: str) -> list[dict[str, str]]:
        records = self._load_records()
        city_name = self._name_for_code(city_code, records)
        return [
            {"code": record["code"], "name": record["name"]}
            for record in records
            if record["level"] == "district"
            and record["name"].startswith(city_name + " ")
        ]

    def has_code(self, code: str) -> bool:
        return any(record["code"] == code for record in self._load_records())

    def find_regions(self, address: str) -> list[dict[str, str]]:
        if not isinstance(address, str) or not address.strip():
            raise RegionCodeApiError("주소는 비어 있을 수 없습니다.")
        if not self.csv_path.is_file():
            raise RegionCodeApiError(f"법정동코드 파일이 없습니다: {self.csv_path}")

        normalized_address = " ".join(address.split())
        matches = []
        for record in self._load_records():
            code = record["code"]
            name = record["name"]
            if (
                name
                and (
                    name in normalized_address
                    or normalized_address in name
                )
            ):
                matches.append({"code": code, "name": name})

        return sorted(matches, key=lambda region: len(region["name"]), reverse=True)

    def _load_records(self) -> list[dict[str, str]]:
        if self._records is not None:
            return self._records
        if not self.csv_path.is_file():
            raise RegionCodeApiError(f"법정동코드 파일이 없습니다: {self.csv_path}")

        try:
            with self.csv_path.open("r", encoding=self.encoding, newline="") as file:
                source_records = list(csv.DictReader(file))
        except (OSError, UnicodeError, csv.Error) as error:
            raise RegionCodeApiError("법정동코드 파일을 읽을 수 없습니다.") from error

        required = {"법정동코드", "법정동명", "폐지여부"}
        if not source_records or not required.issubset(source_records[0]):
            raise RegionCodeApiError("법정동코드 파일의 컬럼이 올바르지 않습니다.")

        records: list[dict[str, str]] = []
        for source in source_records:
            code = str(source.get("법정동코드", "")).strip()
            name = " ".join(str(source.get("법정동명", "")).split())
            if (
                len(code) != 10
                or not code.isdigit()
                or str(source.get("폐지여부", "")).strip() == "폐지"
                or not name
            ):
                continue
            if code[2:] == "00000000":
                level, parent_code = "province", ""
            elif code[5:] == "00000":
                level, parent_code = "city", code[:2] + "00000000"
            else:
                level, parent_code = "district", code[:5] + "00000"
            records.append({
                "code": code,
                "name": name,
                "level": level,
                "parent_code": parent_code,
            })
        self._records = records
        return records

    @staticmethod
    def _name_for_code(
        code: str,
        records: list[dict[str, str]],
    ) -> str:
        return next(
            (record["name"] for record in records if record["code"] == code),
            "",
        )


class RegionCodeClient:
    """외부 행정구역 코드 API를 프로젝트 내부 형식으로 변환합니다.

    API별 응답 차이는 ``ADMIN_CODE_ITEMS_FIELD``, ``ADMIN_CODE_FIELD``,
    ``ADMIN_CODE_NAME_FIELD`` 환경변수로 조정할 수 있습니다.
    """

    def __init__(
        self,
        base_url: str | None | object = ...,
        service_key: str | None = None,
        timeout: float = 5.0,
        session: requests.Session | None = None,
    ):
        if base_url is ...:
            self.base_url = os.getenv("ADMIN_CODE_API_URL", DEFAULT_ADMIN_CODE_URL)
        else:
            self.base_url = base_url
        self.service_key = (
            service_key
            or os.getenv("ADMIN_CODE_API_KEY")
            or os.getenv("ODCLOUD_SERVICE_KEY")
        )
        self.timeout = timeout
        self.session = session or requests.Session()
        self.query_parameter = os.getenv("ADMIN_CODE_QUERY_PARAM", "searchKeyword")
        self.key_parameter = os.getenv("ADMIN_CODE_KEY_PARAM", "serviceKey")
        self.items_field = os.getenv("ADMIN_CODE_ITEMS_FIELD", "data")
        self.code_field = os.getenv("ADMIN_CODE_FIELD", "법정동코드")
        self.name_field = os.getenv("ADMIN_CODE_NAME_FIELD", "법정동명")

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
