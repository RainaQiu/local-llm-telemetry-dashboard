import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inference.store import save_run


class StoreTests(unittest.TestCase):
    def test_writes_latest_and_appends_complete_utf8_json_lines(self):
        first = {
            "schema_version": "1.0",
            "run_id": "run-001",
            "prompt": "你好\n第一行",
            "response": "回答一",
        }
        second = {
            "schema_version": "1.0",
            "run_id": "run-002",
            "prompt": "第二个 prompt",
            "response": "回答二",
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "nested" / "runs"
            save_run(first, data_dir)
            save_run(second, data_dir)

            latest_text = (data_dir / "latest.json").read_text(encoding="utf-8")
            self.assertEqual(json.loads(latest_text), second)
            self.assertIn("第二个", latest_text)

            history_text = (data_dir / "history.jsonl").read_text(encoding="utf-8")
            history_lines = history_text.splitlines()
            self.assertEqual(len(history_lines), 2)
            self.assertIn("你好", history_text)
            history_records = [json.loads(line) for line in history_lines]
            self.assertEqual(history_records, [first, second])
            self.assertEqual(
                [record["run_id"] for record in history_records],
                ["run-001", "run-002"],
            )

    def test_temporary_write_failure_preserves_previous_latest_json(self):
        previous = {"run_id": "run-before", "response": "valid record"}
        replacement = {"run_id": "run-after", "response": "not saved"}

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "runs"
            save_run(previous, data_dir)

            with patch("inference.store.json.dump", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    save_run(replacement, data_dir)

            latest_text = (data_dir / "latest.json").read_text(encoding="utf-8")
            self.assertEqual(json.loads(latest_text), previous)
            self.assertEqual(
                len((data_dir / "history.jsonl").read_text(encoding="utf-8").splitlines()),
                1,
            )


if __name__ == "__main__":
    unittest.main()
