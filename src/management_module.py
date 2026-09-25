"""시설과 봉사활동 등록·조회 관리 모듈."""

import os
from typing import Any

from .backup_module import BackupModule
from .json_repository import JsonRepository, JsonRepositoryError
from .region_code_client import LocalRegionCodeClient, RegionCodeApiError
from .app_logging import logger
from datetime import date, datetime


FACILITIES_FILE = os.path.join(os.path.dirname(__file__), "data", "fac.json")
ACTIVITIES_FILE = os.path.join(os.path.dirname(__file__), "data", "act.json")


class ManagementModule:
    """시설과 활동 데이터를 검증하고 JSON에 영속화합니다."""

    def __init__(
        self,
        facilities_path: str = FACILITIES_FILE,
        activities_path: str = ACTIVITIES_FILE,
        repository: JsonRepository | None = None,
        backup_module: BackupModule | None = None,
        region_client: LocalRegionCodeClient | None = None,
        region_resolver: Any | None = None,
    ):
        self.facilities_path = facilities_path
        self.activities_path = activities_path
        self.repository = repository or JsonRepository()
        self.backup_module = backup_module or BackupModule(repository=self.repository)
        self.region_client = region_client or LocalRegionCodeClient()
        self.region_resolver = region_resolver

    def list_facilities(self) -> list[dict[str, Any]]:
        return self._load_records(
            self.facilities_path,
            ("facility_id", "facility_name", "location", "contact"),
        )

    def list_activities(self) -> list[dict[str, Any]]:
        return self._load_records(
            self.activities_path,
            ("activity_id", "facility_id", "title", "location", "service_hours"),
        )

    def register_facility(self, facility: dict[str, Any]) -> dict[str, Any]:
        error = self._validate_facility(facility)
        if error:
            return error
        region_code = facility.get("region_code") or self._resolve_region_code(
            facility["location"]
        )
        if region_code is None:
            return self._failure(
                "E_REGION_NOT_FOUND",
                "주소에 해당하는 10자리 법정동코드를 찾을 수 없습니다.",
            )
        if self.region_resolver is None and not self.region_client.has_code(
            str(region_code)
        ):
            return self._failure(
                "E_REGION_NOT_FOUND",
                "선택한 법정동코드가 지역 데이터에 없습니다.",
            )
        facilities = self.list_facilities()
        try:
            facility_id = self._next_facility_id(region_code, facilities)
        except ValueError:
            return self._failure(
                "E_ID_EXHAUSTED",
                "해당 지역의 시설 ID를 더 이상 부여할 수 없습니다.",
            )
        if not self.backup_module.backup([self.facilities_path]):
            return self._failure("E_BACKUP_FAILED", "시설 등록 전 백업에 실패했습니다.")
        record = dict(facility)
        record.pop("region_code", None)
        record["facility_id"] = facility_id
        facilities.append(record)
        try:
            self.repository.save(self.facilities_path, facilities)
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))
        logger.info("facility_registered facility_id=%s", facility_id)
        return {"success": True, "facility_id": facility_id}

    def register_activity(self, activity: dict[str, Any]) -> dict[str, Any]:
        error = self._validate_activity(activity, validate_schedule=False)
        if error:
            return error
        facilities = self.list_facilities()
        if not any(item["facility_id"] == activity["facility_id"] for item in facilities):
            return self._failure("E_FACILITY_NOT_FOUND", "시설을 찾을 수 없습니다.")
        schedule_error = self._validate_schedule_date(activity.get("schedule_date"))
        if schedule_error:
            return schedule_error
        activities = self.list_activities()
        try:
            activity_id = activity.get("activity_id") or self._next_activity_id(
                activity["facility_id"],
                activities,
            )
        except ValueError:
            return self._failure(
                "E_ID_EXHAUSTED",
                "해당 시설의 활동 ID를 더 이상 부여할 수 없습니다.",
            )
        if any(item["activity_id"] == activity_id for item in activities):
            return self._failure("E_DUPLICATE_ID", "이미 등록된 활동 ID입니다.")
        if not self.backup_module.backup([self.activities_path]):
            return self._failure("E_BACKUP_FAILED", "활동 등록 전 백업에 실패했습니다.")
        record = dict(activity)
        record["activity_id"] = activity_id
        record.setdefault("status", 1)
        record.setdefault("rating", 0)
        activities.append(record)
        try:
            self.repository.save(self.activities_path, activities)
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))
        logger.info("activity_registered activity_id=%s", activity_id)
        return {"success": True, "activity_id": activity_id}

    def complete_activity(self, activity_id: int) -> dict[str, Any]:
        activities = self.list_activities()
        activity = next(
            (item for item in activities if item.get("activity_id") == activity_id),
            None,
        )
        if activity is None:
            return self._failure("E_ACTIVITY_NOT_FOUND", "활동을 찾을 수 없습니다.")
        if activity.get("completed_at"):
            return self._failure("E_ALREADY_COMPLETED", "이미 완료한 활동입니다.")
        if not self.backup_module.backup([self.activities_path]):
            return self._failure("E_BACKUP_FAILED", "활동 완료 전 백업에 실패했습니다.")
        activity["completed_at"] = datetime.now().isoformat(timespec="seconds")
        activity["status"] = 0
        try:
            self.repository.save(self.activities_path, activities)
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))
        logger.info("activity_completed activity_id=%s", activity_id)
        return {"success": True, "activity_id": activity_id}

    @staticmethod
    def _validate_facility(facility: Any) -> dict[str, Any] | None:
        if not isinstance(facility, dict):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 데이터가 올바르지 않습니다.")
        required = ("facility_name", "location", "contact")
        if any(not facility.get(field) for field in required):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 필수값을 입력해 주세요.")
        return None

    def _resolve_region_code(self, location: str) -> str | None:
        try:
            regions = (
                self.region_resolver(location)
                if self.region_resolver is not None
                else self.region_client.find_regions(location)
            )
        except RegionCodeApiError as error:
            print(f"[오류] 법정동코드 조회 실패: {error}")
            return None

        for region in regions:
            code = str(region.get("code", "")) if isinstance(region, dict) else ""
            if code.isdigit() and len(code) == 10:
                return code
        return None

    @staticmethod
    def _next_facility_id(
        region_code: str,
        facilities: list[dict[str, Any]],
    ) -> int:
        used_suffixes = {
            int(str(item["facility_id"])[10:])
            for item in facilities
            if str(item.get("facility_id", "")).startswith(region_code)
            and str(item.get("facility_id", ""))[10:].isdigit()
            and len(str(item["facility_id"])) == 12
            and 1 <= int(str(item["facility_id"])[10:]) <= 99
        }
        suffix = next(
            (candidate for candidate in range(1, 100) if candidate not in used_suffixes),
            None,
        )
        if suffix is None:
            raise ValueError(f"시설 ID 할당 한도 초과: {region_code}")
        return int(f"{region_code}{suffix:02d}")

    @staticmethod
    def _validate_activity(
        activity: Any,
        validate_schedule: bool = True,
    ) -> dict[str, Any] | None:
        if not isinstance(activity, dict):
            return ManagementModule._failure("E_INVALID_INPUT", "활동 데이터가 올바르지 않습니다.")
        required = ("facility_id", "title", "location", "service_hours")
        if any(not activity.get(field) and field != "service_hours" for field in required):
            return ManagementModule._failure("E_INVALID_INPUT", "활동 필수값을 입력해 주세요.")
        if (
            activity.get("activity_id") is not None
            and not ManagementModule._positive_integer(activity.get("activity_id"))
        ):
            return ManagementModule._failure("E_INVALID_INPUT", "활동 ID가 올바르지 않습니다.")
        if not ManagementModule._positive_integer(activity.get("facility_id")):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 ID가 올바르지 않습니다.")
        hours = activity.get("service_hours")
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 8:
            return ManagementModule._failure("E_INVALID_HOURS", "인정시간은 1~8시간이어야 합니다.")
        if not validate_schedule:
            return None
        return ManagementModule._validate_schedule_date(activity.get("schedule_date"))

    @staticmethod
    def _validate_schedule_date(schedule_date: Any) -> dict[str, Any] | None:
        if not isinstance(schedule_date, str) or not schedule_date.strip():
            return ManagementModule._failure("E_INVALID_DATE", "활동일을 입력해 주세요.")
        try:
            parsed_date = date.fromisoformat(schedule_date)
        except ValueError:
            return ManagementModule._failure("E_INVALID_DATE", "활동일 형식이 올바르지 않습니다.")
        if parsed_date < date.today():
            return ManagementModule._failure("E_PAST_DATE", "과거 날짜의 활동은 등록할 수 없습니다.")
        return None

    @staticmethod
    def _next_activity_id(
        facility_id: int,
        activities: list[dict[str, Any]],
    ) -> int:
        prefix = str(facility_id)
        used_suffixes = {
            int(str(item["activity_id"])[len(prefix):])
            for item in activities
            if str(item.get("activity_id", "")).startswith(prefix)
            and str(item.get("activity_id", ""))[len(prefix):].isdigit()
            and len(str(item["activity_id"])) == len(prefix) + 2
            and 1 <= int(str(item["activity_id"])[len(prefix):]) <= 99
        }
        suffix = next(
            (candidate for candidate in range(1, 100) if candidate not in used_suffixes),
            None,
        )
        if suffix is None:
            raise ValueError(f"활동 ID 할당 한도 초과: {facility_id}")
        return int(f"{prefix}{suffix:02d}")

    def _load_records(self, path: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        try:
            return self.backup_module.load_records_with_backup(path, fields)
        except JsonRepositoryError as error:
            print(f"[오류] 관리 데이터 로드 실패: {error}")
            return []

    @staticmethod
    def _positive_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    @staticmethod
    def _failure(error_code: str, message: str) -> dict[str, Any]:
        return {"success": False, "error_code": error_code, "message": message}
