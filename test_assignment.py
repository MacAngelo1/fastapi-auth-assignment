"""Run with python test_assignment.py. Uses a temporary database, not assignment.db."""
import os
import secrets
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

scratch = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(scratch.name) / "test.db").as_posix()
os.environ["SECRET_KEY"] = secrets.token_hex(32)

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from db_config import Base, Session, engine
from main import app
from models import User
from security import ALGORITHM, SECRET_KEY, verify_password


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def register(self, name):
        response = self.client.post("/auth/register", json={
            "username": name, "email": f"{name}@example.com", "password": "Password123!"
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotIn("password", response.json())
        return response.json()

    def login(self, name, password="Password123!"):
        response = self.client.post("/auth/token", data={"username": name, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["token_type"], "bearer")
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_authentication_and_validation(self):
        alice = self.register("alice")
        headers = self.login("alice")
        self.assertEqual(self.client.get("/users/me").status_code, 401)
        self.assertEqual(self.client.get("/users/me", headers=headers).json()["username"], "alice")
        self.assertEqual(self.client.get("/users/", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/auth/token", data={"username": "alice", "password": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/auth/register", json={"username": "alice", "email": "new@example.com", "password": "Password123!"}).status_code, 409)
        self.assertEqual(self.client.post("/auth/register", json={"username": "other", "email": "alice@example.com", "password": "Password123!"}).status_code, 409)
        self.assertEqual(self.client.put("/users/me", headers=headers, json={"role": "admin"}).status_code, 422)
        self.assertEqual(self.client.put("/users/me", headers=headers, json={"email": None}).status_code, 422)
        self.assertEqual(self.client.post("/auth/register", json={"username": "other", "email": "other@example.com", "password": "Password123!", "role": "admin"}).status_code, 422)
        self.assertEqual(self.client.post("/auth/register", json={"username": "other", "email": "other@example.com", "password": "é" * 40}).status_code, 422)
        with Session() as db:
            user = db.get(User, alice["id"])
            self.assertNotEqual(user.password, "Password123!")
            self.assertTrue(verify_password("Password123!", user.password))

        now = datetime.now(timezone.utc)
        expired = jwt.encode({"sub": str(alice["id"]), "iat": now - timedelta(minutes=2), "exp": now - timedelta(minutes=1)}, SECRET_KEY, algorithm=ALGORITHM)
        response = self.client.get("/users/me", headers={"Authorization": "Bearer " + expired})
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["detail"])
        missing_exp = jwt.encode({"sub": str(alice["id"]), "iat": now}, SECRET_KEY, algorithm=ALGORITHM)
        for token in ["invalid", missing_exp]:
            self.assertEqual(self.client.get("/users/me", headers={"Authorization": "Bearer " + token}).status_code, 401)

        self.assertEqual(self.client.put("/users/me", headers=headers, json={"password": "Changed123!", "full_name": "Alice"}).status_code, 200)
        self.login("alice", "Changed123!")
        self.assertEqual(self.client.post("/auth/token", data={"username": "alice", "password": "Password123!"}).status_code, 401)
        with Session() as db:
            user = db.get(User, alice["id"])
            user.disabled = True
            db.commit()
        self.assertEqual(self.client.get("/users/me", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/auth/token", data={"username": "alice", "password": "Changed123!"}).status_code, 403)

    def test_notes_roles_and_account_deletion(self):
        alice = self.register("alice")
        bob = self.register("bobby")
        admin = self.register("admin")
        ah, bh, dh = self.login("alice"), self.login("bobby"), self.login("admin")
        with Session() as db:
            db.get(User, admin["id"]).role = "admin"
            db.get(User, bob["id"]).role = "editor"
            db.commit()
        self.assertEqual(self.client.get("/users/", headers=dh).status_code, 200)
        self.assertEqual(self.client.get("/users/", headers=bh).status_code, 403)
        ids = []
        for public in [False, True]:
            response = self.client.post("/notes/", headers=ah, json={"title": "Python revision", "content": "SQLAlchemy lesson", "is_public": public, "tags": ["python"]})
            self.assertEqual(response.status_code, 201, response.text)
            ids.append(response.json()["id"])
        private, public = ids
        self.assertEqual(len(self.client.get("/notes/", headers=ah).json()), 2)
        self.assertEqual(len(self.client.get("/notes/", headers=bh).json()), 1)
        self.assertEqual(len(self.client.get("/notes/", headers=dh).json()), 2)
        self.assertEqual(self.client.get(f"/notes/{private}", headers=bh).status_code, 403)
        self.assertEqual(self.client.get(f"/notes/{public}", headers=bh).status_code, 200)
        self.assertEqual(self.client.get(f"/notes/{public}").status_code, 401)
        for note_id in ids:
            self.assertEqual(self.client.put(f"/notes/{note_id}", headers=bh, json={"title": "No"}).status_code, 403)
            self.assertEqual(self.client.delete(f"/notes/{note_id}", headers=bh).status_code, 403)
        self.assertEqual(len(self.client.get("/notes/?tag=python&search_term=sqlalchemy", headers=bh).json()), 1)
        self.assertEqual(self.client.get("/notes/?tag=py", headers=bh).json(), [])
        self.assertEqual(self.client.get("/notes/?search_term=nomatch", headers=ah).json(), [])
        self.assertEqual(self.client.put(f"/notes/{private}", headers=ah, json={"title": "Updated"}).status_code, 200)
        self.assertEqual(self.client.put(f"/notes/{private}", headers=dh, json={"tags": []}).status_code, 200)
        self.assertEqual(self.client.put(f"/notes/{private}", headers=ah, json={"title": None}).status_code, 422)
        self.assertEqual(self.client.put(f"/notes/{private}", headers=ah, json={"owner": "bobby"}).status_code, 422)
        self.assertEqual(self.client.get("/notes/99999", headers=ah).status_code, 404)
        self.assertEqual(self.client.put("/users/me", headers=ah, json={"username": "alice_new"}).status_code, 200)
        self.assertEqual(self.client.get(f"/notes/{private}", headers=ah).json()["owner"], "alice_new")
        self.assertEqual(self.client.delete(f"/notes/{public}", headers=dh).status_code, 204)
        self.assertEqual(self.client.delete("/users/me", headers=ah).status_code, 204)
        self.assertEqual(self.client.get("/users/me", headers=ah).status_code, 401)
        self.assertEqual(self.client.get(f"/notes/{private}", headers=dh).status_code, 404)
        self.register("alice_new")
        self.assertEqual(self.client.get("/users/me", headers=ah).status_code, 401)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        engine.dispose()
        scratch.cleanup()
