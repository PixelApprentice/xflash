import json
import os
import tempfile
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from xflash.analysis import analyze_snapshot
from xflash.db import (
    Database,
    get_default_db_path,
    get_portable_dir,
    get_reports_dir,
    is_portable_mode,
)

FIXTURE = Path(__file__).parents[1] / "examples" / "sample_session.json"


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_file = NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.temp_file.close()
        self.db = Database(self.temp_file.name)

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_save_and_retrieve_session(self):
        snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        report = analyze_snapshot(snapshot)

        session_id = self.db.save_session(snapshot, report, operator_notes="Checked at seller cafe")
        self.assertEqual(session_id, snapshot["inspection"]["id"])

        record = self.db.get_session(session_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["id"], session_id)
        self.assertEqual(record["operator_notes"], "Checked at seller cafe")
        self.assertEqual(record["risk_state"], "review")
        self.assertEqual(record["finding_count"], 3)
        self.assertEqual(record["claims"]["ram_gib"], 16.0)
        self.assertEqual(record["claims"]["storage_capacity_gb"], 512.0)
        self.assertIn("battery_capacity", record["coverage"])
        self.assertEqual(len(record["findings"]), 3)

    def test_record_manual_check(self):
        snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        report = analyze_snapshot(snapshot)
        session_id = self.db.save_session(snapshot, report)

        self.db.record_manual_check(session_id, "keyboard", "passed", "All keys responded cleanly")
        self.db.record_manual_check(session_id, "screen", "failed", "1 stuck green pixel near top-right")

        checks = self.db.get_manual_checks(session_id)
        self.assertEqual(checks["keyboard"]["status"], "passed")
        self.assertEqual(checks["screen"]["status"], "failed")
        self.assertEqual(checks["screen"]["notes"], "1 stuck green pixel near top-right")

    def test_list_recent_sessions(self):
        snapshot1 = {"inspection": {"id": "SESS-001"}, "battery": None, "storage": {"devices": []}}
        report1 = analyze_snapshot(snapshot1)
        snapshot2 = {"inspection": {"id": "SESS-002"}, "battery": None, "storage": {"devices": []}}
        report2 = analyze_snapshot(snapshot2)

        self.db.save_session(snapshot1, report1, operator_notes="First run")
        self.db.save_session(snapshot2, report2, operator_notes="Second run")

        sessions = self.db.list_sessions()
        self.assertEqual(len(sessions), 2)
        ids = [s["id"] for s in sessions]
        self.assertIn("SESS-001", ids)
        self.assertIn("SESS-002", ids)

    def test_delete_session(self):
        snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        report = analyze_snapshot(snapshot)
        session_id = self.db.save_session(snapshot, report)

        self.assertTrue(self.db.delete_session(session_id))
        self.assertIsNone(self.db.get_session(session_id))
        self.assertFalse(self.db.delete_session(session_id))


class PortableModeTests(unittest.TestCase):
    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_get_portable_dir_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XFLASH_PORTABLE_DIR"] = tmpdir
            resolved = get_portable_dir()
            self.assertEqual(resolved, Path(tmpdir).resolve())

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ.pop("XFLASH_PORTABLE_DIR", None)
            os.environ["AEGIS_PORTABLE_DIR"] = tmpdir
            resolved = get_portable_dir()
            self.assertEqual(resolved, Path(tmpdir).resolve())

    def test_is_portable_mode_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XFLASH_PORTABLE_DIR"] = tmpdir
            os.environ.pop("XFLASH_PORTABLE", None)
            os.environ.pop("AEGIS_PORTABLE", None)
            os.environ.pop("LAPTOP_INSPECTOR_PORTABLE", None)

            # In an empty temp dir with no .portable file, returns False
            self.assertFalse(is_portable_mode())

            # Setting XFLASH_PORTABLE enables it
            os.environ["XFLASH_PORTABLE"] = "1"
            self.assertTrue(is_portable_mode())
            os.environ.pop("XFLASH_PORTABLE")

            # Setting AEGIS_PORTABLE enables it (backward compatibility)
            os.environ["AEGIS_PORTABLE"] = "1"
            self.assertTrue(is_portable_mode())

            # Setting LAPTOP_INSPECTOR_PORTABLE enables it
            os.environ.pop("AEGIS_PORTABLE")
            os.environ["LAPTOP_INSPECTOR_PORTABLE"] = "true"
            self.assertTrue(is_portable_mode())

    def test_is_portable_mode_marker_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XFLASH_PORTABLE_DIR"] = tmpdir
            os.environ.pop("XFLASH_PORTABLE", None)
            os.environ.pop("AEGIS_PORTABLE", None)
            os.environ.pop("LAPTOP_INSPECTOR_PORTABLE", None)

            marker = Path(tmpdir) / ".portable"
            marker.touch()
            self.assertTrue(is_portable_mode())

    def test_get_default_db_path_portable_vs_normal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XFLASH_PORTABLE_DIR"] = tmpdir
            portable_path = get_default_db_path(portable=True)
            self.assertEqual(portable_path, Path(tmpdir).resolve() / "xflash_data" / "inspections.sqlite3")

            # Legacy fallback if aegis_data exists
            aegis_dir = Path(tmpdir).resolve() / "aegis_data"
            aegis_dir.mkdir(parents=True, exist_ok=True)
            (aegis_dir / "inspections.sqlite3").touch()
            legacy_path = get_default_db_path(portable=True)
            self.assertEqual(legacy_path, aegis_dir / "inspections.sqlite3")

            normal_path = get_default_db_path(portable=False)
            self.assertNotEqual(normal_path, portable_path)
            self.assertTrue(str(normal_path).endswith("inspections.sqlite3"))

    def test_get_reports_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XFLASH_PORTABLE_DIR"] = tmpdir
            reports_dir = get_reports_dir(portable=True)
            self.assertEqual(reports_dir, Path(tmpdir).resolve() / "xflash_reports")
            self.assertTrue(reports_dir.is_dir())

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["XFLASH_PORTABLE_DIR"] = tmpdir
            legacy_rep = Path(tmpdir).resolve() / "aegis_reports"
            legacy_rep.mkdir(parents=True, exist_ok=True)
            reports_dir = get_reports_dir(portable=True)
            self.assertEqual(reports_dir, legacy_rep)
            self.assertTrue(reports_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
