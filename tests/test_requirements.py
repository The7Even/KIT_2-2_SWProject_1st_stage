import tempfile
import unittest
from pathlib import Path

from src.activity_time_module import ActivityTimeModule
from src.backup_module import BackupModule
from src.json_repository import JsonRepository, JsonRepositoryError
from src.management_module import ManagementModule
from src.review_module import ReviewModule
from src.search_module import SearchModule


class RequirementsCoverageTests(unittest.TestCase):
    def test_corrupted_json_is_rejected(self):
        path = Path(tempfile.mkdtemp()) / "broken.json"
        path.write_text("{broken", encoding="utf-8")

        with self.assertRaises(JsonRepositoryError):
            JsonRepository().load(path)

    def test_backup_failure_does_not_report_success(self):
        root = Path(tempfile.mkdtemp())
        source = root / "data.json"
        JsonRepository().save(source, [{"value": 1}])

        self.assertFalse(BackupModule(root / "backup").backup([root / "missing.json"]))

    def test_search_requires_title_and_location_fields(self):
        root = Path(tempfile.mkdtemp())
        path = root / "act.json"
        JsonRepository().save(path, [{"title": "활동"}])

        self.assertEqual(SearchModule(str(path)).search_act("활동"), [])

    def test_review_rejects_blank_text(self):
        root = Path(tempfile.mkdtemp())
        reviews = root / "rev.json"
        activities = root / "act.json"
        repository = JsonRepository()
        repository.save(reviews, [])
        repository.save(activities, [{"activity_id": 1, "rating": 0}])
        module = ReviewModule(str(reviews), str(activities))

        result = module.submit_review({
            "activity_id": 1,
            "rating": 5,
            "text": "   ",
        })

        self.assertEqual(result["error_code"], "E_INVALID_INPUT")

    def test_management_rejects_missing_required_values(self):
        root = Path(tempfile.mkdtemp())
        facilities = root / "fac.json"
        activities = root / "act.json"
        repository = JsonRepository()
        repository.save(facilities, [])
        repository.save(activities, [])
        module = ManagementModule(str(facilities), str(activities))

        result = module.register_facility({
            "facility_id": 1,
            "facility_name": "",
            "location": "구미",
            "contact": "000",
        })

        self.assertEqual(result["error_code"], "E_INVALID_INPUT")

    def test_activity_time_rejects_invalid_existing_total(self):
        root = Path(tempfile.mkdtemp())
        users = root / "user.json"
        JsonRepository().save(users, [{"name": "사용자", "total_hours": -1}])
        module = ActivityTimeModule(str(users))

        result = module.add_service_hours(1)

        self.assertEqual(result["error_code"], "E_INVALID_DATA")


if __name__ == "__main__":
    unittest.main()
