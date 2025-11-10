from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .security import hash_password


DB_FILE = Path("transport_fleet.db")


def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    columns = [col[0] for col in cursor.description]
    return {col: row[idx] for idx, col in enumerate(columns)}


class DatabaseManager:
    """Lightweight wrapper to manage SQLite connections and initialization."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_FILE
        self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_initialized()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        try:
            connection.row_factory = _dict_factory
            connection.execute("PRAGMA foreign_keys = ON;")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _ensure_initialized(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = _dict_factory
            connection.execute("PRAGMA foreign_keys = ON;")
            cursor = connection.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    license_number TEXT,
                    license_expiry TEXT,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registry_number TEXT NOT NULL UNIQUE,
                    vin TEXT,
                    make TEXT NOT NULL,
                    model TEXT NOT NULL,
                    year INTEGER,
                    mileage INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'Активен',
                    acquisition_date TEXT,
                    next_service_date TEXT,
                    fuel_type TEXT,
                    assigned_driver_id INTEGER,
                    notes TEXT,
                    FOREIGN KEY (assigned_driver_id)
                        REFERENCES drivers(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS maintenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    service_date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    mileage INTEGER,
                    cost REAL DEFAULT 0,
                    service_center TEXT,
                    notes TEXT,
                    FOREIGN KEY (vehicle_id)
                        REFERENCES vehicles(id) ON DELETE CASCADE
                );
                """
            )
            connection.commit()
            self._ensure_default_user(cursor)
            self._ensure_seed_data(cursor)
            connection.commit()

    def _ensure_default_user(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        if cursor.fetchone()["count"]:
            return
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, full_name)
            VALUES (?, ?, ?);
            """,
            ("admin", hash_password("admin123"), "Администратор"),
        )

    def _ensure_seed_data(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("SELECT COUNT(*) AS count FROM vehicles;")
        if cursor.fetchone()["count"]:
            return

        cursor.executescript(
            """
            INSERT INTO drivers (full_name, phone, email, license_number, license_expiry, notes)
            VALUES
                ('Иван Петров', '+7 900 111-22-33', 'ivan.petrov@example.com', '77 12 345678', '2026-04-15', 'Стаж 8 лет'),
                ('Анна Смирнова', '+7 901 222-33-44', 'anna.smirnova@example.com', '77 65 432109', '2025-10-01', 'Категории B, C'),
                ('Сергей Кузнецов', '+7 902 333-44-55', 'sergey.kuznetsov@example.com', '77 98 765432', '2027-06-30', 'Работает ночными сменами');

            INSERT INTO vehicles (registry_number, vin, make, model, year, mileage, status, acquisition_date,
                                  next_service_date, fuel_type, assigned_driver_id, notes)
            VALUES
                ('А123ВС77', 'WAUZZZ8V2GA123456', 'Audi', 'A4', 2019, 86500, 'Активен', '2019-05-10', '2024-11-01', 'Бензин', 1, 'Нужна замена тормозных колодок.'),
                ('Х555КУ97', 'JTMBD33V286123457', 'Toyota', 'RAV4', 2018, 125400, 'В ремонте', '2018-08-25', '2024-09-15', 'Бензин', 2, 'Проблемы с коробкой передач.'),
                ('М777ОР77', 'WDBUF56X18B123458', 'Mercedes-Benz', 'E200', 2020, 45200, 'Активен', '2020-02-17', '2025-02-10', 'Дизель', 3, 'Используется для VIP клиентов.');

            INSERT INTO maintenance (vehicle_id, service_date, description, mileage, cost, service_center, notes)
            VALUES
                (1, '2024-01-12', 'ТО-60 000: замена масла, фильтров, свечей', 82000, 28000, 'Ауди Центр Москва', 'Рекомендована диагностика подвески'),
                (2, '2023-11-05', 'Ремонт подвески', 118000, 54000, 'Toyota Major', 'Требуется повторная проверка через 5000 км'),
                (3, '2024-02-20', 'Плановое ТО, обновление ПО', 43000, 35000, 'Звезда столицы', 'Замечаний нет');
            """
        )
