from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .database import DatabaseManager


class DriverRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_all(self) -> List[Dict[str, Any]]:
        with self.db.connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM drivers ORDER BY full_name COLLATE NOCASE;"
            )
            return cursor.fetchall()

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        like = f"%{keyword}%"
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM drivers
                WHERE full_name LIKE ? OR license_number LIKE ? OR phone LIKE ?
                ORDER BY full_name COLLATE NOCASE;
                """,
                (like, like, like),
            )
            return cursor.fetchall()

    def get(self, driver_id: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM drivers WHERE id = ?;",
                (driver_id,),
            )
            return cursor.fetchone()

    def create(self, record: Dict[str, Any]) -> int:
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        values = tuple(record.values())
        with self.db.connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO drivers ({columns}) VALUES ({placeholders});",
                values,
            )
            return cursor.lastrowid

    def update(self, driver_id: int, record: Dict[str, Any]) -> None:
        assignments = ", ".join([f"{key} = ?" for key in record])
        values = tuple(record.values()) + (driver_id,)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE drivers SET {assignments} WHERE id = ?;",
                values,
            )

    def delete(self, driver_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM drivers WHERE id = ?;", (driver_id,))


class VehicleRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_all(self) -> List[Dict[str, Any]]:
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                SELECT v.*, d.full_name AS driver_name
                FROM vehicles v
                LEFT JOIN drivers d ON d.id = v.assigned_driver_id
                ORDER BY v.make COLLATE NOCASE, v.model COLLATE NOCASE;
                """
            )
            return cursor.fetchall()

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        like = f"%{keyword}%"
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                SELECT v.*, d.full_name AS driver_name
                FROM vehicles v
                LEFT JOIN drivers d ON d.id = v.assigned_driver_id
                WHERE v.registry_number LIKE ?
                    OR v.vin LIKE ?
                    OR v.make LIKE ?
                    OR v.model LIKE ?
                    OR d.full_name LIKE ?
                ORDER BY v.make COLLATE NOCASE, v.model COLLATE NOCASE;
                """,
                (like, like, like, like, like),
            )
            return cursor.fetchall()

    def list_due_for_service(self) -> List[Dict[str, Any]]:
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                SELECT v.*
                FROM vehicles v
                WHERE v.next_service_date <= date('now', '+30 days')
                ORDER BY v.next_service_date;
                """
            )
            return cursor.fetchall()

    def create(self, record: Dict[str, Any]) -> int:
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        values = tuple(record.values())
        with self.db.connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO vehicles ({columns}) VALUES ({placeholders});",
                values,
            )
            return cursor.lastrowid

    def update(self, vehicle_id: int, record: Dict[str, Any]) -> None:
        assignments = ", ".join([f"{key} = ?" for key in record])
        values = tuple(record.values()) + (vehicle_id,)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE vehicles SET {assignments} WHERE id = ?;",
                values,
            )

    def delete(self, vehicle_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM vehicles WHERE id = ?;", (vehicle_id,))

    def summary(self) -> Dict[str, Any]:
        with self.db.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM vehicles;").fetchone()["count"]
            active = conn.execute(
                "SELECT COUNT(*) AS count FROM vehicles WHERE status = 'Активен';"
            ).fetchone()["count"]
            in_service = conn.execute(
                "SELECT COUNT(*) AS count FROM vehicles WHERE status = 'В ремонте';"
            ).fetchone()["count"]
            due_service = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM vehicles
                WHERE next_service_date <= date('now', '+30 days');
                """
            ).fetchone()["count"]
            return {
                "total": total,
                "active": active,
                "in_service": in_service,
                "due_service": due_service,
            }


class MaintenanceRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_for_vehicle(self, vehicle_id: int) -> List[Dict[str, Any]]:
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM maintenance
                WHERE vehicle_id = ?
                ORDER BY service_date DESC;
                """,
                (vehicle_id,),
            )
            return cursor.fetchall()

    def create(self, record: Dict[str, Any]) -> int:
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        values = tuple(record.values())
        with self.db.connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO maintenance ({columns}) VALUES ({placeholders});",
                values,
            )
            return cursor.lastrowid

    def update(self, maintenance_id: int, record: Dict[str, Any]) -> None:
        assignments = ", ".join([f"{key} = ?" for key in record])
        values = tuple(record.values()) + (maintenance_id,)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE maintenance SET {assignments} WHERE id = ?;",
                values,
            )

    def delete(self, maintenance_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM maintenance WHERE id = ?;", (maintenance_id,))

    def stats(self) -> List[Tuple[str, float]]:
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                SELECT strftime('%Y-%m', service_date) AS month, SUM(cost) AS total_cost
                FROM maintenance
                GROUP BY strftime('%Y-%m', service_date)
                ORDER BY month DESC
                LIMIT 6;
                """
            )
            return [(row["month"], row["total_cost"]) for row in cursor.fetchall()]

