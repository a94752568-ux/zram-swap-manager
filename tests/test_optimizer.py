import unittest
from unittest.mock import patch

from optimizer import LightweightPredictor


class LightweightPredictorTests(unittest.TestCase):
    def test_high_cpu_does_not_reduce_swappiness_under_memory_pressure(self):
        predictor = LightweightPredictor()
        predictor.update(75, 95)
        predictor.update(82, 98)

        self.assertEqual(predictor.get_optimal_swappiness(60), 100)

    def test_empty_history_uses_clamped_fallback(self):
        predictor = LightweightPredictor()

        self.assertEqual(predictor.get_optimal_swappiness(140), 100)
        self.assertEqual(predictor.get_optimal_swappiness(-10), 0)

    def test_prediction_stays_within_valid_percent_range(self):
        predictor = LightweightPredictor()
        predictor.update(99, 20)
        predictor.update(100, 20)

        self.assertGreaterEqual(predictor.predict_next_minute_ram(), 0)
        self.assertLessEqual(predictor.predict_next_minute_ram(), 100)

    def test_cpu_cap_is_not_described_as_real_undervolt(self):
        predictor = LightweightPredictor()

        self.assertEqual(predictor.suggest_cpu_cap(10, 90), 60)
        self.assertEqual(predictor.suggest_cpu_cap(90, 90), 70)

    def test_invalid_history_length_is_rejected(self):
        with self.assertRaises(ValueError):
            LightweightPredictor(history_len=1)


if __name__ == "__main__":
    unittest.main()
