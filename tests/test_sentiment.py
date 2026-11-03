import unittest

from sentiment import analyze_sentiment, clean_text, identify_topics, is_noise
from preprocess import build_dataset


class SentimentPipelineTests(unittest.TestCase):
    def test_clean_text_removes_urls_and_preserves_hashtag_word(self):
        self.assertEqual(
            clean_text("Love #ChatGPT https://example.com @someone"),
            "Love ChatGPT",
        )

    def test_negation_reverses_word_polarity(self):
        self.assertEqual(analyze_sentiment("This is not good")[0], "Negatif")
        self.assertEqual(analyze_sentiment("Ini tidak buruk")[0], "Positif")

    def test_neutral_text_has_zero_score(self):
        self.assertEqual(analyze_sentiment("AI is used in a data center"), ("Netral", 0.0))

    def test_multiple_topics_can_be_detected(self):
        topics = identify_topics("AI jobs and education are changing")
        self.assertIn("Pekerjaan", topics)
        self.assertIn("Pendidikan", topics)

    def test_indonesian_environment_topic(self):
        self.assertIn("Lingkungan dan sumber daya", identify_topics("Pusat data memakai banyak air"))

    def test_noise_detection(self):
        self.assertTrue(is_noise("[deleted]"))
        self.assertTrue(is_noise("This action was performed automatically by a bot."))
        self.assertFalse(is_noise("Teknologi AI membantu pekerjaan saya"))

    def test_build_dataset_combines_available_raw_platforms(self):
        dataset, stats = build_dataset()
        self.assertEqual(set(dataset["platform"]), {"X", "Reddit", "YouTube"})
        self.assertEqual(len(dataset), sum(source["kept"] for source in stats.values()))
        self.assertFalse(dataset["clean_text"].str.strip().eq("").any())


if __name__ == "__main__":
    unittest.main()
