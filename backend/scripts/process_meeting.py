from __future__ import annotations

import argparse
import json
from pathlib import Path

from database import init_db
from pipeline.ingest import ingest_pdf_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a meeting PDF into structured summary output")
    parser.add_argument("pdf_path")
    parser.add_argument("--deliver", action="store_true")
    args = parser.parse_args()

    init_db()
    meeting = ingest_pdf_sync(
        pdf_path=args.pdf_path,
        subject=Path(args.pdf_path).stem.replace("-", " ").title(),
        deliver=args.deliver,
    )
    output_dir = Path(__file__).resolve().parents[2] / "backend" / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"meeting-{meeting.id}.json"
    output_path.write_text(json.dumps(meeting.summary_nl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
