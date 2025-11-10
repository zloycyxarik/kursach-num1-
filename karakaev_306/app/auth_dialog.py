from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .auth import AuthService


class AuthDialog(QDialog):
    """Modal dialog that provides login and sign-up tabs."""

    def __init__(self, auth_service: AuthService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.authenticated_user: Optional[dict] = None
        self.setWindowTitle("Авторизация")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Учет автопарка")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Авторизуйтесь или создайте новый аккаунт для доступа к системе.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.login_tab = QWidget()
        self.register_tab = QWidget()
        self.tabs.addTab(self.login_tab, "Вход")
        self.tabs.addTab(self.register_tab, "Регистрация")

        self._build_login_tab()
        self._build_register_tab()

        layout.addWidget(self.tabs)

    def _build_login_tab(self) -> None:
        tab_layout = QVBoxLayout(self.login_tab)
        tab_layout.setContentsMargins(12, 12, 12, 12)
        tab_layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Имя пользователя")
        form.addRow("Имя пользователя", self.login_username)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Пароль")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Пароль", self.login_password)

        tab_layout.addLayout(form)

        self.login_error = QLabel()
        self.login_error.setStyleSheet("color: #dc2626;")
        tab_layout.addWidget(self.login_error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.login_button = QPushButton("Войти")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._handle_login)
        buttons.addWidget(self.login_button)
        tab_layout.addLayout(buttons)

    def _build_register_tab(self) -> None:
        tab_layout = QVBoxLayout(self.register_tab)
        tab_layout.setContentsMargins(12, 12, 12, 12)
        tab_layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.register_full_name = QLineEdit()
        self.register_full_name.setPlaceholderText("Отображаемое имя (необязательно)")
        form.addRow("Имя", self.register_full_name)

        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Не менее 3 символов")
        form.addRow("Имя пользователя*", self.register_username)

        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Не менее 6 символов")
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Пароль*", self.register_password)

        self.register_confirm = QLineEdit()
        self.register_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Подтверждение*", self.register_confirm)

        tab_layout.addLayout(form)

        note = QLabel("Пароль должен содержать минимум 6 символов.")
        note.setStyleSheet("color: #6b7280;")
        tab_layout.addWidget(note)

        self.register_error = QLabel()
        self.register_error.setStyleSheet("color: #dc2626;")
        tab_layout.addWidget(self.register_error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.register_button = QPushButton("Создать аккаунт")
        self.register_button.clicked.connect(self._handle_register)
        buttons.addWidget(self.register_button)
        tab_layout.addLayout(buttons)

    def _handle_login(self) -> None:
        username = self.login_username.text().strip()
        password = self.login_password.text()
        self.login_error.clear()
        user = self.auth_service.authenticate(username, password)
        if user:
            self.authenticated_user = user
            self.accept()
            return
        self.login_error.setText("Неверное имя пользователя или пароль.")

    def _handle_register(self) -> None:
        username = self.register_username.text().strip()
        password = self.register_password.text()
        confirm = self.register_confirm.text()
        full_name = self.register_full_name.text().strip()
        self.register_error.clear()

        if password != confirm:
            self.register_error.setText("Пароли не совпадают.")
            return

        try:
            self.auth_service.register_user(username, password, full_name)
        except ValueError as exc:
            self.register_error.setText(str(exc))
            return

        QMessageBox.information(
            self,
            "Регистрация",
            "Аккаунт создан. Используйте свои данные для входа.",
        )
        self.tabs.setCurrentWidget(self.login_tab)
        self.login_username.setText(username)
        self.login_password.clear()
        self.register_password.clear()
        self.register_confirm.clear()
