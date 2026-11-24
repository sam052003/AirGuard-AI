"""開發規格 smoke tests：只確認範例與 30 情境結構，尚非 Agent 執行測試。

不依賴外部 jsonschema 套件。Schema 的完整語意驗證將在 API 實作 PR 增加。
"""
from __future__ import annotations
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

def load(relative):
    return json.loads((DOCS / relative).read_text(encoding="utf-8"))

class ContractSmokeTests(unittest.TestCase):
    def test_schema_files_are_valid_draft202012_json(self):
        for name in ("query.schema.json", "report.schema.json"):
            with self.subTest(schema=name):
                schema = load(f"schemas/{name}")
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["type"], "object")
                self.assertIn("properties", schema)
                self.assertIn("required", schema)

    def test_request_example_has_required_properties(self):
        payload, schema = load("examples/agent-query-request.json"), load("schemas/query.schema.json")
        self.assertTrue(set(schema["required"]) <= set(payload))
        self.assertEqual(payload["timezone"], "Asia/Taipei")
        self.assertIn(payload["population_group"], schema["properties"]["population_group"]["enum"])
        self.assertEqual(payload["station_id"], "999")

    def test_response_example_is_explicitly_unavailable(self):
        payload, schema = load("examples/agent-query-response.json"), load("schemas/report.schema.json")
        self.assertTrue(set(schema["required"]) <= set(payload))
        self.assertEqual(payload["status"], "unavailable")
        self.assertIsNone(payload["official_aqi"])
        self.assertEqual(payload["forecasts"], [])
        self.assertTrue(payload["limitations"])

    def test_thirty_agent_acceptance_cases_are_specs_not_results(self):
        spec = load("agent-acceptance-cases.json")
        cases = spec["cases"]
        self.assertEqual(len(cases), 30)
        self.assertEqual(len({c["id"] for c in cases}), 30)
        self.assertEqual(
            dict(Counter(c["category"] for c in cases)),
            {x: 5 for x in ("normal_activity", "sensitive_activity",
                           "ambiguity", "data_quality", "forecast_horizon",
                           "source_and_safety")},
        )
        allowed = set(load("schemas/report.schema.json")["properties"]["status"]["enum"])
        for case in cases:
            with self.subTest(id=case["id"]):
                self.assertEqual(case["execution_status"], "not_run")
                self.assertEqual(case["fixture"], "synthetic_only")
                self.assertIn(case["expected_status"], allowed)
                self.assertTrue(case["required_behavior"])
                self.assertTrue(case["forbidden_behavior"])

if __name__ == "__main__":
    unittest.main()
