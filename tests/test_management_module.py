import tempfile
import unittest
from pathlib import Path

from src.backup_module import BackupModule
from src.json_repository import JsonRepository
from src.management_module import ManagementModule


class ManagementModuleTests(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.facilities = root / "fac.json"
        self.activities = root / "act.json"
        repository = JsonRepository()
        repository.save(self.facilities, [{
            "facility_id": 1,
            "facility_name": "기존 시설",
            "location": "구미",
            "contact": "000",
        }])
        repository.save(self.activities, [{
            "activity_id": 10,
            "facility_id": 1,
            "title": "기존 활동",
            "location": "구미",
            "service_hours": 2,
            "rating": 0,
        }])
        self.module = ManagementModule(
            str(self.facilities),
            str(self.activities),
            repository,
            BackupModule(root / "backup", repository),
        )

    def test_register_facility(self):
        result = self.module.register_facility({
            "facility_id": 2,
            "facility_name": "새 시설",
            "location": "포항",
            "contact": "111",
        })
        self.assertTrue(result["success"])
        self.assertEqual(len(self.module.list_facilities()), 2)

    def test_register_activity_requires_existing_facility(self):
        result = self.module.register_activity({
            "activity_id": 11,
            "facility_id": 999,
            "title": "활동",
            "location": "구미",
            "service_hours": 2,
        })
        self.assertEqual(result["error_code"], "E_FACILITY_NOT_FOUND")

    def test_register_activity_and_reject_duplicate(self):
        activity = {
            "activity_id": 11,
            "facility_id": 1,
            "title": "새 활동",
            "location": "구미",
            "service_hours": 3,
        }
        self.assertTrue(self.module.register_activity(activity)["success"])
        duplicate = self.module.register_activity(activity)
        self.assertEqual(duplicate["error_code"], "E_DUPLICATE_ID")


if __name__ == "__main__":
    unittest.main()
