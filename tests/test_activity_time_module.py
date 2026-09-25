import tempfile
import unittest
from pathlib import Path

from src.activity_time_module import ActivityTimeModule
from src.backup_module import BackupModule
from src.json_repository import JsonRepository


class ActivityTimeModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.users_path = self.temp_dir / "user.json"
        self.backup_dir = self.temp_dir / "backup"
        repository = JsonRepository()
        repository.save(
            self.users_path,
            [{"name": "테스트 사용자", "total_hours": 12}],
        )
        self.module = ActivityTimeModule(
            users_path=str(self.users_path),
            backup_module=BackupModule(self.backup_dir, repository),
        )

    def test_add_hours_updates_total_and_creates_backup(self):
        result = self.module.add_service_hours(2)

        self.assertEqual(
            result,
            {
                "success": True,
                "previous_total_hours": 12,
                "added_hours": 2,
                "new_total_hours": 14,
            },
        )
        self.assertEqual(self.module.get_total_hours(), 14)
        self.assertEqual(len(list(self.backup_dir.glob("*/*.json"))), 1)

    def test_hours_outside_allowed_range_are_rejected(self):
        for hours in (0, 9, -1, 1.5, "2"):
            with self.subTest(hours=hours):
                result = self.module.add_service_hours(hours)
                self.assertEqual(result["error_code"], "E_INVALID_HOURS")

        self.assertEqual(self.module.get_total_hours(), 12)

    def test_missing_user_is_reported(self):
        result = self.module.add_service_hours(2, user_index=1)

        self.assertEqual(result["error_code"], "E_USER_NOT_FOUND")
        self.assertEqual(self.module.get_total_hours(), 12)

    def test_corrupted_user_data_uses_latest_backup(self):
        self.module.backup_module.backup([self.users_path])
        self.users_path.write_text("{broken", encoding="utf-8")

        self.assertEqual(self.module.get_total_hours(), 12)
        self.assertEqual(
            JsonRepository().load(self.users_path),
            [{"name": "테스트 사용자", "total_hours": 12}],
        )


if __name__ == "__main__":
    unittest.main()
