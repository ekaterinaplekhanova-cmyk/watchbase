import csv, json, re, time
from pathlib import Path
import sys

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
OUT_DIR = PROJECT_ROOT / "output" / "2026-07-02"

# Seconds from perf.log / existing run
known_seconds = {
    "LW1W-KB": 67.77,
    "AI6008-SS002-430-1": 251.27,
    "M021.626.11.061.00": 61.44,
    "127339": 69.73,
    "210.30.42.20.03.001": 279.91,
    "01 733 7766 4135-07 8 20 05PEB": 64.96,
    "PAM01393": 224.29,
    "PFC914-1020001-400182": 69.47,
    "5811/1G-001": 69.68,
    "P1253 SG TU 1614 4000": 69.1,
}


def _safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(text)).strip("-")


all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
rows = all_rows[49:59]
summary = []
for idx, row in enumerate(rows, start=51):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    safe_articul = _safe_filename(articul)
    safe_brand = _safe_filename(brand)
    result_path = OUT_DIR / f"{safe_brand}-{safe_articul}" / "result.json"
    if result_path.exists():
        result = json.load(open(result_path, encoding="utf-8"))
    else:
        result = {}
    card = result.get("card", {})
    summary.append({
        "brand": brand,
        "articul": articul,
        "note": row.get("note", ""),
        "source_url": result.get("source_url", ""),
        "source_tier": result.get("source_tier", ""),
        "confidence_status": result.get("confidence_status", ""),
        "error": card.get("error", ""),
        "name": card.get("name", ""),
        "collection": card.get("collection", ""),
        "mechanism": card.get("mechanism", ""),
        "caliber": card.get("caliber", ""),
        "diameter": card.get("diameter", ""),
        "water_resistance": card.get("water_resistance", ""),
        "seconds": known_seconds.get(articul, 0.0),
    })

out = PROJECT_ROOT / "output" / "partial_summary_51_60.json"
out.parent.mkdir(parents=True, exist_ok=True)
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {out}")
