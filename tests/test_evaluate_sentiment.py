import tempfile
import unittest
from pathlib import Path

import pandas as pd

from analysis.evaluate_sentiment import (
    create_annotation_sample,
    evaluate_labeled_data,
    write_label_workbook,
)


class SentimentEvaluationTests(unittest.TestCase):
    def test_sample_is_reproducible_and_covers_platform_groups(self):
        data = pd.DataFrame(
            [
                {
                    "platform": platform,
                    "source_id": f"{platform}-{sentiment}-{index}",
                    "clean_text": f"AI comment {index}",
                    "sentiment": sentiment,
                    "sarcasm": "Tidak",
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
        self.assertEqual(set(first["human_sarcasm"]), {""})
        self.assertEqual(len(set(zip(first["platform"], first["model_sentiment"]))), 9)

    def test_evaluation_compares_model_with_human_labels(self):
        annotations = pd.DataFrame(
            {
                "model_sentiment": ["Positif", "Netral", "Negatif", "Negatif"],
                "human_sentiment": ["Positif", "Netral", "Negatif", "Positif"],
                "model_sarcasm": ["Ya", "Tidak", "Tidak", "Ya"],
                "human_sarcasm": ["Ya", "Tidak", "", ""],
            }
        )

        report = evaluate_labeled_data(annotations)

        self.assertEqual(report["sentiment"]["rows"], 4)
        self.assertEqual(report["sentiment"]["accuracy"], 0.75)
        self.assertEqual(report["sarcasm"]["rows"], 2)
        self.assertEqual(report["sarcasm"]["accuracy"], 1.0)

    def test_sarcasm_extra_rows_only_count_for_flag_precision(self):
        annotations = pd.DataFrame(
            {
                "sample_group": ["acak", "acak", "tambahan_sarkasme", "tambahan_sarkasme"],
                "model_sentiment": ["Positif", "Negatif", "Positif", "Positif"],
                "human_sentiment": ["Positif", "Negatif", "Negatif", "Negatif"],
                "model_sarcasm": ["Tidak", "Ya", "Ya", "Ya"],
                "human_sarcasm": ["Tidak", "Ya", "Ya", "Tidak"],
            }
        )

        report = evaluate_labeled_data(annotations)

        self.assertEqual(report["sentiment"]["rows"], 2)
        self.assertEqual(report["sentiment"]["accuracy"], 1.0)
        self.assertEqual(report["sarcasm_flag_precision"]["rows"], 3)
        self.assertAlmostEqual(report["sarcasm_flag_precision"]["precision"], 2 / 3)

    def test_label_workbook_hides_model_answers(self):
        sample = pd.DataFrame(
            {
                "row_id": [1, 2],
                "platform": ["X", "Reddit"],
                "clean_text": ["=1+1 is funny", "AI is fine"],
                "model_sentiment": ["Positif", "Netral"],
            }
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "label.xlsx"
            write_label_workbook(sample, path, random_state=1)
            labels = pd.read_excel(path, sheet_name="Label", keep_default_na=False)

        self.assertEqual(len(labels), 2)
        self.assertNotIn("model_sentiment", labels.columns)
        self.assertIn("=1+1 is funny", labels["komentar"].tolist())

    def test_evaluation_rejects_unknown_label(self):
        annotations = pd.DataFrame(
            {
                "model_sentiment": ["Positif"],
                "human_sentiment": ["Bagus"],
                "model_sarcasm": ["Tidak"],
                "human_sarcasm": [""],
            }
        )
        with self.assertRaises(ValueError):
            evaluate_labeled_data(annotations)


if __name__ == "__main__":
    unittest.main()
