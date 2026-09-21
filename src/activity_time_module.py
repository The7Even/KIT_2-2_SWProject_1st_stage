"""사용자 누적 봉사시간 관리 모듈."""

import os
from typing import Any

from .backup_module import BackupModule
from .json_repository import JsonRepository, JsonRepositoryError


USERS_FILE = os.path.join(os.path.dirname(__file__), "data", "user.json")


class ActivityTimeModule:
    """단일 사용자 기준으로 봉사시간을 검증하고 누적합니다."""

    def __init__(
        self,
        users_path: str = USERS_FILE,
        repository: JsonRepository | None = None,
        backup_module: BackupModule | None = None,
    ):
        self.users_path = users_path
        self.repository = repository or JsonRepository()
        self.backup_module = backup_module or BackupModule(repository=self.repository)

    def get_total_hours(self, user_index: int = 0) -> int | None:
        """사용자의 누적 봉사시간을 반환합니다."""
        users = self._load_users()
        if users is None or not self._is_valid_user_index(users, user_index):
            return None
        return users[user_index]["total_hours"]

    def add_service_hours(
        self,
        hours: int,
        user_index: int = 0,
    ) -> dict[str, Any]:
        """유효한 활동시간을 사용자 누적시간에 더합니다."""
        validation_error = self._validate_hours(hours)
        if validation_error is not None:
            return validation_error

        users = self._load_users()
        if users is None:
            return self._failure(
                "E_FAILED_UPDATE",
                "사용자 데이터를 불러올 수 없습니다.",
            )
        if not self._is_valid_user_index(users, user_index):
            return self._failure(
                "E_USER_NOT_FOUND",
                "사용자를 찾을 수 없습니다.",
            )

        current_hours = users[user_index].get("total_hours")
        if not self._is_non_negative_integer(current_hours):
            return self._failure(
                "E_INVALID_DATA",
                "기존 누적 봉사시간 데이터가 올바르지 않습니다.",
            )

        if not self.backup_module.backup([self.users_path]):
            return self._failure(
                "E_BACKUP_FAILED",
                "봉사시간 갱신 전 데이터 백업에 실패했습니다.",
            )

        updated_hours = current_hours + hours
        users[user_index]["total_hours"] = updated_hours
        try:
            self.repository.save(self.users_path, users)
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))

        return {
            "success": True,
            "previous_total_hours": current_hours,
            "added_hours": hours,
            "new_total_hours": updated_hours,
        }

    def _load_users(self) -> list[dict[str, Any]] | None:
        try:
            return self.repository.load_records(
                self.users_path,
                required_fields=("name", "total_hours"),
            )
        except JsonRepositoryError as error:
            print(f"[오류] 사용자 데이터 로드 실패: {error}")
            return None

    @staticmethod
    def _validate_hours(hours: Any) -> dict[str, Any] | None:
        if (
            isinstance(hours, bool)
            or not isinstance(hours, int)
            or not 1 <= hours <= 8
        ):
            return ActivityTimeModule._failure(
                "E_INVALID_HOURS",
                "활동시간은 1시간 이상 8시간 이하의 정수여야 합니다.",
            )
        return None

    @staticmethod
    def _is_non_negative_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @staticmethod
    def _is_valid_user_index(users: list[dict[str, Any]], user_index: int) -> bool:
        return (
            isinstance(user_index, int)
            and not isinstance(user_index, bool)
            and 0 <= user_index < len(users)
        )

    @staticmethod
    def _failure(error_code: str, message: str) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": error_code,
            "message": message,
        }
