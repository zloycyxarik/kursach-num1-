from __future__ import annotations

from typing import Dict, Optional

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .auth import AuthService
from .auth_dialog import AuthDialog
from .database import DatabaseManager
from .repositories import DriverRepository, MaintenanceRepository, VehicleRepository
from .styles import APP_STYLESHEET


class NavigationButton(QPushButton):
    def __init__(self, text: str, *, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class BasePage(QWidget):
    title: str = ""
    enable_search: bool = False
    enable_add: bool = False

    def refresh(self) -> None:
        """Called when the page becomes visible."""

    def handle_search(self, keyword: str) -> None:
        """Handle user search input."""

    def handle_add(self) -> None:
        """Handle add button click."""


class DashboardPage(BasePage):
    title = "Дашборд"
    enable_search = False
    enable_add = False

    def __init__(
        self,
        vehicle_repo: VehicleRepository,
        maintenance_repo: MaintenanceRepository,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.vehicle_repo = vehicle_repo
        self.maintenance_repo = maintenance_repo
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        self.cards = []
        card_labels = [
            ("Всего ТС", "0"),
            ("Активны", "0"),
            ("В ремонте", "0"),
            ("Сервис < 30 дн", "0"),
        ]
        for title, value in card_labels:
            card = self._create_info_card(title, value)
            self.cards.append(card[1])
            cards_layout.addWidget(card[0])

        layout.addLayout(cards_layout)

        lower_layout = QHBoxLayout()
        lower_layout.setSpacing(24)

        self.upcoming_list = QListWidget()
        self.upcoming_list.setMinimumWidth(320)
        self.upcoming_list.setStyleSheet("QListWidget::item { padding: 12px; }")

        upcoming_frame = QFrame()
        upcoming_frame.setObjectName("InfoCard")
        upcoming_layout = QVBoxLayout(upcoming_frame)
        upcoming_layout.setSpacing(12)
        title = QLabel("Ближайшие обслуживания")
        title.setObjectName("SectionTitle")
        upcoming_layout.addWidget(title)
        upcoming_layout.addWidget(self.upcoming_list)

        self.maintenance_table = QTableWidget(0, 2)
        self.maintenance_table.setHorizontalHeaderLabels(["Месяц", "Расходы, ₽"])
        self.maintenance_table.horizontalHeader().setStretchLastSection(True)
        self.maintenance_table.verticalHeader().setVisible(False)
        self.maintenance_table.setAlternatingRowColors(True)

        maintenance_frame = QFrame()
        maintenance_frame.setObjectName("InfoCard")
        maintenance_layout = QVBoxLayout(maintenance_frame)
        maintenance_layout.setSpacing(12)
        maintenance_title = QLabel("Расходы на обслуживание по месяцам")
        maintenance_title.setObjectName("SectionTitle")
        maintenance_layout.addWidget(maintenance_title)
        maintenance_layout.addWidget(self.maintenance_table)

        lower_layout.addWidget(upcoming_frame, 1)
        lower_layout.addWidget(maintenance_frame, 2)

        layout.addLayout(lower_layout)

    def _create_info_card(self, caption: str, value: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("InfoCard")
        frame.setMinimumWidth(160)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(8)
        value_label = QLabel(value)
        value_label.setObjectName("CardNumber")
        caption_label = QLabel(caption)
        caption_label.setObjectName("CardCaption")
        frame_layout.addWidget(value_label)
        frame_layout.addWidget(caption_label)
        return frame, value_label

    def refresh(self) -> None:
        summary = self.vehicle_repo.summary()
        for label, key in zip(self.cards, ("total", "active", "in_service", "due_service")):
            label.setText(str(summary[key]))

        self.upcoming_list.clear()
        for item in self.vehicle_repo.list_due_for_service():
            text = (
                f"{item['registry_number']} — {item['make']} {item['model']} "
                f"(до {item['next_service_date'] or 'не указано'})"
            )
            list_item = QListWidgetItem(text)
            status = item.get("status", "")
            accent = QColor("#f97316" if status == "В ремонте" else "#2563eb")
            list_item.setForeground(Qt.GlobalColor.black)
            list_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            list_item.setBackground(Qt.GlobalColor.transparent)
            list_item.setFont(QFont("Segoe UI", 11))
            list_item.setToolTip(status or "Статус не задан")
            list_item.setData(Qt.ItemDataRole.DecorationRole, accent)
            self.upcoming_list.addItem(list_item)

        chart_data = self.maintenance_repo.stats()
        self.maintenance_table.setRowCount(len(chart_data))
        for row_index, (month, total_cost) in enumerate(chart_data):
            self.maintenance_table.setItem(row_index, 0, QTableWidgetItem(month))
            self.maintenance_table.setItem(
                row_index, 1, QTableWidgetItem(f"{total_cost:,.0f}".replace(",", " "))
            )


class VehiclesPage(BasePage):
    title = "Транспортные средства"
    enable_search = True
    enable_add = True

    def __init__(
        self,
        vehicle_repo: VehicleRepository,
        driver_repo: DriverRepository,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.vehicle_repo = vehicle_repo
        self.driver_repo = driver_repo
        self.current_vehicle_id: Optional[int] = None
        self.search_query: str = ""
        self.status_filter = "Все"
        self._driver_map: Dict[int, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(12)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)
        status_label = QLabel("Статус:")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Все", "Активен", "В ремонте", "Списан", "На консервации"])
        self.status_combo.currentTextChanged.connect(self._on_status_filter_changed)
        filter_layout.addWidget(status_label)
        filter_layout.addWidget(self.status_combo)
        filter_layout.addStretch()

        left_layout.addLayout(filter_layout)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Рег. номер",
                "Марка",
                "Модель",
                "Год",
                "Пробег",
                "Статус",
                "Водитель",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        self.table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.table)

        layout.addWidget(left_frame, 3)

        form_frame = QFrame()
        form_frame.setObjectName("InfoCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(16)

        form_title = QLabel("Карточка ТС")
        form_title.setObjectName("SectionTitle")
        form_layout.addWidget(form_title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.registry_input = QLineEdit()
        self.registry_input.setPlaceholderText("Например, А123ВС77")
        form.addRow("Регистрационный номер*", self.registry_input)

        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("17 символов VIN")
        form.addRow("VIN", self.vin_input)

        self.make_input = QLineEdit()
        self.make_input.setPlaceholderText("Марка")
        form.addRow("Марка*", self.make_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Модель")
        form.addRow("Модель*", self.model_input)

        self.year_input = QSpinBox()
        self.year_input.setRange(1980, QDate.currentDate().year() + 2)
        form.addRow("Год выпуска", self.year_input)

        self.mileage_input = QSpinBox()
        self.mileage_input.setRange(0, 2_000_000)
        self.mileage_input.setSingleStep(500)
        form.addRow("Пробег, км", self.mileage_input)

        self.status_input = QComboBox()
        self.status_input.addItems(["Активен", "В ремонте", "Списан", "На консервации"])
        form.addRow("Статус", self.status_input)

        self.acquisition_input = QDateEdit()
        self.acquisition_input.setDisplayFormat("dd.MM.yyyy")
        self.acquisition_input.setCalendarPopup(True)
        form.addRow("Дата приобретения", self.acquisition_input)

        self.next_service_input = QDateEdit()
        self.next_service_input.setDisplayFormat("dd.MM.yyyy")
        self.next_service_input.setCalendarPopup(True)
        form.addRow("Следующее ТО", self.next_service_input)

        self.fuel_input = QComboBox()
        self.fuel_input.addItems(["Бензин", "Дизель", "Электро", "Гибрид", "Газ"])
        form.addRow("Топливо", self.fuel_input)

        self.driver_input = QComboBox()
        form.addRow("Водитель", self.driver_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Дополнительные сведения...")
        self.notes_input.setFixedHeight(100)
        form.addRow("Примечание", self.notes_input)

        form_layout.addLayout(form)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save_vehicle)

        self.new_button = QPushButton("Очистить")
        self.new_button.setObjectName("SecondaryButton")
        self.new_button.clicked.connect(self.reset_form)

        self.delete_button = QPushButton("Удалить")
        self.delete_button.setObjectName("SecondaryButton")
        self.delete_button.clicked.connect(self.delete_vehicle)

        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.new_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()

        form_layout.addLayout(buttons_layout)
        layout.addWidget(form_frame, 2)

    def refresh(self) -> None:
        self._populate_drivers()
        self._load_table()

    def handle_search(self, keyword: str) -> None:
        self.search_query = keyword.strip()
        self._load_table()

    def handle_add(self) -> None:
        self.reset_form()
        self.registry_input.setFocus()

    def _populate_drivers(self) -> None:
        self.driver_input.blockSignals(True)
        self.driver_input.clear()
        self.driver_input.addItem("Не назначен", None)
        self._driver_map = {None: "Не назначен"}
        for record in self.driver_repo.list_all():
            self.driver_input.addItem(record["full_name"], record["id"])
            self._driver_map[record["id"]] = record["full_name"]
        self.driver_input.blockSignals(False)

    def _load_table(self) -> None:
        if self.search_query:
            records = self.vehicle_repo.search(self.search_query)
        else:
            records = self.vehicle_repo.list_all()

        if self.status_filter != "Все":
            records = [r for r in records if r["status"] == self.status_filter]

        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(record["registry_number"]))
            self.table.setItem(row, 1, QTableWidgetItem(record["make"]))
            self.table.setItem(row, 2, QTableWidgetItem(record["model"]))
            self.table.setItem(row, 3, QTableWidgetItem(str(record.get("year") or "")))
            self.table.setItem(row, 4, QTableWidgetItem(f"{record.get('mileage', 0):,}".replace(",", " ")))
            self.table.setItem(row, 5, QTableWidgetItem(record.get("status", "")))
            driver_name = record.get("driver_name") or "Не назначен"
            self.table.setItem(row, 6, QTableWidgetItem(driver_name))
            for col in range(7):
                item = self.table.item(row, col)
                item.setData(Qt.ItemDataRole.UserRole, record["id"])

        self.table.resizeColumnsToContents()

    def _on_status_filter_changed(self, text: str) -> None:
        self.status_filter = text
        self._load_table()

    def _on_table_selection(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        vehicle_id = selected[0].data(Qt.ItemDataRole.UserRole)
        for record in self.vehicle_repo.list_all():
            if record["id"] == vehicle_id:
                self._fill_form(record)
                break

    def _fill_form(self, record: Dict[str, Optional[str]]) -> None:
        self.current_vehicle_id = record["id"]
        self.registry_input.setText(record.get("registry_number", ""))
        self.vin_input.setText(record.get("vin", "") or "")
        self.make_input.setText(record.get("make", "") or "")
        self.model_input.setText(record.get("model", "") or "")
        self.year_input.setValue(int(record.get("year") or 2000))
        self.mileage_input.setValue(int(record.get("mileage") or 0))
        status = record.get("status") or "Активен"
        index = self.status_input.findText(status)
        self.status_input.setCurrentIndex(max(index, 0))
        self._set_date(self.acquisition_input, record.get("acquisition_date"))
        self._set_date(self.next_service_input, record.get("next_service_date"))
        fuel_index = self.fuel_input.findText(record.get("fuel_type") or "Бензин")
        self.fuel_input.setCurrentIndex(max(fuel_index, 0))
        driver_id = record.get("assigned_driver_id")
        index = self.driver_input.findData(driver_id)
        self.driver_input.setCurrentIndex(index if index >= 0 else 0)
        self.notes_input.setPlainText(record.get("notes") or "")

    def reset_form(self) -> None:
        self.current_vehicle_id = None
        self.registry_input.clear()
        self.vin_input.clear()
        self.make_input.clear()
        self.model_input.clear()
        self.year_input.setValue(QDate.currentDate().year())
        self.mileage_input.setValue(0)
        self.status_input.setCurrentIndex(0)
        self.acquisition_input.setDate(QDate.currentDate())
        self.next_service_input.setDate(QDate.currentDate().addMonths(6))
        self.fuel_input.setCurrentIndex(0)
        self.driver_input.setCurrentIndex(0)
        self.notes_input.clear()

    def _collect_form_data(self) -> Optional[Dict[str, Optional[str]]]:
        registry = self.registry_input.text().strip()
        make = self.make_input.text().strip()
        model = self.model_input.text().strip()
        if not registry or not make or not model:
            QMessageBox.warning(self, "Заполнение формы", "Поля с * обязательны для заполнения.")
            return None

        data = {
            "registry_number": registry,
            "vin": self.vin_input.text().strip() or None,
            "make": make,
            "model": model,
            "year": self.year_input.value(),
            "mileage": self.mileage_input.value(),
            "status": self.status_input.currentText(),
            "acquisition_date": self._date_to_iso(self.acquisition_input),
            "next_service_date": self._date_to_iso(self.next_service_input),
            "fuel_type": self.fuel_input.currentText(),
            "assigned_driver_id": self.driver_input.currentData(),
            "notes": self.notes_input.toPlainText().strip() or None,
        }
        return data

    def save_vehicle(self) -> None:
        data = self._collect_form_data()
        if not data:
            return
        try:
            if self.current_vehicle_id:
                self.vehicle_repo.update(self.current_vehicle_id, data)
            else:
                self.current_vehicle_id = self.vehicle_repo.create(data)
            self._load_table()
            QMessageBox.information(self, "Сохранение", "Данные успешно сохранены.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить запись: {exc}")

    def delete_vehicle(self) -> None:
        if not self.current_vehicle_id:
            QMessageBox.information(self, "Удаление", "Выберите запись для удаления.")
            return
        confirm = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранное транспортное средство? Связанные записи обслуживания будут удалены.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.vehicle_repo.delete(self.current_vehicle_id)
                self.reset_form()
                self._load_table()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись: {exc}")

    @staticmethod
    def _set_date(widget: QDateEdit, value: Optional[str]) -> None:
        if value:
            widget.setDate(QDate.fromString(value, "yyyy-MM-dd"))
        else:
            widget.setDate(QDate.currentDate())

    @staticmethod
    def _date_to_iso(widget: QDateEdit) -> str:
        return widget.date().toString("yyyy-MM-dd")


class DriversPage(BasePage):
    title = "Водители"
    enable_search = True
    enable_add = True

    def __init__(self, driver_repo: DriverRepository, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.driver_repo = driver_repo
        self.current_driver_id: Optional[int] = None
        self.search_query: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ФИО", "Телефон", "E-mail", "Вод. удостоверение", "Срок действия"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 3)

        form_frame = QFrame()
        form_frame.setObjectName("InfoCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(16)

        title = QLabel("Карточка водителя")
        title.setObjectName("SectionTitle")
        form_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.name_input = QLineEdit()
        form.addRow("ФИО*", self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+7 XXX XXX-XX-XX")
        form.addRow("Телефон", self.phone_input)

        self.email_input = QLineEdit()
        form.addRow("E-mail", self.email_input)

        self.license_input = QLineEdit()
        form.addRow("№ удостоверения", self.license_input)

        self.license_expiry_input = QDateEdit()
        self.license_expiry_input.setDisplayFormat("dd.MM.yyyy")
        self.license_expiry_input.setCalendarPopup(True)
        form.addRow("Срок действия", self.license_expiry_input)

        self.driver_notes = QTextEdit()
        self.driver_notes.setFixedHeight(100)
        form.addRow("Примечание", self.driver_notes)

        form_layout.addLayout(form)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        self.driver_save = QPushButton("Сохранить")
        self.driver_save.setObjectName("PrimaryButton")
        self.driver_save.clicked.connect(self.save_driver)

        self.driver_new = QPushButton("Очистить")
        self.driver_new.setObjectName("SecondaryButton")
        self.driver_new.clicked.connect(self.reset_form)

        self.driver_delete = QPushButton("Удалить")
        self.driver_delete.setObjectName("SecondaryButton")
        self.driver_delete.clicked.connect(self.delete_driver)

        buttons_layout.addWidget(self.driver_save)
        buttons_layout.addWidget(self.driver_new)
        buttons_layout.addWidget(self.driver_delete)
        buttons_layout.addStretch()

        form_layout.addLayout(buttons_layout)
        layout.addWidget(form_frame, 2)

    def refresh(self) -> None:
        self._load_table()

    def handle_search(self, keyword: str) -> None:
        self.search_query = keyword.strip()
        self._load_table()

    def handle_add(self) -> None:
        self.reset_form()
        self.name_input.setFocus()

    def _load_table(self) -> None:
        if self.search_query:
            records = self.driver_repo.search(self.search_query)
        else:
            records = self.driver_repo.list_all()

        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(record["full_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(record.get("phone") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(record.get("email") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(record.get("license_number") or ""))
            self.table.setItem(row, 4, QTableWidgetItem(record.get("license_expiry") or ""))
            for col in range(5):
                item = self.table.item(row, col)
                item.setData(Qt.ItemDataRole.UserRole, record["id"])

        self.table.resizeColumnsToContents()

    def _on_table_selection(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        driver_id = selected[0].data(Qt.ItemDataRole.UserRole)
        record = self.driver_repo.get(driver_id)
        if record:
            self._fill_form(record)

    def _fill_form(self, record: Dict[str, Optional[str]]) -> None:
        self.current_driver_id = record["id"]
        self.name_input.setText(record.get("full_name", ""))
        self.phone_input.setText(record.get("phone") or "")
        self.email_input.setText(record.get("email") or "")
        self.license_input.setText(record.get("license_number") or "")
        self._set_date(self.license_expiry_input, record.get("license_expiry"))
        self.driver_notes.setPlainText(record.get("notes") or "")

    def reset_form(self) -> None:
        self.current_driver_id = None
        self.name_input.clear()
        self.phone_input.clear()
        self.email_input.clear()
        self.license_input.clear()
        self.license_expiry_input.setDate(QDate.currentDate().addYears(1))
        self.driver_notes.clear()

    def _collect_form_data(self) -> Optional[Dict[str, Optional[str]]]:
        full_name = self.name_input.text().strip()
        if not full_name:
            QMessageBox.warning(self, "Заполнение формы", "Укажите ФИО водителя.")
            return None

        return {
            "full_name": full_name,
            "phone": self.phone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "license_number": self.license_input.text().strip() or None,
            "license_expiry": self.license_expiry_input.date().toString("yyyy-MM-dd"),
            "notes": self.driver_notes.toPlainText().strip() or None,
        }

    def save_driver(self) -> None:
        data = self._collect_form_data()
        if not data:
            return
        try:
            if self.current_driver_id:
                self.driver_repo.update(self.current_driver_id, data)
            else:
                self.current_driver_id = self.driver_repo.create(data)
            self._load_table()
            QMessageBox.information(self, "Сохранение", "Данные успешно сохранены.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить запись: {exc}")

    def delete_driver(self) -> None:
        if not self.current_driver_id:
            QMessageBox.information(self, "Удаление", "Выберите запись для удаления.")
            return
        confirm = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранного водителя? В транспортных средствах назначение будет снято.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.driver_repo.delete(self.current_driver_id)
                self.reset_form()
                self._load_table()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись: {exc}")

    @staticmethod
    def _set_date(widget: QDateEdit, value: Optional[str]) -> None:
        if value:
            widget.setDate(QDate.fromString(value, "yyyy-MM-dd"))
        else:
            widget.setDate(QDate.currentDate().addYears(1))


class MaintenancePage(BasePage):
    title = "Обслуживание"
    enable_search = False
    enable_add = True

    def __init__(
        self,
        maintenance_repo: MaintenanceRepository,
        vehicle_repo: VehicleRepository,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.maintenance_repo = maintenance_repo
        self.vehicle_repo = vehicle_repo
        self.current_vehicle_id: Optional[int] = None
        self.current_record_id: Optional[int] = None
        self._vehicles_cache: Dict[int, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(12)
        label = QLabel("Транспортное средство:")
        self.vehicle_selector = QComboBox()
        self.vehicle_selector.currentIndexChanged.connect(self._on_vehicle_changed)
        selection_layout.addWidget(label)
        selection_layout.addWidget(self.vehicle_selector, 1)
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Дата", "Описание", "Пробег", "Стоимость, ₽", "Сервис"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        self.table.horizontalHeader().setStretchLastSection(True)
        content_layout.addWidget(self.table, 3)

        form_frame = QFrame()
        form_frame.setObjectName("InfoCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(16)

        title = QLabel("Запись обслуживания")
        title.setObjectName("SectionTitle")
        form_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.service_date_input = QDateEdit()
        self.service_date_input.setDisplayFormat("dd.MM.yyyy")
        self.service_date_input.setCalendarPopup(True)
        form.addRow("Дата*", self.service_date_input)

        self.description_input = QLineEdit()
        form.addRow("Описание*", self.description_input)

        self.service_mileage_input = QSpinBox()
        self.service_mileage_input.setRange(0, 2_000_000)
        self.service_mileage_input.setSingleStep(500)
        form.addRow("Пробег, км", self.service_mileage_input)

        self.service_cost_input = QDoubleSpinBox()
        self.service_cost_input.setMaximum(10_000_000)
        self.service_cost_input.setDecimals(2)
        self.service_cost_input.setSingleStep(1000)
        form.addRow("Стоимость, ₽", self.service_cost_input)

        self.service_center_input = QLineEdit()
        form.addRow("Сервисный центр", self.service_center_input)

        self.service_notes_input = QTextEdit()
        self.service_notes_input.setFixedHeight(80)
        form.addRow("Примечание", self.service_notes_input)

        form_layout.addLayout(form)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        self.service_save = QPushButton("Сохранить")
        self.service_save.setObjectName("PrimaryButton")
        self.service_save.clicked.connect(self.save_record)

        self.service_reset = QPushButton("Очистить")
        self.service_reset.setObjectName("SecondaryButton")
        self.service_reset.clicked.connect(self.reset_form)

        self.service_delete = QPushButton("Удалить")
        self.service_delete.setObjectName("SecondaryButton")
        self.service_delete.clicked.connect(self.delete_record)

        buttons_layout.addWidget(self.service_save)
        buttons_layout.addWidget(self.service_reset)
        buttons_layout.addWidget(self.service_delete)
        buttons_layout.addStretch()

        form_layout.addLayout(buttons_layout)

        content_layout.addWidget(form_frame, 2)
        layout.addLayout(content_layout)

    def refresh(self) -> None:
        self._load_vehicles()
        if self.vehicle_selector.count() > 0 and self.current_vehicle_id is None:
            self.vehicle_selector.setCurrentIndex(0)

    def handle_add(self) -> None:
        self.reset_form()
        self.description_input.setFocus()

    def _load_vehicles(self) -> None:
        records = self.vehicle_repo.list_all()
        self.vehicle_selector.blockSignals(True)
        self.vehicle_selector.clear()
        self._vehicles_cache.clear()
        for record in records:
            label = f"{record['registry_number']} — {record['make']} {record['model']}"
            self.vehicle_selector.addItem(label, record["id"])
            self._vehicles_cache[record["id"]] = label
        self.vehicle_selector.blockSignals(False)

    def _load_table(self) -> None:
        if not self.current_vehicle_id:
            self.table.setRowCount(0)
            return
        records = self.maintenance_repo.list_for_vehicle(self.current_vehicle_id)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(record.get("service_date") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(record.get("description") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(record.get("mileage") or "")))
            self.table.setItem(row, 3, QTableWidgetItem(f"{record.get('cost', 0):,.2f}".replace(",", " ")))
            self.table.setItem(row, 4, QTableWidgetItem(record.get("service_center") or ""))
            for col in range(5):
                item = self.table.item(row, col)
                item.setData(Qt.ItemDataRole.UserRole, record["id"])
        self.table.resizeColumnsToContents()

    def _on_vehicle_changed(self, index: int) -> None:
        self.current_vehicle_id = self.vehicle_selector.itemData(index)
        self._load_table()
        self.reset_form()

    def _on_table_selection(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        record_id = selected[0].data(Qt.ItemDataRole.UserRole)
        for record in self.maintenance_repo.list_for_vehicle(self.current_vehicle_id):  # type: ignore[arg-type]
            if record["id"] == record_id:
                self._fill_form(record)
                break

    def _fill_form(self, record: Dict[str, Optional[str]]) -> None:
        self.current_record_id = record["id"]
        self.service_date_input.setDate(QDate.fromString(record.get("service_date") or "", "yyyy-MM-dd"))
        self.description_input.setText(record.get("description") or "")
        self.service_mileage_input.setValue(int(record.get("mileage") or 0))
        self.service_cost_input.setValue(float(record.get("cost") or 0))
        self.service_center_input.setText(record.get("service_center") or "")
        self.service_notes_input.setPlainText(record.get("notes") or "")

    def reset_form(self) -> None:
        self.current_record_id = None
        self.service_date_input.setDate(QDate.currentDate())
        self.description_input.clear()
        self.service_mileage_input.setValue(0)
        self.service_cost_input.setValue(0)
        self.service_center_input.clear()
        self.service_notes_input.clear()

    def _collect_form_data(self) -> Optional[Dict[str, Optional[str]]]:
        if not self.current_vehicle_id:
            QMessageBox.information(self, "Сохранение", "Выберите транспортное средство.")
            return None
        if not self.description_input.text().strip():
            QMessageBox.warning(self, "Заполнение формы", "Укажите описание выполненных работ.")
            return None
        return {
            "vehicle_id": self.current_vehicle_id,
            "service_date": self.service_date_input.date().toString("yyyy-MM-dd"),
            "description": self.description_input.text().strip(),
            "mileage": self.service_mileage_input.value(),
            "cost": self.service_cost_input.value(),
            "service_center": self.service_center_input.text().strip() or None,
            "notes": self.service_notes_input.toPlainText().strip() or None,
        }

    def save_record(self) -> None:
        data = self._collect_form_data()
        if not data:
            return
        try:
            if self.current_record_id:
                self.maintenance_repo.update(self.current_record_id, data)
            else:
                self.current_record_id = self.maintenance_repo.create(data)
            self._load_table()
            QMessageBox.information(self, "Сохранение", "Данные успешно сохранены.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить запись: {exc}")

    def delete_record(self) -> None:
        if not self.current_record_id:
            QMessageBox.information(self, "Удаление", "Выберите запись для удаления.")
            return
        confirm = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранную запись обслуживания?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.maintenance_repo.delete(self.current_record_id)
                self.reset_form()
                self._load_table()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись: {exc}")


class MainWindow(QMainWindow):
    def __init__(
        self,
        db: DatabaseManager,
        user: Optional[dict] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Учет автопарка")
        self.resize(1320, 820)
        self.db = db
        self.vehicle_repo = VehicleRepository(self.db)
        self.driver_repo = DriverRepository(self.db)
        self.maintenance_repo = MaintenanceRepository(self.db)
        self.user = user or {}
        self._current_page: Optional[BasePage] = None
        self._navigation_buttons: Dict[str, NavigationButton] = {}
        self._build_ui()
        self.setStyleSheet(APP_STYLESHEET)
        self.switch_page("dashboard")
        self._update_user_badge()

    def _build_ui(self) -> None:
        font = QFont("Segoe UI", 10)
        QApplication.instance().setFont(font)

        central = QSplitter(Qt.Orientation.Horizontal)
        central.setHandleWidth(8)

        sidebar = self._build_sidebar()
        central.addWidget(sidebar)

        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        header = self._build_header()
        content_layout.addWidget(header, 0)

        self.stack = QStackedWidget()
        self.pages: Dict[str, BasePage] = {
            "dashboard": DashboardPage(self.vehicle_repo, self.maintenance_repo),
            "vehicles": VehiclesPage(self.vehicle_repo, self.driver_repo),
            "drivers": DriversPage(self.driver_repo),
            "maintenance": MaintenancePage(self.maintenance_repo, self.vehicle_repo),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)

        central.addWidget(content_frame)
        central.setStretchFactor(0, 0)
        central.setStretchFactor(1, 1)
        central.setSizes([320, 1000])

        self.setCentralWidget(central)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(260)
        sidebar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Fleet Manager")
        title.setStyleSheet("font-size: 18pt; color: #ffffff; font-weight: 700;")
        layout.addWidget(title)

        self._navigation_buttons["dashboard"] = self._create_nav_button("Дашборд")
        self._navigation_buttons["vehicles"] = self._create_nav_button("Транспортные средства")
        self._navigation_buttons["drivers"] = self._create_nav_button("Водители")
        self._navigation_buttons["maintenance"] = self._create_nav_button("Обслуживание")

        for key, button in self._navigation_buttons.items():
            button.clicked.connect(lambda checked, k=key: self.switch_page(k))
            layout.addWidget(button)

        layout.addStretch()
        return sidebar

    def _create_nav_button(self, text: str) -> NavigationButton:
        button = NavigationButton(text)
        return button

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 12, 24, 12)
        header_layout.setSpacing(16)

        self.title_label = QLabel("Дашборд")
        self.title_label.setObjectName("SectionTitle")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch(1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Быстрый поиск...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setFixedWidth(260)
        header_layout.addWidget(self.search_input, 0, Qt.AlignmentFlag.AlignRight)

        self.add_button = QPushButton("Добавить")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignRight)

        self.user_badge = QLabel()
        self.user_badge.setObjectName("UserBadge")
        self.user_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.user_badge, 0, Qt.AlignmentFlag.AlignRight)

        return header

    def switch_page(self, page_key: str) -> None:
        page = self.pages.get(page_key)
        if not page:
            return

        index = list(self.pages.keys()).index(page_key)
        self.stack.setCurrentIndex(index)
        self.title_label.setText(page.title)
        self.search_input.setVisible(page.enable_search)
        if not page.enable_search:
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
        self.add_button.setVisible(page.enable_add)
        page.refresh()
        self._current_page = page

        for key, button in self._navigation_buttons.items():
            button.setChecked(key == page_key)

    def _on_search_changed(self, text: str) -> None:
        if self._current_page and self._current_page.enable_search:
            self._current_page.handle_search(text)

    def _on_add_clicked(self) -> None:
        if self._current_page and self._current_page.enable_add:
            self._current_page.handle_add()

    def _update_user_badge(self) -> None:
        if not hasattr(self, "user_badge"):
            return
        full_name = (self.user.get("full_name") or "").strip()
        username = (self.user.get("username") or "Пользователь").strip()
        display_name = full_name or username
        self.user_badge.setText(display_name)


def run() -> None:
    import sys

    db = DatabaseManager()
    auth_service = AuthService(db)

    app = QApplication(sys.argv)
    dialog = AuthDialog(auth_service)
    if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.authenticated_user:
        sys.exit(0)

    user_record = dialog.authenticated_user
    user_info = {
        "id": user_record.get("id"),
        "username": user_record.get("username"),
        "full_name": user_record.get("full_name"),
        "created_at": user_record.get("created_at"),
    }

    window = MainWindow(db=db, user=user_info)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
