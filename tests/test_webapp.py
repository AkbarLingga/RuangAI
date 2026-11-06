import unittest

from web.app import app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_homepage_serves_web_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Komposisi sentimen", response.data)
        self.assertIn(b"Tren sentimen bulanan", response.data)

    def test_data_api_returns_platform_rows(self):
        response = self.client.get("/api/data")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertGreater(payload["total"], 0)
        self.assertEqual(
            {row["platform"] for row in payload["rows"]},
            {"X", "Reddit", "YouTube"},
        )
        self.assertTrue(all(-1 <= row["polarity"] <= 1 for row in payload["rows"]))
        self.assertTrue(all(row["date"] for row in payload["rows"]))
        self.assertEqual(
            set(payload["sentiment_model"]["classes"]),
            {"Positif", "Netral", "Negatif"},
        )

    def test_analyze_endpoint_labels_text(self):
        response = self.client.post(
            "/api/analyze",
            json={"text": "AI membantu pekerjaan, tapi privasi data harus dijaga"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["sentiment"], "Positif")
        self.assertIn("Pekerjaan", payload["topics"])
        self.assertIn("Privasi dan keamanan data", payload["topics"])
        self.assertAlmostEqual(sum(payload["model_probabilities"].values()), 1.0)
        self.assertIn(payload["model_sentiment"], payload["model_probabilities"])

    def test_analyze_endpoint_rejects_empty_text(self):
        response = self.client.post("/api/analyze", json={"text": "  "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
