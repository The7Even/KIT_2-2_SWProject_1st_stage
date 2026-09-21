import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_builds_title_and_search_pages(self):
        window = MainWindow()

        self.assertEqual(window.pages.count(), 2)
        self.assertEqual(window.windowTitle(), "굿포인트")
        self.assertEqual(window.total_hours_label.text(), "12시간")

    def test_search_action_populates_results(self):
        window = MainWindow()
        window.search_input.setText("도시")
        window.search_activities()

        self.assertEqual(window.results_list.count(), 1)
        self.assertIn("도시 미화 작업", window.results_list.item(0).text())


if __name__ == "__main__":
    unittest.main()
