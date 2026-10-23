"""Pure JalSaathi scenario and sensor-rule domain logic.

Scenario values are test fixtures only. They must never be described as live
device measurements or verified agronomic targets.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO_PATH = BASE_DIR / "data" / "climate_test_scenarios.json"


class ScenarioNotFound(ValueError):
    pass


def load_scenarios() -> Dict[str, Any]:
    path = Path(os.getenv("CLIMATE_SCENARIOS_PATH", str(DEFAULT_SCENARIO_PATH)))
    if not path.is_file():
        return {"available": False, "scenarios": [], "message": "Scenario fixture file is unavailable."}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "scenarios": [], "message": f"Scenario fixture file could not be read: {exc}"}
    scenarios = payload.get("scenarios", [])
    if len(scenarios) != 20:
        return {"available": False, "scenarios": [], "message": "Scenario fixture must contain exactly 20 cases."}
    return {
        "available": True,
        "dataset_name": payload.get("datasetName", "JalSaathi climate scenario lab"),
        "mode": payload.get("mode", "SIMULATED_TEST_FIXTURES_ONLY"),
        "notice": payload.get("notice", "Test fixtures only."),
        "thresholds_note": payload.get("thresholdsNote", "SIMULATED TEST THRESHOLDS — NOT OPTIMAL CROP RANGES"),
        "scenarios": scenarios,
    }


def _status(value: float, low: float, high: float, low_state: str, high_state: str) -> str:
    if value < low:
        return low_state
    if value > high:
        return high_state
    return "normal"


def evaluate_scenario(scenario_id: str, temperature_c: Optional[float] = None, moisture_percent: Optional[float] = None) -> Dict[str, Any]:
    payload = load_scenarios()
    if not payload["available"]:
        raise ScenarioNotFound(payload["message"])
    scenario = next((item for item in payload["scenarios"] if item.get("id") == scenario_id), None)
    if scenario is None:
        raise ScenarioNotFound(f"Unknown climate scenario '{scenario_id}'.")

    temperature = float(scenario["temperatureC"] if temperature_c is None else temperature_c)
    moisture = float(scenario["soilMoisturePercent"] if moisture_percent is None else moisture_percent)
    thresholds = scenario["thresholds"]
    temp_status = _status(temperature, thresholds["temperature"]["lowC"], thresholds["temperature"]["highC"], "low_temperature", "high_temperature")
    moisture_status = _status(moisture, thresholds["moisture"]["lowPercent"], thresholds["moisture"]["highPercent"], "low_moisture", "high_moisture")
    return {
        "scenario_id": scenario["id"],
        "label": scenario["label"],
        "crop_label": scenario.get("cropLabel"),
        "source": "simulated_scenario",
        "display_label": "SIMULATED SCENARIO — NOT ESP32 DATA",
        "thresholds_label": payload["thresholds_note"],
        "temperature_c": temperature,
        "soil_moisture_percent": moisture,
        "thresholds": thresholds,
        "temperature_status": temp_status,
        "moisture_status": moisture_status,
        "alerts": [status for status in (temp_status, moisture_status) if status != "normal"],
        "expected": scenario.get("expected", {}),
        "demo_only": True,
    }
