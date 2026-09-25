"""굿포인트 PyQt6 메인 화면."""

from typing import Any

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .activity_time_module import ActivityTimeModule
from .management_module import ManagementModule
from .review_module import ReviewModule
from .region_code_client import LocalRegionCodeClient
from .search_module import SearchModule
from .app_logging import logger
from datetime import date


class MainWindow(QMainWindow):
    """UI-01~UI-04 화면과 핵심 사용자 흐름을 제공합니다."""

    def __init__(
        self,
        search_module: SearchModule | None = None,
        activity_time_module: ActivityTimeModule | None = None,
        review_module: ReviewModule | None = None,
        management_module: ManagementModule | None = None,
    ):
        super().__init__()
        self.search_module = search_module or SearchModule()
        self.activity_time_module = activity_time_module or ActivityTimeModule()
        self.review_module = review_module or ReviewModule()
        self.management_module = management_module or ManagementModule()
        self.region_client = getattr(
            self.management_module, "region_client", LocalRegionCodeClient()
        )
        self.selected_activity: dict[str, Any] | None = None
        self.setWindowTitle("굿포인트")
        self.resize(900, 620)

        self.pages = QStackedWidget()
        self.title_page = self._build_title_page()
        self.search_page = self._build_search_page()
        self.facility_page = self._build_facility_page()
        self.activity_page = self._build_activity_page()
        self.review_page = self._build_review_page()
        self.pages.addWidget(self.title_page)
        self.pages.addWidget(self.search_page)
        self.pages.addWidget(self.facility_page)
        self.pages.addWidget(self.activity_page)
        self.pages.addWidget(self.review_page)
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
        self.schedule_list = QListWidget()
        summary_layout.addRow("사용자", self.user_name_label)
        summary_layout.addRow("누적 봉사시간", self.total_hours_label)
        layout.addWidget(summary_box)
        layout.addWidget(QLabel("예정된 활동"))
        layout.addWidget(self.schedule_list)

        open_search_button = QPushButton("활동 검색")
        open_search_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.search_page))
        layout.addWidget(open_search_button)

        open_facility_button = QPushButton("시설 등록")
        open_facility_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.facility_page)
        )
        layout.addWidget(open_facility_button)
        open_activity_button = QPushButton("활동 등록")
        open_activity_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.activity_page)
        )
        layout.addWidget(open_activity_button)
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

        action_box = QGroupBox("활동 기록")
        action_layout = QFormLayout(action_box)
        self.record_hours_button = QPushButton("활동 완료")
        self.record_hours_button.clicked.connect(self.record_service_hours)
        action_layout.addRow(self.record_hours_button)

        self.open_review_button = QPushButton("후기 작성")
        self.open_review_button.clicked.connect(self.open_review_page)
        action_layout.addRow(self.open_review_button)
        layout.addWidget(action_box)

        self._set_activity_actions_enabled(False)

        back_button = QPushButton("첫 화면으로")
        back_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.title_page))
        layout.addWidget(back_button)
        return page

    def _build_review_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("후기 작성")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self.review_activity_label = QLabel("선택된 활동 없음")
        self.review_activity_label.setWordWrap(True)
        layout.addWidget(self.review_activity_label)

        form_box = QGroupBox("활동 후기")
        form_layout = QFormLayout(form_box)
        self.review_text_input = QLineEdit()
        self.review_text_input.setPlaceholderText("후기 내용을 입력하세요")
        self.review_rating_input = QSpinBox()
        self.review_rating_input.setRange(1, 5)
        self.review_rating_input.setValue(5)
        form_layout.addRow("후기 내용", self.review_text_input)
        form_layout.addRow("평점", self.review_rating_input)
        layout.addWidget(form_box)

        self.review_status_label = QLabel()
        self.review_status_label.setWordWrap(True)
        layout.addWidget(self.review_status_label)

        submit_button = QPushButton("후기 등록")
        submit_button.clicked.connect(self.submit_review)
        layout.addWidget(submit_button)

        back_button = QPushButton("활동 검색으로")
        back_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.search_page))
        layout.addWidget(back_button)

        home_button = QPushButton("첫 화면으로")
        home_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.title_page))
        layout.addWidget(home_button)
        return page

    def _build_facility_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("시설 등록")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        form_box = QGroupBox("봉사활동 시설 정보")
        form_layout = QFormLayout(form_box)
        self.facility_name_input = QLineEdit()
        self.facility_name_input.setPlaceholderText("시설명을 입력하세요")
        self.facility_province_input = QComboBox()
        self.facility_city_input = QComboBox()
        self.facility_district_input = QComboBox()
        self.facility_address_input = QLineEdit()
        self.facility_address_input.setPlaceholderText("상세 주소를 입력하세요")
        self.facility_province_input.currentIndexChanged.connect(
            self._load_facility_cities
        )
        self.facility_city_input.currentIndexChanged.connect(
            self._load_facility_districts
        )
        self._load_facility_provinces()
        self.facility_contact_input = QLineEdit()
        self.facility_contact_input.setPlaceholderText("연락처를 입력하세요")
        form_layout.addRow("시설명", self.facility_name_input)
        form_layout.addRow("시·도", self.facility_province_input)
        form_layout.addRow("시·군·구", self.facility_city_input)
        form_layout.addRow("읍·면·동", self.facility_district_input)
        form_layout.addRow("상세 주소", self.facility_address_input)
        form_layout.addRow("연락처", self.facility_contact_input)
        layout.addWidget(form_box)

        self.facility_status_label = QLabel()
        self.facility_status_label.setWordWrap(True)
        layout.addWidget(self.facility_status_label)

        register_button = QPushButton("시설 등록")
        register_button.clicked.connect(self.register_facility)
        layout.addWidget(register_button)

        back_button = QPushButton("첫 화면으로")
        back_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.title_page))
        layout.addWidget(back_button)
        return page

    def _build_activity_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("활동 등록")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        facility_box = QGroupBox("시설 선택")
        facility_layout = QVBoxLayout(facility_box)
        self.activity_facility_search = QLineEdit()
        self.activity_facility_search.setPlaceholderText("시설명 또는 장소를 입력하세요")
        search_facility_button = QPushButton("시설 검색")
        search_facility_button.clicked.connect(self.search_activity_facilities)
        self.activity_facility_list = QListWidget()
        self.activity_facility_list.itemClicked.connect(
            self.select_activity_facility
        )
        facility_layout.addWidget(self.activity_facility_search)
        facility_layout.addWidget(search_facility_button)
        facility_layout.addWidget(self.activity_facility_list)
        layout.addWidget(facility_box)

        form_box = QGroupBox("활동 정보")
        form_layout = QFormLayout(form_box)
        self.activity_title_input = QLineEdit()
        self.activity_description_input = QLineEdit()
        self.activity_date_input = QDateEdit()
        self.activity_date_input.setCalendarPopup(True)
        self.activity_date_input.setDate(QDate.currentDate())
        self.activity_date_input.setMinimumDate(QDate.currentDate())
        self.activity_hours_input = QSpinBox()
        self.activity_hours_input.setRange(1, 8)
        form_layout.addRow("활동명", self.activity_title_input)
        form_layout.addRow("설명", self.activity_description_input)
        form_layout.addRow("활동일", self.activity_date_input)
        form_layout.addRow("인정시간", self.activity_hours_input)
        layout.addWidget(form_box)

        self.selected_activity_facility: dict[str, Any] | None = None
        self.activity_status_label = QLabel()
        self.activity_status_label.setWordWrap(True)
        layout.addWidget(self.activity_status_label)

        register_button = QPushButton("활동 등록")
        register_button.clicked.connect(self.register_activity)
        layout.addWidget(register_button)
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
        self.schedule_list.clear()
        upcoming = []
        for activity in self.management_module.list_activities():
            schedule_date = activity.get("schedule_date")
            if activity.get("completed_at") or not isinstance(schedule_date, str):
                continue
            try:
                parsed = date.fromisoformat(schedule_date)
            except ValueError:
                continue
            if parsed >= date.today():
                upcoming.append((parsed, activity))
        for _, activity in sorted(upcoming, key=lambda item: item[0]):
            self.schedule_list.addItem(
                f"{activity.get('schedule_date')} | "
                f"{activity.get('title', '이름 없음')} | "
                f"{activity.get('service_hours', '-')}시간"
            )

    def search_activities(self) -> None:
        results = self.search_module.search_act(self.search_input.text())
        logger.info("activity_search query=%s result_count=%s", self.search_input.text(), len(results))
        self._display_results(results)

    def search_by_region(self) -> None:
        region_name = self.search_input.text()
        results = self.search_module.search_by_region(region_name)
        self._display_results(results)

    def _display_results(self, activities: list[dict[str, Any]]) -> None:
        self.results_list.clear()
        self.selected_activity = None
        self._set_activity_actions_enabled(False)
        for activity in activities:
            item = QListWidgetItem(self._format_activity(activity))
            item.setData(Qt.ItemDataRole.UserRole, activity)
            self.results_list.addItem(item)
        if not activities:
            self.review_label.setText("검색 결과가 없습니다.")
        else:
            self.review_label.setText("활동을 선택하면 후기를 확인할 수 있습니다.")

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
        self.selected_activity = activity
        self._set_activity_actions_enabled(True)
        reviews = self.review_module.get_reviews(activity.get("activity_id"))
        if not reviews:
            self.review_label.setText("등록된 후기가 없습니다.")
            return
        review_text = "\n".join(
            f"평점 {review.get('rating')}: {review.get('text')}"
            for review in reviews
        )
        self.review_label.setText(review_text)

    def record_service_hours(self) -> None:
        if self.selected_activity is None:
            return
        if self.selected_activity.get("completed_at"):
            self.review_label.setText("이미 완료한 활동입니다.")
            return
        result = self.activity_time_module.add_service_hours(
            self._activity_service_hours(self.selected_activity)
        )
        if not result.get("success"):
            self.review_label.setText(result.get("message", "봉사시간 기록에 실패했습니다."))
            return
        completion = self.management_module.complete_activity(
            self.selected_activity.get("activity_id")
        )
        if not completion.get("success"):
            self.review_label.setText(completion.get("message", "활동 완료 처리에 실패했습니다."))
            return
        self.refresh_dashboard()
        self.review_label.setText(
            f"활동을 완료했습니다. 인정시간 {result['added_hours']}시간을 "
            f"기록했습니다."
        )
        self.open_review_page()

    def submit_review(self) -> None:
        if self.selected_activity is None:
            return
        result = self.review_module.submit_review(
            {
                "activity_id": self.selected_activity.get("activity_id"),
                "rating": self.review_rating_input.value(),
                "text": self.review_text_input.text(),
            }
        )
        if not result.get("success"):
            self.review_status_label.setText(
                result.get("message", "후기 등록에 실패했습니다.")
            )
            return
        self.review_text_input.clear()
        self.selected_activity["rating"] = result["new_rating"]
        self.review_status_label.setText(
            f"후기가 등록되었습니다. 현재 평점은 {result['new_rating']}점입니다."
        )
        self.show_reviews(self.results_list.currentItem())
        self.refresh_dashboard()
        self.pages.setCurrentWidget(self.title_page)

    def _set_activity_actions_enabled(self, enabled: bool) -> None:
        self.record_hours_button.setEnabled(enabled)
        self.open_review_button.setEnabled(enabled)

    @staticmethod
    def _activity_service_hours(activity: dict[str, Any]) -> int:
        value = activity.get("service_hours")
        return value if isinstance(value, int) and not isinstance(value, bool) else 0

    def open_review_page(self) -> None:
        if self.selected_activity is None:
            return
        self.review_activity_label.setText(
            f"활동: {self.selected_activity.get('title', '이름 없음')}\n"
            f"장소: {self.selected_activity.get('location', '장소 없음')}"
        )
        self.review_text_input.clear()
        self.review_rating_input.setValue(5)
        self.review_status_label.clear()
        self.pages.setCurrentWidget(self.review_page)

    def register_facility(self) -> None:
        district_code = self.facility_district_input.currentData()
        district_name = self.facility_district_input.currentText()
        if not district_code:
            self.facility_status_label.setText("시·도, 시·군·구, 읍·면·동을 선택해 주세요.")
            return
        location = " ".join(
            part
            for part in (
                self.facility_province_input.currentText(),
                self.facility_city_input.currentText(),
                district_name,
                self.facility_address_input.text().strip(),
            )
            if part
        )
        result = self.management_module.register_facility(
            {
                "facility_name": self.facility_name_input.text(),
                "location": location,
                "contact": self.facility_contact_input.text(),
                "region_code": district_code,
            }
        )
        if not result.get("success"):
            self.facility_status_label.setText(
                result.get("message", "시설 등록에 실패했습니다.")
            )
            return

        self.facility_status_label.setText(
            f"시설 등록이 완료되었습니다. (ID: {result['facility_id']})"
        )
        self.facility_name_input.clear()
        self.facility_address_input.clear()
        self.facility_contact_input.clear()
        self.facility_province_input.setCurrentIndex(0)

    def search_activity_facilities(self) -> None:
        query = self.activity_facility_search.text().strip().casefold()
        facilities = self.management_module.list_facilities()
        results = [
            facility
            for facility in facilities
            if not query
            or query in str(facility.get("facility_name", "")).casefold()
            or query in str(facility.get("location", "")).casefold()
        ]
        self.activity_facility_list.clear()
        self.selected_activity_facility = None
        self.refresh_dashboard()
        for facility in results:
            item = QListWidgetItem(
                f"{facility.get('facility_name', '이름 없음')} | "
                f"{facility.get('location', '장소 없음')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, facility)
            self.activity_facility_list.addItem(item)
        self.activity_status_label.setText(
            "시설을 선택해 주세요." if results else "검색된 시설이 없습니다."
        )

    def select_activity_facility(self, item: QListWidgetItem) -> None:
        self.selected_activity_facility = item.data(Qt.ItemDataRole.UserRole)
        self.activity_status_label.setText(
            f"선택 시설: {self.selected_activity_facility['facility_name']}"
        )

    def register_activity(self) -> None:
        facility = self.selected_activity_facility
        if facility is None:
            self.activity_status_label.setText("먼저 활동을 등록할 시설을 선택해 주세요.")
            return
        result = self.management_module.register_activity(
            {
                "facility_id": facility["facility_id"],
                "title": self.activity_title_input.text(),
                "description": self.activity_description_input.text(),
                "location": facility["location"],
                "schedule_date": self.activity_date_input.date().toString("yyyy-MM-dd"),
                "service_hours": self.activity_hours_input.value(),
            }
        )
        if not result.get("success"):
            self.activity_status_label.setText(
                result.get("message", "활동 등록에 실패했습니다.")
            )
            return
        self.activity_status_label.setText(
            f"활동 등록이 완료되었습니다. (ID: {result['activity_id']})"
        )
        self.activity_title_input.clear()
        self.activity_description_input.clear()
        self.selected_activity_facility = None

    def _load_facility_provinces(self) -> None:
        self.facility_province_input.clear()
        self.facility_province_input.addItem("시·도를 선택하세요", None)
        for region in self.region_client.list_provinces():
            self.facility_province_input.addItem(region["name"], region["code"])

    def _load_facility_cities(self) -> None:
        self.facility_city_input.clear()
        self.facility_district_input.clear()
        self.facility_city_input.addItem("시·군·구를 선택하세요", None)
        province_code = self.facility_province_input.currentData()
        if province_code:
            for region in self.region_client.list_cities(province_code):
                self.facility_city_input.addItem(region["name"], region["code"])

    def _load_facility_districts(self) -> None:
        self.facility_district_input.clear()
        self.facility_district_input.addItem("읍·면·동을 선택하세요", None)
        city_code = self.facility_city_input.currentData()
        if city_code:
            for region in self.region_client.list_districts(city_code):
                self.facility_district_input.addItem(region["name"], region["code"])


def run() -> int:
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
