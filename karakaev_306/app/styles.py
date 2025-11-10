APP_STYLESHEET = """
* {
    font-family: "Segoe UI", "Inter", "SF Pro Display", sans-serif;
    font-size: 11pt;
    color: #1f2933;
}

QMainWindow {
    background: #f4f6f8;
}

QFrame#Sidebar {
    background-color: #111827;
    border: none;
}

QFrame#Sidebar QLabel {
    color: #e5e7eb;
    font-size: 14pt;
    font-weight: 600;
}

QPushButton#NavButton {
    color: #d1d5db;
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    background-color: transparent;
}

QPushButton#NavButton:hover {
    background-color: #1f2937;
    color: #ffffff;
}

QPushButton#NavButton:checked {
    background-color: #2563eb;
    color: #ffffff;
}

QPushButton#PrimaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #1e4ec9;
}

QPushButton#SecondaryButton {
    background-color: #e5e7eb;
    color: #111827;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 500;
}

QPushButton#SecondaryButton:hover {
    background-color: #d1d5db;
}

QLineEdit, QComboBox, QTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #2563eb;
}

QHeaderView::section {
    background-color: #111827;
    color: #f9fafb;
    padding: 8px;
    border: none;
    font-weight: 600;
}

QTableWidget {
    background: #ffffff;
    border: none;
    gridline-color: #e5e7eb;
    alternate-background-color: #f9fafb;
}

QTableWidget::item {
    padding: 6px;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: transparent;
    border: none;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #9ca3af;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #6b7280;
}

QLabel#SectionTitle {
    font-size: 18pt;
    font-weight: 700;
    color: #111827;
}

QLabel#CardNumber {
    font-size: 24pt;
    font-weight: 700;
    color: #111827;
}

QLabel#CardCaption {
    font-size: 10pt;
    color: #6b7280;
}

QFrame#InfoCard {
    background: #ffffff;
    border-radius: 16px;
    padding: 18px;
    border: 1px solid #e5e7eb;
}

QFrame#HeaderBar {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #e5e7eb;
}

QListWidget {
    border: none;
    background: #ffffff;
}

QLabel#UserBadge {
    background-color: #111827;
    color: #f9fafb;
    padding: 6px 14px;
    border-radius: 16px;
    font-size: 10pt;
    font-weight: 600;
}
"""
