from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "docs" / "openapi.json"


def main() -> None:
    with tempfile.TemporaryDirectory() as data_dir:
        os.environ.setdefault("DATA_DIR", data_dir)
        os.environ.setdefault("LLM_PROVIDER", "openai")

        from app.main import create_app

        app = create_app(data_dir=data_dir, provider_mode="fake")
        schema = app.openapi()

    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
