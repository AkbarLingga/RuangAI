import unittest

import pandas as pd

from evaluate_sentiment import create_annotation_sample, evaluate_labeled_data


class SentimentEvaluationTests(unittest.TestCase):
    def test_sample_is_reproducible_and_covers_platform_baseline_groups(self):
        data = pd.DataFrame(
            [
                {
                    "platform": platform,
                    "source_id": f"{platform}-{index}",
                    "clean_text": f"AI comment {index}",
                    "sentiment": sentiment,
                }
                for platform in ("X", "Reddit", "YouTube")
                for sentiment in ("Positif", "Netral", "Negatif")
                for index in range(10)
            ]
        )

        first = create_annotation_sample(data, sample_size=18, random_state=7)
        second = create_annotation_sample(data, sample_size=18, random_state=7)

        self.assertEqual(first["row_id"].tolist(), second["row_id"].tolist())
        self.assertEqual(len(first), 18)
        self.assertEqual(set(first["human_sentiment"]), {""})
        self.assertEqual(
            set(zip(first["platform"], first["lexicon_sentiment"])),
            set(
                (platform, sentiment)
                for platform in ("X", "Reddit", "YouTube")
                for sentiment in ("Positif", "Netral", "Negatif")
            ),
        )

    def test_evaluation_compares_baseline_and_train_only_tfidf_model(self):
        rows = []
        for sentiment, text in (
            ("Positif", "helpful useful good"),
            ("Netral", "ordinary discussion about technology"),
            ("Negatif", "harmful dangerous bad"),
        ):
            for index in range(12):
                rows.append(
                    {
                        "clean_text": f"{text} example{index}",
                        "lexicon_sentiment": sentiment,
                        "human_sentiment": sentiment,
                    }
                )

        report = evaluate_labeled_data(pd.DataFrame(rows), random_state=11)

        self.assertEqual(report["labeled_rows"], 36)
        self.assertEqual(report["train_rows"] + report["test_rows"], 36)
        self.assertEqual(report["lexicon_baseline"]["accuracy"], 1.0)
        self.assertIn("macro_f1", report["tfidf_logistic_regression"])
        self.assertEqual(
            len(report["tfidf_logistic_regression"]["confusion_matrix"]), 3
        )


if __name__ == "__main__":
    unittest.main()
