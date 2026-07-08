import csv, json, sys, time
from pathlib import Path

sys.path.insert(0, "app")
from generator import generate_package
from utils import save_result

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"

if len(sys.argv) != 3:
    print("Usage: python run_slice.py <start_index> <end_index>", flush=True)
    sys.exit(1)

start_idx = int(sys.argv[1])
end_idx = int(sys.argv[2])

all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
rows = all_rows[start_idx - 1:end_idx]
summary = []

for idx, row in enumerate(rows, start=start_idx):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    print(f"[{idx}] {brand} {articul}", flush=True)
    t0 = time.time()
    try:
        result = generate_package(articul, brand, image_path=None, card_only=True)
    except Exception as e:
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": str(e)},
            "source_url": "",
            "source_tier": "error",
            "confidence_status": "manual_check_required",
            "note": str(e),
        }
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
    print(f"[{idx}] done in {elapsed:.1f}s tier={result.get('source_tier')} status={result.get('confidence_status')}", flush=True)

out = PROJECT_ROOT / "output" / f"partial_summary_{start_idx}_{end_idx}.json"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"Saved {out}", flush=True)
