import unittest

from analysis import sentiment
from analysis.sentiment import clean_text, identify_topics, is_noise


class TextPipelineTests(unittest.TestCase):
    def test_clean_text_removes_urls_and_preserves_hashtag_word(self):
        self.assertEqual(
            clean_text("Love #ChatGPT https://example.com @someone"),
            "Love ChatGPT",
        )

    def test_word_lists_are_gone(self):
        self.assertFalse(hasattr(sentiment, "_POSITIVE_WORDS"))
        self.assertFalse(hasattr(sentiment, "_NEGATIVE_WORDS"))
        self.assertFalse(hasattr(sentiment, "analyze_sentiment"))

    def test_topics_can_match_more_than_one_label(self):
        topics = identify_topics("AI could replace jobs and leak personal data")
        self.assertIn("Pekerjaan", topics)
        self.assertIn("Privasi dan keamanan data", topics)

    def test_unmatched_text_gets_other_topic(self):
        self.assertEqual(identify_topics("Nothing relevant here"), "Lainnya")

    def test_indonesian_environment_topic(self):
        self.assertIn("Lingkungan dan sumber daya", identify_topics("Pusat data memakai banyak air"))

    def test_noise_detection(self):
        self.assertTrue(is_noise("[deleted]"))
        self.assertTrue(is_noise("This action was performed automatically by a bot."))
        self.assertFalse(is_noise("Teknologi AI membantu pekerjaan saya"))


if __name__ == "__main__":
    unittest.main()
