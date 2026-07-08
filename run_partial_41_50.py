import csv, json, time
from pathlib import Path
import sys
sys.path.insert(0, "app")
from generator import generate_package
from utils import save_result

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
rows = all_rows[40:50]
summary = []
for idx, row in enumerate(rows, start=41):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    print(f"[{idx}] {brand} {articul}")
    t0 = time.time()
    try:
        result = generate_package(articul, brand, image_path=None, card_only=True)
    except Exception as e:
        result = {"articul": articul, "brand": brand, "card": {"error": str(e)}, "source_url": "", "source_tier": "error", "confidence_status": "manual_check_required", "note": str(e)}
    elapsed = time.time() - t0
    save_result(articul, brand, result)
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
        "seconds": round(elapsed, 2),
    })
out = PROJECT_ROOT / "output" / "partial_summary_41_50.json"
out.parent.mkdir(parents=True, exist_ok=True)
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {out}")
