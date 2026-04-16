#!/usr/bin/env python3
"""Inline CSS in email templates using premailer, output to emails/out/.

Usage:
    uv run python scripts/build_emails.py
"""

import shutil
import sys
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "emails"
OUT_DIR = ROOT / "emails" / "out"
OUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR = ROOT / "emails" / "assets"
ASSETS_DIR.mkdir(exist_ok=True)
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Logo_of_Gemeente_Amsterdam.svg/3840px-Logo_of_Gemeente_Amsterdam.svg.png"


def build_template(template_path: Path) -> None:
    try:
        import premailer
    except ImportError:
        print("ERROR: premailer not installed. Run: uv pip install premailer")
        sys.exit(1)

    raw = template_path.read_text(encoding="utf-8")
    inlined = premailer.transform(raw)
    out_path = OUT_DIR / template_path.name.replace(".j2", ".html")
    out_path.write_text(inlined, encoding="utf-8")
    print(f"  ✓ {template_path.name} → {out_path.relative_to(ROOT)}")


def ensure_logo() -> None:
    logo_path = ASSETS_DIR / "amsterdam-logo.png"
    if logo_path.exists():
        return
    try:
        urlretrieve(LOGO_URL, logo_path)
        print(f"  ✓ downloaded {logo_path.relative_to(ROOT)}")
    except Exception:
        fallback = TEMPLATES_DIR / "assets" / "amsterdam-logo.png"
        if fallback.exists():
            shutil.copy2(fallback, logo_path)


def main() -> None:
    templates = list(TEMPLATES_DIR.glob("*.j2"))
    if not templates:
        print("No .j2 templates found in emails/. Nothing to build.")
        return

    print(f"Building {len(templates)} email template(s)...")
    ensure_logo()
    for t in templates:
        build_template(t)
    print("Done.")


if __name__ == "__main__":
    main()
