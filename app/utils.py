import json
import re
import csv
import io
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def load_template():
    path = TEMPLATES_DIR / "watch_card_template.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_name(brand, collection, articul):
    parts = [p for p in [brand, collection, articul] if p]
    return " ".join(parts)


def _safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(text)).strip("-")


def save_result(articul, brand, data):
    today = datetime.now().strftime("%Y-%m-%d")
    safe_articul = _safe_filename(articul)
    safe_brand = _safe_filename(brand)
    out_dir = OUTPUT_DIR / today / f"{safe_brand}-{safe_articul}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    card = data.get("card", {})
    if card and "error" not in card:
        # Save card as Excel/CSV for CMS import
        card_for_export = dict(card)
        if isinstance(card_for_export.get("additional_functions"), list):
            card_for_export["additional_functions"] = ", ".join(
                str(f).strip() for f in card_for_export["additional_functions"] if f
            )

        # Add metadata columns
        card_for_export["confidence_status"] = data.get("confidence_status", "")
        card_for_export["source_url"] = data.get("source_url", "")

        df = pd.DataFrame([card_for_export])
        df.to_excel(out_dir / "card_import.xlsx", index=False, engine="openpyxl")
        df.to_csv(out_dir / "card_import.csv", index=False, encoding="utf-8")

    return out_dir
