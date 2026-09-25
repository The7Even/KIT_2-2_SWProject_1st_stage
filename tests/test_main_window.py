import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow
from src.activity_time_module import ActivityTimeModule
from src.backup_module import BackupModule
from src.json_repository import JsonRepository
from src.management_module import ManagementModule
from src.review_module import ReviewModule
from src.search_module import SearchModule


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_builds_title_and_search_pages(self):
        window = MainWindow()

        self.assertEqual(window.pages.count(), 5)
        self.assertEqual(window.windowTitle(), "굿포인트")
        self.assertEqual(window.total_hours_label.text(), "12시간")

    def test_search_action_populates_results(self):
        window = MainWindow()
        window.search_input.setText("도시")
        window.search_activities()

        self.assertEqual(window.results_list.count(), 1)
        self.assertIn("도시 미화 작업", window.results_list.item(0).text())

    def test_completing_activity_adds_its_recognized_hours_and_opens_review(self):
        root = Path(tempfile.mkdtemp())
        repository = JsonRepository()
        reviews = root / "rev.json"
        activities = root / "act.json"
        users = root / "user.json"
        repository.save(reviews, [])
        repository.save(
            activities,
            [{
                "activity_id": 1,
                "facility_id": 1,
                "title": "인정시간 활동",
                "location": "구미",
                "service_hours": 3,
                "rating": 0,
            }],
        )
        repository.save(users, [{"name": "사용자", "total_hours": 4}])
        backup = BackupModule(root / "backup", repository)
        management = ManagementModule(
            str(root / "fac.json"),
            str(activities),
            repository,
            backup,
            region_resolver=lambda location: [{"code": "1234567890", "name": location}],
        )
        repository.save(root / "fac.json", [{
            "facility_id": 1,
            "facility_name": "시설",
            "location": "구미",
            "contact": "000",
        }])
        window = MainWindow(
            search_module=SearchModule(str(activities), repository),
            activity_time_module=ActivityTimeModule(str(users), repository, backup),
            review_module=ReviewModule(str(reviews), str(activities), repository, backup),
            management_module=management,
        )

        window.search_input.setText("인정시간")
        window.search_activities()
        window.show_reviews(window.results_list.item(0))
        window.record_service_hours()

        self.assertEqual(window.activity_time_module.get_total_hours(), 7)
        self.assertIs(window.pages.currentWidget(), window.review_page)

    def test_review_page_registers_review_for_selected_activity(self):
        root = Path(tempfile.mkdtemp())
        repository = JsonRepository()
        reviews = root / "rev.json"
        activities = root / "act.json"
        users = root / "user.json"
        repository.save(reviews, [])
        repository.save(
            activities,
            [{
                "activity_id": 1,
                "title": "테스트 활동",
                "location": "구미",
                "rating": 0,
            }],
        )
        repository.save(users, [{"name": "사용자", "total_hours": 0}])
        backup = BackupModule(root / "backup", repository)
        window = MainWindow(
            search_module=SearchModule(str(activities), repository),
            activity_time_module=ActivityTimeModule(str(users), repository, backup),
            review_module=ReviewModule(str(reviews), str(activities), repository, backup),
        )

        window.search_input.setText("테스트")
        window.search_activities()
        window.results_list.setCurrentRow(0)
        window.show_reviews(window.results_list.currentItem())
        window.open_review_page()
        window.review_text_input.setText("좋은 활동이었습니다.")
        window.review_rating_input.setValue(5)
        window.submit_review()

        self.assertIn("후기가 등록되었습니다.", window.review_status_label.text())
        self.assertEqual(len(window.review_module.get_reviews(1)), 1)
        self.assertIs(window.pages.currentWidget(), window.title_page)

    def test_facility_registration_uses_management_module(self):
        root = Path(tempfile.mkdtemp())
        repository = JsonRepository()
        facilities = root / "fac.json"
        activities = root / "act.json"
        repository.save(facilities, [])
        repository.save(activities, [])
        management = ManagementModule(
            str(facilities),
            str(activities),
            repository,
            BackupModule(root / "backup", repository),
            region_resolver=lambda location: [
                {"code": "1234567890", "name": location}
            ],
        )
        window = MainWindow(management_module=management)

        window.facility_name_input.setText("새 시설")
        window.facility_province_input.setCurrentIndex(
            window.facility_province_input.findData("4700000000")
        )
        window.facility_city_input.setCurrentIndex(
            window.facility_city_input.findData("4719000000")
        )
        window.facility_district_input.setCurrentIndex(1)
        window.facility_address_input.setText("대학로 61")
        window.facility_contact_input.setText("000")
        window.register_facility()

        self.assertIn("시설 등록이 완료되었습니다.", window.facility_status_label.text())
        self.assertIn("471901010001", window.facility_status_label.text())
        self.assertEqual(management.list_facilities()[0]["facility_name"], "새 시설")

    def test_activity_registration_searches_and_registers_selected_facility(self):
        root = Path(tempfile.mkdtemp())
        repository = JsonRepository()
        facilities = root / "fac.json"
        activities = root / "act.json"
        repository.save(facilities, [{
            "facility_id": 1,
            "facility_name": "구미 센터",
            "location": "구미시",
            "contact": "000",
        }])
        repository.save(activities, [])
        management = ManagementModule(
            str(facilities),
            str(activities),
            repository,
            BackupModule(root / "backup", repository),
            region_resolver=lambda location: [{"code": "1234567890", "name": location}],
        )
        window = MainWindow(management_module=management)

        window.activity_facility_search.setText("구미")
        window.search_activity_facilities()
        window.activity_facility_list.setCurrentRow(0)
        window.select_activity_facility(window.activity_facility_list.currentItem())
        window.activity_title_input.setText("환경 정화")
        window.activity_description_input.setText("하천 주변 정화")
        window.register_activity()

        self.assertIn("활동 등록이 완료되었습니다.", window.activity_status_label.text())
        self.assertEqual(management.list_activities()[0]["facility_id"], 1)


if __name__ == "__main__":
    unittest.main()
