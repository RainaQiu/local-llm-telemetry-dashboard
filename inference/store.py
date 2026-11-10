"""Persist normalized inference records for local consumers."""

import json
import os
import tempfile
from pathlib import Path


def save_run(record: dict[str, object], data_dir: Path) -> None:
    """Atomically update the latest record and append it to run history."""

    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    latest_path = data_dir / "latest.json"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=data_dir,
            prefix=".latest-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(record, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()

        os.replace(temporary_path, latest_path)
        temporary_path = None

        history_line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with (data_dir / "history.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as history_file:
            history_file.write(history_line + "\n")
            history_file.flush()
    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
