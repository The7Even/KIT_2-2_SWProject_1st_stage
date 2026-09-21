"""시설과 봉사활동 등록·조회 관리 모듈."""

import os
from typing import Any

from .backup_module import BackupModule
from .json_repository import JsonRepository, JsonRepositoryError


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
    ):
        self.facilities_path = facilities_path
        self.activities_path = activities_path
        self.repository = repository or JsonRepository()
        self.backup_module = backup_module or BackupModule(repository=self.repository)

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
        facilities = self.list_facilities()
        facility_id = facility["facility_id"]
        if any(item["facility_id"] == facility_id for item in facilities):
            return self._failure("E_DUPLICATE_ID", "이미 등록된 시설 ID입니다.")
        if not self.backup_module.backup([self.facilities_path]):
            return self._failure("E_BACKUP_FAILED", "시설 등록 전 백업에 실패했습니다.")
        facilities.append(dict(facility))
        try:
            self.repository.save(self.facilities_path, facilities)
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))
        return {"success": True, "facility_id": facility_id}

    def register_activity(self, activity: dict[str, Any]) -> dict[str, Any]:
        error = self._validate_activity(activity)
        if error:
            return error
        facilities = self.list_facilities()
        if not any(item["facility_id"] == activity["facility_id"] for item in facilities):
            return self._failure("E_FACILITY_NOT_FOUND", "시설을 찾을 수 없습니다.")
        activities = self.list_activities()
        activity_id = activity["activity_id"]
        if any(item["activity_id"] == activity_id for item in activities):
            return self._failure("E_DUPLICATE_ID", "이미 등록된 활동 ID입니다.")
        if not self.backup_module.backup([self.activities_path]):
            return self._failure("E_BACKUP_FAILED", "활동 등록 전 백업에 실패했습니다.")
        record = dict(activity)
        record.setdefault("status", 1)
        record.setdefault("rating", 0)
        activities.append(record)
        try:
            self.repository.save(self.activities_path, activities)
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))
        return {"success": True, "activity_id": activity_id}

    @staticmethod
    def _validate_facility(facility: Any) -> dict[str, Any] | None:
        if not isinstance(facility, dict):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 데이터가 올바르지 않습니다.")
        required = ("facility_id", "facility_name", "location", "contact")
        if any(not facility.get(field) for field in required):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 필수값을 입력해 주세요.")
        if not ManagementModule._positive_integer(facility["facility_id"]):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 ID가 올바르지 않습니다.")
        return None

    @staticmethod
    def _validate_activity(activity: Any) -> dict[str, Any] | None:
        if not isinstance(activity, dict):
            return ManagementModule._failure("E_INVALID_INPUT", "활동 데이터가 올바르지 않습니다.")
        required = ("activity_id", "facility_id", "title", "location", "service_hours")
        if any(not activity.get(field) and field != "service_hours" for field in required):
            return ManagementModule._failure("E_INVALID_INPUT", "활동 필수값을 입력해 주세요.")
        if not ManagementModule._positive_integer(activity.get("activity_id")):
            return ManagementModule._failure("E_INVALID_INPUT", "활동 ID가 올바르지 않습니다.")
        if not ManagementModule._positive_integer(activity.get("facility_id")):
            return ManagementModule._failure("E_INVALID_INPUT", "시설 ID가 올바르지 않습니다.")
        hours = activity.get("service_hours")
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 8:
            return ManagementModule._failure("E_INVALID_HOURS", "인정시간은 1~8시간이어야 합니다.")
        return None

    def _load_records(self, path: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        try:
            return self.repository.load_records(path, fields)
        except JsonRepositoryError as error:
            print(f"[오류] 관리 데이터 로드 실패: {error}")
            return []

    @staticmethod
    def _positive_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    @staticmethod
    def _failure(error_code: str, message: str) -> dict[str, Any]:
        return {"success": False, "error_code": error_code, "message": message}
