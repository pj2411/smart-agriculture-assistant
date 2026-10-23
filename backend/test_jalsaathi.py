import sys
import unittest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))

from jalsaathi_domain import evaluate_scenario, load_scenarios


class JalSaathiDomainTests(unittest.TestCase):
    def test_exactly_twenty_test_fixtures_load(self):
        payload = load_scenarios()
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["scenarios"]), 20)
        self.assertEqual(payload["mode"], "SIMULATED_TEST_FIXTURES_ONLY")

    def test_dual_alert_case_is_deterministic(self):
        result = evaluate_scenario("js-07")
        self.assertEqual(result["temperature_status"], "high_temperature")
        self.assertEqual(result["moisture_status"], "low_moisture")
        self.assertTrue(result["demo_only"])

    def test_boundary_values_are_normal(self):
        result = evaluate_scenario("js-01", temperature_c=12, moisture_percent=70)
        self.assertEqual(result["temperature_status"], "normal")
        self.assertEqual(result["moisture_status"], "normal")

    def test_manual_override_changes_only_test_readings_and_status(self):
        result = evaluate_scenario("js-01", temperature_c=35, moisture_percent=15)
        self.assertEqual(result["scenario_id"], "js-01")
        self.assertEqual(result["temperature_c"], 35.0)
        self.assertEqual(result["soil_moisture_percent"], 15.0)
        self.assertEqual(result["alerts"], ["high_temperature", "low_moisture"])


if __name__ == "__main__":
    unittest.main()
