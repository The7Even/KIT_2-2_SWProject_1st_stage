"""굿포인트 PyQt6 메인 화면."""

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .activity_time_module import ActivityTimeModule
from .review_module import ReviewModule
from .search_module import SearchModule


class MainWindow(QMainWindow):
    """UI-01 타이틀 화면과 UI-02 검색 화면을 제공합니다."""

    def __init__(
        self,
        search_module: SearchModule | None = None,
        activity_time_module: ActivityTimeModule | None = None,
        review_module: ReviewModule | None = None,
    ):
        super().__init__()
        self.search_module = search_module or SearchModule()
        self.activity_time_module = activity_time_module or ActivityTimeModule()
        self.review_module = review_module or ReviewModule()
        self.setWindowTitle("굿포인트")
        self.resize(900, 620)

        self.pages = QStackedWidget()
        self.title_page = self._build_title_page()
        self.search_page = self._build_search_page()
        self.pages.addWidget(self.title_page)
        self.pages.addWidget(self.search_page)
        self.setCentralWidget(self.pages)
        self.refresh_dashboard()

    def _build_title_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("굿포인트")
        heading.setObjectName("heading")
        subtitle = QLabel("봉사활동을 찾고, 기록하고, 돌아보는 공간")
        layout.addWidget(heading)
        layout.addWidget(subtitle)

        summary_box = QGroupBox("나의 활동 현황")
        summary_layout = QFormLayout(summary_box)
        self.user_name_label = QLabel()
        self.total_hours_label = QLabel()
        summary_layout.addRow("사용자", self.user_name_label)
        summary_layout.addRow("누적 봉사시간", self.total_hours_label)
        layout.addWidget(summary_box)

        open_search_button = QPushButton("활동 검색")
        open_search_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.search_page))
        layout.addWidget(open_search_button)
        return page

    def _build_search_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("활동 검색")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("활동명 또는 장소를 입력하세요")
        self.search_input.returnPressed.connect(self.search_activities)
        search_button = QPushButton("검색")
        search_button.clicked.connect(self.search_activities)
        region_button = QPushButton("지역 검색")
        region_button.clicked.connect(self.search_by_region)
        controls.addWidget(self.search_input)
        controls.addWidget(search_button)
        controls.addWidget(region_button)
        layout.addLayout(controls)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_reviews)
        layout.addWidget(self.results_list)

        self.review_label = QLabel("활동을 선택하면 후기를 확인할 수 있습니다.")
        self.review_label.setWordWrap(True)
        layout.addWidget(self.review_label)

        back_button = QPushButton("첫 화면으로")
        back_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.title_page))
        layout.addWidget(back_button)
        return page

    def refresh_dashboard(self) -> None:
        users = self.activity_time_module._load_users()
        if users:
            self.user_name_label.setText(str(users[0].get("name", "사용자")))
        else:
            self.user_name_label.setText("사용자 정보 없음")
        total_hours = self.activity_time_module.get_total_hours()
        self.total_hours_label.setText(
            f"{total_hours}시간" if total_hours is not None else "불러오기 실패"
        )

    def search_activities(self) -> None:
        results = self.search_module.search_act(self.search_input.text())
        self._display_results(results)

    def search_by_region(self) -> None:
        region_name = self.search_input.text()
        results = self.search_module.search_by_region(region_name)
        self._display_results(results)

    def _display_results(self, activities: list[dict[str, Any]]) -> None:
        self.results_list.clear()
        for activity in activities:
            item = QListWidgetItem(self._format_activity(activity))
            item.setData(Qt.ItemDataRole.UserRole, activity)
            self.results_list.addItem(item)
        if not activities:
            self.review_label.setText("검색 결과가 없습니다.")

    @staticmethod
    def _format_activity(activity: dict[str, Any]) -> str:
        return (
            f"{activity.get('title', '이름 없음')} | "
            f"{activity.get('location', '장소 없음')} | "
            f"인정시간 {activity.get('service_hours', '-')}시간 | "
            f"평점 {activity.get('rating', 0)}"
        )

    def show_reviews(self, item: QListWidgetItem) -> None:
        activity = item.data(Qt.ItemDataRole.UserRole)
        reviews = self.review_module.get_reviews(activity.get("activity_id"))
        if not reviews:
            self.review_label.setText("등록된 후기가 없습니다.")
            return
        review_text = "\n".join(
            f"평점 {review.get('rating')}: {review.get('text')}"
            for review in reviews
        )
        self.review_label.setText(review_text)


def run() -> int:
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
