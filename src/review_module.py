"""활동 후기 등록·조회와 활동 평균 평점 갱신 모듈."""

from datetime import datetime
import os
from pathlib import Path
from typing import Any

from .backup_module import BackupModule
from .json_repository import JsonRepository, JsonRepositoryError


REVIEWS_FILE = os.path.join(os.path.dirname(__file__), "data", "rev.json")
ACTIVITIES_FILE = os.path.join(os.path.dirname(__file__), "data", "act.json")


class ReviewModule:
    """후기 저장과 활동 평점 갱신을 함께 처리합니다."""

    def __init__(
        self,
        reviews_path: str = REVIEWS_FILE,
        activities_path: str = ACTIVITIES_FILE,
        repository: JsonRepository | None = None,
        backup_module: BackupModule | None = None,
    ):
        self.reviews_path = reviews_path
        self.activities_path = activities_path
        self.repository = repository or JsonRepository()
        self.backup_module = backup_module or BackupModule(repository=self.repository)

    def get_reviews(self, activity_id: int) -> list[dict[str, Any]]:
        """특정 활동의 후기 목록을 반환합니다."""
        if not self._is_valid_activity_id(activity_id):
            return []

        try:
            reviews = self.repository.load_records(
                self.reviews_path,
                required_fields=("review_id", "activity_id", "rating", "text"),
            )
        except JsonRepositoryError as error:
            print(f"[오류] 후기 데이터 로드 실패: {error}")
            return []

        return [
            review for review in reviews
            if review.get("activity_id") == activity_id
        ]

    def submit_review(self, review: dict[str, Any]) -> dict[str, Any]:
        """후기를 저장하고 해당 활동의 평균 평점을 갱신합니다."""
        validation_error = self._validate_review(review)
        if validation_error is not None:
            return validation_error

        activity_id = review["activity_id"]
        try:
            reviews = self.repository.load_records(
                self.reviews_path,
                required_fields=("review_id", "activity_id", "rating", "text"),
            )
            activities = self.repository.load_records(
                self.activities_path,
                required_fields=("activity_id", "rating"),
            )
        except JsonRepositoryError as error:
            return self._failure("E_FAILED_UPDATE", str(error))

        activity = next(
            (item for item in activities if item.get("activity_id") == activity_id),
            None,
        )
        if activity is None:
            return self._failure(
                "E_ACTIVITY_NOT_FOUND",
                "후기를 작성할 활동을 찾을 수 없습니다.",
            )

        if not self.backup_module.backup([self.reviews_path, self.activities_path]):
            return self._failure(
                "E_BACKUP_FAILED",
                "후기 등록 전 데이터 백업에 실패했습니다.",
            )

        original_reviews = [dict(item) for item in reviews]
        original_activities = [dict(item) for item in activities]
        new_review = dict(review)
        new_review["review_id"] = self._next_review_id(reviews)
        new_review["text"] = review["text"].strip()
        new_review["created_at"] = review.get(
            "created_at",
            datetime.now().isoformat(timespec="seconds"),
        )
        reviews.append(new_review)

        ratings = [
            item["rating"]
            for item in reviews
            if item.get("activity_id") == activity_id
        ]
        activity["rating"] = round(sum(ratings) / len(ratings), 2)

        try:
            self.repository.save(self.reviews_path, reviews)
            self.repository.save(self.activities_path, activities)
        except JsonRepositoryError as error:
            self._restore(original_reviews, original_activities)
            return self._failure("E_FAILED_UPDATE", str(error))

        return {
            "success": True,
            "review_id": new_review["review_id"],
            "new_rating": activity["rating"],
        }

    @staticmethod
    def _validate_review(review: Any) -> dict[str, Any] | None:
        if not isinstance(review, dict):
            return ReviewModule._failure(
                "E_INVALID_INPUT",
                "후기 데이터는 객체 형식이어야 합니다.",
            )

        activity_id = review.get("activity_id")
        rating = review.get("rating")
        text = review.get("text")
        if not ReviewModule._is_valid_activity_id(activity_id):
            return ReviewModule._failure(
                "E_INVALID_INPUT",
                "활동 ID가 올바르지 않습니다.",
            )
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            return ReviewModule._failure(
                "E_INVALID_RATING",
                "별점은 1에서 5 사이의 정수여야 합니다.",
            )
        if not isinstance(text, str) or not text.strip():
            return ReviewModule._failure(
                "E_INVALID_INPUT",
                "후기 내용을 입력해 주세요.",
            )
        return None

    @staticmethod
    def _is_valid_activity_id(activity_id: Any) -> bool:
        return isinstance(activity_id, int) and not isinstance(activity_id, bool) and activity_id > 0

    @staticmethod
    def _next_review_id(reviews: list[dict[str, Any]]) -> int:
        identifiers = [
            item["review_id"]
            for item in reviews
            if isinstance(item.get("review_id"), int)
            and not isinstance(item.get("review_id"), bool)
        ]
        return max(identifiers, default=0) + 1

    def _restore(
        self,
        reviews: list[dict[str, Any]],
        activities: list[dict[str, Any]],
    ) -> None:
        self.repository.save(self.reviews_path, reviews)
        self.repository.save(self.activities_path, activities)

    @staticmethod
    def _failure(error_code: str, message: str) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": error_code,
            "message": message,
        }
