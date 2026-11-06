import unittest
from unittest.mock import patch

from web.app import app


FAKE_RESULT = {
    "sentiment": "Negatif",
    "sentiment_score": 0.9,
    "polarity": -0.8,
    "probabilities": {"Positif": 0.05, "Netral": 0.05, "Negatif": 0.9},
    "sarcasm": "Ya",
    "sarcasm_score": 0.8,
}


class WebAppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_homepage_serves_web_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Komposisi sentimen", response.data)
        self.assertIn(b"Tren sentimen per platform", response.data)
        self.assertIn(b"sarcasm-filter", response.data)

    def test_data_api_returns_platform_rows(self):
        response = self.client.get("/api/data")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 6000)
        self.assertEqual(
            {row["platform"] for row in payload["rows"]},
            {"X", "Reddit", "YouTube"},
        )
        self.assertTrue(all(-1 <= row["polarity"] <= 1 for row in payload["rows"]))
        self.assertTrue(all(row["date"] for row in payload["rows"]))
        self.assertEqual({row["sarcasm"] for row in payload["rows"]}, {"Ya", "Tidak"})

    @patch("analysis.transformer_model.analyze_text", return_value=FAKE_RESULT)
    def test_analyze_endpoint_labels_text(self, _analyze):
        response = self.client.post(
            "/api/analyze",
            json={"text": "AI could replace jobs and leak personal data"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["sentiment"], "Negatif")
        self.assertEqual(payload["sarcasm"], "Ya")
        self.assertIn("Pekerjaan", payload["topics"])

    def test_analyze_endpoint_rejects_empty_text(self):
        response = self.client.post("/api/analyze", json={"text": "  "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
