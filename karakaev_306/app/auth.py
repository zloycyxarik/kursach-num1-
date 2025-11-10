from __future__ import annotations

from typing import Optional

from .database import DatabaseManager
from .security import hash_password, verify_password


class AuthService:
    """High-level service to manage user accounts and authentication."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        username = username.strip().lower()
        if not username or not password:
            return None
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE lower(username) = ?;",
                (username,),
            ).fetchone()
            if not row:
                return None
            if verify_password(password, row["password_hash"]):
                return row
        return None

    def user_exists(self, username: str) -> bool:
        username = username.strip().lower()
        if not username:
            return False
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE lower(username) = ?;",
                (username,),
            ).fetchone()
            return bool(row)

    def register_user(self, username: str, password: str, full_name: str = "") -> int:
        username = username.strip()
        if len(username) < 3:
            raise ValueError("Имя пользователя должно содержать не менее 3 символов.")
        if len(password) < 6:
            raise ValueError("Пароль должен содержать не менее 6 символов.")
        if self.user_exists(username):
            raise ValueError("Пользователь с таким именем уже существует.")

        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name)
                VALUES (?, ?, ?);
                """,
                (username, hash_password(password), full_name.strip() or None),
            )
            return cursor.lastrowid

