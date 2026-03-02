import os
import tempfile
import unittest
import uuid

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ai_study_buddy_test.db")
os.environ["DATABASE_FILE"] = TEST_DB_PATH
os.environ["FLASK_SECRET_KEY"] = "test-secret"

from app import create_app  # noqa: E402


class AppRoutesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_health_endpoint(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("status", data)
        self.assertIn("database", data)

    def _signup_and_login(self, username=None, password="secret123", avatar="🧠"):
        if username is None:
            username = f"user_{uuid.uuid4().hex[:8]}"
        signup = self.client.post(
            "/signup",
            data={"username": username, "password": password, "avatar": avatar},
            follow_redirects=False,
        )
        self.assertEqual(signup.status_code, 302)

        login = self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 302)
        return username, password

    def test_private_score_endpoints_require_login(self):
        self.assertEqual(self.client.get("/chat").status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)
        self.assertEqual(self.client.get("/profile").status_code, 302)
        self.assertEqual(self.client.get("/xp-center").status_code, 302)
        self.assertEqual(self.client.get("/api/stats").status_code, 302)
        self.assertEqual(self.client.get("/api/history").status_code, 302)
        self.assertEqual(self.client.get("/api/leaderboard").status_code, 302)
        self.assertEqual(self.client.post("/api/assistant", json={"message": "help"}).status_code, 302)

    def test_profile_avatar_and_password_update(self):
        username, _ = self._signup_and_login()

        avatar_update = self.client.post(
            "/profile",
            data={"action": "avatar", "avatar": "🐉"},
            follow_redirects=False,
        )
        self.assertEqual(avatar_update.status_code, 302)

        password_update = self.client.post(
            "/profile",
            data={
                "action": "password",
                "current_password": "secret123",
                "new_password": "secret456",
            },
            follow_redirects=False,
        )
        self.assertEqual(password_update.status_code, 302)

        self.client.get("/logout")
        relogin = self.client.post(
            "/login",
            data={"username": username, "password": "secret456"},
            follow_redirects=False,
        )
        self.assertEqual(relogin.status_code, 302)

    def test_save_score_and_private_stats_history_export(self):
        self._signup_and_login()

        save = self.client.post(
            "/save_score",
            data={
                "topic": "Geometry",
                "score": "4",
                "total": "5",
                "difficulty": "Medium",
                "provider": "gemini",
            },
        )
        self.assertEqual(save.status_code, 200)

        stats = self.client.get("/api/stats")
        self.assertEqual(stats.status_code, 200)
        stats_data = stats.get_json()
        self.assertGreaterEqual(stats_data["attempts"], 1)

        history = self.client.get("/api/history?limit=5&q=Geo")
        self.assertEqual(history.status_code, 200)
        history_data = history.get_json()
        self.assertTrue(isinstance(history_data, list))
        self.assertGreaterEqual(len(history_data), 1)

        leaderboard = self.client.get("/api/leaderboard")
        self.assertEqual(leaderboard.status_code, 200)
        leaderboard_data = leaderboard.get_json()
        self.assertTrue(isinstance(leaderboard_data, list))

        xp_center = self.client.get("/xp-center")
        self.assertEqual(xp_center.status_code, 200)

        export = self.client.get("/export_scores.pdf")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.mimetype, "application/pdf")

    def test_assistant_api_returns_guidance(self):
        self._signup_and_login()

        save_owner = self.client.post(
            "/profile",
            data={
                "action": "owner_ai",
                "owner_name": "Kishan Nishad",
                "linkedin_url": "",
                "owner_strengths": "focused, disciplined, helpful",
                "owner_achievements": "consistent learner",
                "linkedin_summary": "Builder and continuous learner",
            },
            follow_redirects=False,
        )
        self.assertEqual(save_owner.status_code, 302)

        response = self.client.post("/api/assistant", json={"message": "How do I study math fast?"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("reply", data)
        self.assertIn("quote", data)
        self.assertNotIn("is my owner", data["reply"])

        owner_response = self.client.post("/api/assistant", json={"message": "Tell me about Kishan and his LinkedIn"})
        self.assertEqual(owner_response.status_code, 200)
        owner_data = owner_response.get_json()
        self.assertIn("Kishan Nishad is my owner", owner_data["reply"])


if __name__ == "__main__":
    unittest.main()
