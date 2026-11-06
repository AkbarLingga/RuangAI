import unittest
from unittest.mock import patch

import pandas as pd

from analysis import config, transformer_model


def fake_sentiment(texts, **_):
    return [
        {
            "sentiment": "Negatif",
            "sentiment_score": 0.9,
            "polarity": -0.8,
            "probabilities": {"Positif": 0.05, "Netral": 0.05, "Negatif": 0.9},
        }
        for _text in texts
    ]


class LabelFrameTests(unittest.TestCase):
    @patch.object(transformer_model, "predict_sentiment", fake_sentiment)
    def test_label_frame_applies_sarcasm_threshold(self):
        scores = [config.SARCASM_THRESHOLD, config.SARCASM_THRESHOLD - 0.01]
        frame = pd.DataFrame({"clean_text": ["a", "b"]})
        with patch.object(transformer_model, "predict_sarcasm", lambda texts, **_: scores):
            labeled = transformer_model.label_frame(frame)
        self.assertEqual(labeled["sarcasm"].tolist(), ["Ya", "Tidak"])
        self.assertEqual(labeled["sentiment"].tolist(), ["Negatif", "Negatif"])
        self.assertNotIn("sentiment", frame.columns)


if __name__ == "__main__":
    unittest.main()
