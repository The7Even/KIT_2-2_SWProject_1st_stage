import tempfile
import unittest
from datetime import date, timedelta
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
            region_resolver=lambda location: [
                {"code": "1234567890", "name": location}
            ],
        )

    def test_register_facility(self):
        result = self.module.register_facility({
            "facility_name": "새 시설",
            "location": "포항",
            "contact": "111",
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["facility_id"], 123456789001)
        self.assertEqual(len(self.module.list_facilities()), 2)

    def test_register_facility_assigns_smallest_available_suffix(self):
        repository = JsonRepository()
        repository.save(
            self.facilities,
            [
                {
                    "facility_id": 123456789001,
                    "facility_name": "시설 1",
                    "location": "구미",
                    "contact": "000",
                },
                {
                    "facility_id": 123456789003,
                    "facility_name": "시설 3",
                    "location": "구미",
                    "contact": "000",
                },
            ],
        )

        result = self.module.register_facility({
            "facility_name": "새 시설",
            "location": "구미",
            "contact": "111",
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["facility_id"], 123456789002)

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
            "schedule_date": (date.today() + timedelta(days=1)).isoformat(),
        }
        self.assertTrue(self.module.register_activity(activity)["success"])
        duplicate = self.module.register_activity(activity)
        self.assertEqual(duplicate["error_code"], "E_DUPLICATE_ID")

    def test_register_activity_assigns_id_when_not_provided(self):
        result = self.module.register_activity({
            "facility_id": 1,
            "title": "자동 등록 활동",
            "description": "설명",
            "location": "구미",
            "schedule_date": "2026-09-24",
            "service_hours": 2,
            "schedule_date": (date.today() + timedelta(days=1)).isoformat(),
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["activity_id"], 101)

    def test_register_activity_rejects_past_date(self):
        result = self.module.register_activity({
            "facility_id": 1,
            "title": "지난 활동",
            "location": "구미",
            "service_hours": 2,
            "schedule_date": "2000-01-01",
        })

        self.assertEqual(result["error_code"], "E_PAST_DATE")

    def test_complete_activity_cannot_be_repeated(self):
        activity = {
            "facility_id": 1,
            "title": "완료 활동",
            "location": "구미",
            "service_hours": 2,
            "schedule_date": (date.today() + timedelta(days=1)).isoformat(),
        }
        created = self.module.register_activity(activity)

        self.assertTrue(self.module.complete_activity(created["activity_id"])["success"])
        duplicate = self.module.complete_activity(created["activity_id"])
        self.assertEqual(duplicate["error_code"], "E_ALREADY_COMPLETED")


if __name__ == "__main__":
    unittest.main()
