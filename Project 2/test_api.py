from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import make_handler


class UserApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test-users.db"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.db_path))
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tempdir.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request) as response:
                raw = response.read()
                data = json.loads(raw.decode("utf-8")) if raw else None
                return response.status, data
        except HTTPError as error:
            raw = error.read()
            data = json.loads(raw.decode("utf-8")) if raw else None
            return error.code, data

    def test_crud_lifecycle_and_duplicate_email_conflict(self) -> None:
        status, created = self.request(
            "POST",
            "/users",
            {"email": "ada@example.com", "age": 24},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["email"], "ada@example.com")
        self.assertEqual(created["age"], 24)
        self.assertTrue(created["is_active"])

        status, duplicate = self.request(
            "POST",
            "/users",
            {"email": "ada@example.com", "age": 24},
        )
        self.assertEqual(status, 409)
        self.assertIn("already exists", duplicate["error"])

        status, users = self.request("GET", "/users")
        self.assertEqual(status, 200)
        self.assertEqual(len(users), 1)

        user_id = created["id"]
        status, updated = self.request(
            "PATCH",
            f"/users/{user_id}",
            {"age": 25, "is_active": False},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["age"], 25)
        self.assertFalse(updated["is_active"])

        status, deleted = self.request("DELETE", f"/users/{user_id}")
        self.assertEqual(status, 204)
        self.assertIsNone(deleted)

        status, users = self.request("GET", "/users")
        self.assertEqual(status, 200)
        self.assertEqual(users, [])


if __name__ == "__main__":
    unittest.main()
