import csv, json
from pathlib import Path
import sys
sys.path.insert(0, "app")
from utils import _safe_filename

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
rows = all_rows[60:70]

today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")

summary = []
for idx, row in enumerate(rows, start=61):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    safe_articul = _safe_filename(articul)
    safe_brand = _safe_filename(brand)
    path = PROJECT_ROOT / "output" / today / f"{safe_brand}-{safe_articul}" / "result.json"
    if path.exists():
        result = json.load(open(path, encoding="utf-8"))
    else:
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": "result not found"},
            "source_url": "",
            "source_tier": "error",
            "confidence_status": "manual_check_required",
            "note": "result file not found",
        }
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
        "seconds": 0.0,
    })

out = PROJECT_ROOT / "output" / "partial_summary_61_70.json"
out.parent.mkdir(parents=True, exist_ok=True)
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {out}")

tiers = {}
statuses = {}
for s in summary:
    tiers[s["source_tier"]] = tiers.get(s["source_tier"], 0) + 1
    statuses[s["confidence_status"]] = statuses.get(s["confidence_status"], 0) + 1
print("processed:", len(summary))
print("tiers:", tiers)
print("statuses:", statuses)
