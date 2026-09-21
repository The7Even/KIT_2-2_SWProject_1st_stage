import tempfile
import unittest
from pathlib import Path

from src.backup_module import BackupModule
from src.json_repository import JsonRepository
from src.review_module import ReviewModule


class ReviewModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.reviews_path = self.temp_dir / "rev.json"
        self.activities_path = self.temp_dir / "act.json"
        self.backup_dir = self.temp_dir / "backup"
        repository = JsonRepository()
        repository.save(
            self.reviews_path,
            [{
                "review_id": 1,
                "activity_id": 10,
                "rating": 5,
                "text": "기존 후기",
            }],
        )
        repository.save(
            self.activities_path,
            [{
                "activity_id": 10,
                "title": "활동",
                "rating": 5.0,
            }],
        )
        self.module = ReviewModule(
            reviews_path=str(self.reviews_path),
            activities_path=str(self.activities_path),
            backup_module=BackupModule(self.backup_dir, repository),
        )

    def test_submit_review_saves_review_and_updates_average_rating(self):
        result = self.module.submit_review({
            "activity_id": 10,
            "rating": 3,
            "text": "  새 후기  ",
        })

        self.assertEqual(result["success"], True)
        self.assertEqual(result["review_id"], 2)
        self.assertEqual(result["new_rating"], 4.0)
        self.assertEqual(len(self.module.get_reviews(10)), 2)
        activity = JsonRepository().load(self.activities_path)[0]
        self.assertEqual(activity["rating"], 4.0)
        self.assertEqual(len(list(self.backup_dir.glob("*/*.json"))), 2)

    def test_invalid_rating_is_rejected_without_mutation(self):
        result = self.module.submit_review({
            "activity_id": 10,
            "rating": 5.1,
            "text": "잘못된 별점",
        })

        self.assertEqual(result["error_code"], "E_INVALID_RATING")
        self.assertEqual(len(self.module.get_reviews(10)), 1)

    def test_unknown_activity_is_rejected(self):
        result = self.module.submit_review({
            "activity_id": 999,
            "rating": 4,
            "text": "없는 활동",
        })

        self.assertEqual(result["error_code"], "E_ACTIVITY_NOT_FOUND")
        self.assertEqual(len(self.module.get_reviews(10)), 1)


if __name__ == "__main__":
    unittest.main()
