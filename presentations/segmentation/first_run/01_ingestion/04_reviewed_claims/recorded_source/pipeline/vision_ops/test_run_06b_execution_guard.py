"""Meaningful offline safety tests; temporary SQLite only; no provider calls."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from run_06b_execution_guard import Guard, REQUIRED_CONFIG, work_key


class GuardTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        parent = root / "presentations/segmentation/run_06b_v1/test_tmp"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        assert Path(self.temp.name).resolve().is_relative_to(parent.resolve())
        self.path = str(Path(self.temp.name) / "guard.sqlite")
        self.policy = {"execution_authorized": True, "tariffs_validated": True,
            "approval_sha256": "synthetic_approval_only", "manifest_sha256": "synthetic_manifest_only",
            "attempt_cap": 2, "ceiling_nanochf": 100, "worst_case_nanochf_per_call": {"ocr": 60, "extract": 30},
            "max_calls_per_job": {"ocr": 1, "extract": 1}}
        self.g = Guard(self.path, self.policy)
        self.config = {key: "synthetic_value" for key in REQUIRED_CONFIG}
        self.identity = {"product_name": "Product", "brand": "Brand", "category_context": "non_dairy"}
        self.key = work_key("a" * 64, self.config, self.identity)

    def tearDown(self):
        self.g.close()
        self.temp.cleanup()

    def test_default_denies_execution(self):
        p = dict(self.policy, execution_authorized=False)
        other = Guard(str(Path(self.temp.name) / "disabled.sqlite"), p)
        try:
            with self.assertRaises(PermissionError):
                other.begin_job(self.key, p["manifest_sha256"])
        finally:
            other.close()

    def test_image_config_and_metadata_changes_create_distinct_work(self):
        changed = [work_key("b" * 64, self.config, self.identity),
            work_key("a" * 64, dict(self.config, model_version="changed"), self.identity),
            work_key("a" * 64, self.config, dict(self.identity, product_name="Changed"))]
        self.assertEqual(len(set(changed + [self.key])), 4)
        with self.assertRaises(ValueError):
            work_key("a" * 64, dict(self.config, model_version="UNRESOLVED"), self.identity)

    def test_resume_no_claim_and_append_only_merge(self):
        self.assertTrue(self.g.begin_job(self.key, self.policy["manifest_sha256"]))
        payload = {"flags": [False] * 34, "full_ocr_text": "Texte français préservé.\n" * 200}
        oid = self.g.append_observation(self.key, "success_no_claims", payload)
        self.g.append_observation(self.key, "failed", {"reason": "later failure"})
        self.assertTrue(self.g.has_success(self.key))
        self.assertEqual(oid, self.g.append_observation(self.key, "success_no_claims", payload))
        self.g.close()
        self.g = Guard(self.path, self.policy)
        self.assertFalse(self.g.begin_job(self.key, self.policy["manifest_sha256"]))
        self.assertEqual(self.g.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)
        saved = json.loads(self.g.db.execute("SELECT payload_json FROM observations WHERE observation_id=?", (oid,)).fetchone()[0])
        self.assertEqual(saved["full_ocr_text"], payload["full_ocr_text"])
        self.assertGreater(len(saved["full_ocr_text"]), 2000)

    def test_attempt_cap_and_manifest_mismatch(self):
        with self.assertRaises(PermissionError):
            self.g.begin_job(self.key, "wrong_manifest")
        for k in [self.key, "b" * 64]:
            self.g.begin_job(k, self.policy["manifest_sha256"])
        with self.assertRaises(PermissionError):
            self.g.begin_job("c" * 64, self.policy["manifest_sha256"])

    def test_atomic_spend_reservation_crash_and_no_blind_retry(self):
        self.g.begin_job(self.key, self.policy["manifest_sha256"])
        self.g.reserve_call("ocr1", self.key, "ocr")
        self.g.close()  # Simulate crash after dispatch; reservation survives.
        self.g = Guard(self.path, self.policy)
        with self.assertRaises(PermissionError):
            self.g.reserve_call("ocr1", self.key, "ocr")
        with self.assertRaises(PermissionError):
            self.g.reserve_call("ocr_retry", self.key, "ocr")
        self.g.reserve_call("extract1", self.key, "extract")
        self.g.begin_job("b" * 64, self.policy["manifest_sha256"])
        with self.assertRaises(PermissionError):
            self.g.reserve_call("ocr2", "b" * 64, "ocr")
        self.assertEqual(self.g.db.execute("SELECT SUM(reserved_nanochf) FROM calls").fetchone()[0], 90)

    def test_overbound_receipt_trips_circuit_and_cannot_overwrite(self):
        self.g.begin_job(self.key, self.policy["manifest_sha256"])
        self.g.reserve_call("ocr1", self.key, "ocr")
        receipt = {"usage": {"billable_images": 1}, "tariff_sha256": "synthetic_tariff", "raw_receipt_sha256": "synthetic_receipt"}
        self.g.receipt("ocr1", "provider-id", 61, "success", **receipt)
        with self.assertRaises(PermissionError):
            self.g.reserve_call("extract1", self.key, "extract")
        with self.assertRaises(Exception):
            self.g.receipt("ocr1", "provider-id", 0, "overwritten", **receipt)

    def test_concurrent_reservations_cannot_overspend(self):
        self.g.begin_job(self.key, self.policy["manifest_sha256"])
        self.g.begin_job("b" * 64, self.policy["manifest_sha256"])
        def submit(key):
            guard = Guard(self.path, self.policy)
            try:
                guard.reserve_call(key, key, "ocr")
                return True
            except PermissionError:
                return False
            finally:
                guard.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, [self.key, "b" * 64]))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.g.db.execute("SELECT SUM(reserved_nanochf) FROM calls").fetchone()[0], 60)

    def test_barcode_key_and_changed_policy_refused(self):
        with self.assertRaises(ValueError):
            self.g.begin_job("1234567890123", self.policy["manifest_sha256"])
        with self.assertRaises(ValueError):
            other = Guard(self.path, dict(self.policy, attempt_cap=3))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"scope": "Offline standalone primitive only; provider adapter and production integration not validated",
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "successful": result.wasSuccessful(), "provider_calls": 0}
    root = Path(__file__).resolve().parents[2]
    out = root / "presentations/segmentation/run_06b_v1/execution_guard_test_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
