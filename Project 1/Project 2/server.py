from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_DB_PATH = Path(__file__).with_name("users.db")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: str | Path) -> None:
    with closing(connect(db_path)) as db, db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                age INTEGER NOT NULL CHECK (age >= 0),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL
            )
            """
        )


def row_to_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "age": row["age"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def validate_email(value: object) -> str | None:
    if not isinstance(value, str) or not EMAIL_RE.match(value):
        return None
    return value.strip().lower()


def validate_age(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        age = int(value)
    except (TypeError, ValueError):
        return None
    return age if age >= 0 else None


def validate_is_active(value: object, default: bool = True) -> bool | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return None


def make_handler(db_path: str | Path):
    database_path = Path(db_path)
    init_db(database_path)

    class UserApiHandler(BaseHTTPRequestHandler):
        server_version = "BackendP2/1.0"

        def log_message(self, format: str, *args) -> None:
            return

        def send_json(self, status: int, payload: dict | list | None = None) -> None:
            body = b"" if payload is None else json.dumps(
                payload, indent=2).encode("utf-8")
            self.send_response(status)
            if payload is not None:
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def read_json(self) -> dict | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                data = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return None
            return data if isinstance(data, dict) else None

        def route_parts(self) -> list[str]:
            path = urlparse(self.path).path.strip("/")
            return [] if not path else path.split("/")

        def do_GET(self) -> None:
            parts = self.route_parts()
            if parts == ["health"]:
                self.send_json(200, {"status": "ok"})
                return
            if parts == ["users"]:
                with closing(connect(database_path)) as db, db:
                    rows = db.execute(
                        "SELECT * FROM users ORDER BY id").fetchall()
                self.send_json(200, [row_to_user(row) for row in rows])
                return
            if len(parts) == 2 and parts[0] == "users":
                user_id = self.parse_user_id(parts[1])
                if user_id is None:
                    self.send_json(400, {"error": "User id must be a number."})
                    return
                with closing(connect(database_path)) as db, db:
                    row = db.execute(
                        "SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if row is None:
                    self.send_json(404, {"error": "User not found."})
                    return
                self.send_json(200, row_to_user(row))
                return
            self.send_json(404, {"error": "Route not found."})

        def do_POST(self) -> None:
            if self.route_parts() != ["users"]:
                self.send_json(404, {"error": "Route not found."})
                return
            payload = self.read_json()
            if payload is None:
                self.send_json(
                    400, {"error": "Request body must be valid JSON object."})
                return
            email = validate_email(payload.get("email"))
            age = validate_age(payload.get("age"))
            is_active = validate_is_active(
                payload.get("is_active"), default=True)
            if email is None:
                self.send_json(400, {"error": "A valid email is required."})
                return
            if age is None:
                self.send_json(
                    400, {"error": "age must be a number greater than or equal to 0."})
                return
            if is_active is None:
                self.send_json(
                    400, {"error": "is_active must be true or false."})
                return
            try:
                with closing(connect(database_path)) as db, db:
                    cursor = db.execute(
                        """
                        INSERT INTO users (email, age, is_active, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            email,
                            age,
                            1 if is_active else 0,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    row = db.execute(
                        "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
                    ).fetchone()
            except sqlite3.IntegrityError:
                self.send_json(
                    409, {"error": "A user with this email already exists."})
                return
            self.send_json(201, row_to_user(row))

        def do_PUT(self) -> None:
            self.update_user()

        def do_PATCH(self) -> None:
            self.update_user()

        def update_user(self) -> None:
            parts = self.route_parts()
            if len(parts) != 2 or parts[0] != "users":
                self.send_json(404, {"error": "Route not found."})
                return
            user_id = self.parse_user_id(parts[1])
            if user_id is None:
                self.send_json(400, {"error": "User id must be a number."})
                return
            payload = self.read_json()
            if payload is None:
                self.send_json(
                    400, {"error": "Request body must be valid JSON object."})
                return
            allowed_fields = {"email", "age", "is_active"}
            if not allowed_fields.intersection(payload):
                self.send_json(
                    400, {"error": "Provide email, age, or is_active to update."})
                return

            updates = {}
            if "email" in payload:
                email = validate_email(payload.get("email"))
                if email is None:
                    self.send_json(
                        400, {"error": "A valid email is required."})
                    return
                updates["email"] = email
            if "age" in payload:
                age = validate_age(payload.get("age"))
                if age is None:
                    self.send_json(
                        400, {"error": "age must be a number greater than or equal to 0."})
                    return
                updates["age"] = age
            if "is_active" in payload:
                is_active = validate_is_active(payload.get("is_active"))
                if is_active is None:
                    self.send_json(
                        400, {"error": "is_active must be true or false."})
                    return
                updates["is_active"] = 1 if is_active else 0

            with closing(connect(database_path)) as db, db:
                existing = db.execute(
                    "SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
                if existing is None:
                    self.send_json(404, {"error": "User not found."})
                    return
                set_clause = ", ".join(f"{field} = ?" for field in updates)
                values = list(updates.values()) + [user_id]
                try:
                    db.execute(
                        f"UPDATE users SET {set_clause} WHERE id = ?", values)
                except sqlite3.IntegrityError:
                    self.send_json(
                        409, {"error": "A user with this email already exists."})
                    return
                row = db.execute(
                    "SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            self.send_json(200, row_to_user(row))

        def do_DELETE(self) -> None:
            parts = self.route_parts()
            if len(parts) != 2 or parts[0] != "users":
                self.send_json(404, {"error": "Route not found."})
                return
            user_id = self.parse_user_id(parts[1])
            if user_id is None:
                self.send_json(400, {"error": "User id must be a number."})
                return
            with closing(connect(database_path)) as db, db:
                cursor = db.execute(
                    "DELETE FROM users WHERE id = ?", (user_id,))
            if cursor.rowcount == 0:
                self.send_json(404, {"error": "User not found."})
                return
            self.send_json(204)

        @staticmethod
        def parse_user_id(value: str) -> int | None:
            try:
                user_id = int(value)
            except ValueError:
                return None
            return user_id if user_id > 0 else None

    return UserApiHandler


def run_server() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = Path(os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
    handler = make_handler(db_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Backend P2 API running at http://{host}:{port}")
    print(f"SQLite database: {db_path}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
