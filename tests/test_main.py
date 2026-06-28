import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main as main_module


class UrlShortenerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.TestingSessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        main_module.Base.metadata.create_all(bind=self.engine)

        main_module.rate_limit = lambda *args, **kwargs: None

        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        main_module.app.dependency_overrides[main_module.get_db] = override_get_db
        self.client = TestClient(main_module.app)
        self.addCleanup(self.client.close)
        self.addCleanup(main_module.app.dependency_overrides.clear)

    def test_shorten_url_creates_record_and_returns_short_url(self):
        response = self.client.post(
            "/shorten",
            params={"long_url": "https://example.com"},
            headers={"Idempotency-Key": "id-1"},
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["long_url"], "https://example.com")
        self.assertTrue(body["short_url"].startswith("http://testserver/"))
        self.assertTrue(body["alias"])

        with self.TestingSessionLocal() as db:
            self.assertEqual(db.query(main_module.URL).count(), 1)
            self.assertEqual(db.query(main_module.IdempotencyKey).count(), 1)

    def test_redirect_increases_click_count(self):
        with self.TestingSessionLocal() as db:
            db.add(main_module.URL(alias="abc123", long_url="https://example.com"))
            db.commit()

        response = self.client.get("/abc123", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://example.com")

        with self.TestingSessionLocal() as db:
            updated = db.query(main_module.URL).filter(main_module.URL.alias == "abc123").one()
            self.assertEqual(updated.clicks, 1)

    def test_info_and_delete_endpoints_work(self):
        with self.TestingSessionLocal() as db:
            db.add(main_module.URL(alias="del123", long_url="https://example.org"))
            db.commit()

        info_response = self.client.get("/info/del123")
        self.assertEqual(info_response.status_code, 200)
        self.assertEqual(info_response.json()["alias"], "del123")
        self.assertEqual(info_response.json()["long_url"], "https://example.org")

        delete_response = self.client.delete("/delete/del123")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["message"], "Short URL deleted successfully")

        with self.TestingSessionLocal() as db:
            self.assertEqual(db.query(main_module.URL).filter(main_module.URL.alias == "del123").count(), 0)


if __name__ == "__main__":
    unittest.main()
