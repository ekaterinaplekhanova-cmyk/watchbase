import csv, json, time
from pathlib import Path
import sys
import concurrent.futures
sys.path.insert(0, "app")
from generator import generate_package
from utils import save_result

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
rows = all_rows[60:70]


def _extract_summary(idx, row, result, elapsed):
    card = result.get("card", {})
    return {
        "brand": row["brand"].strip(),
        "articul": row["articul"].strip(),
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
    }


def _load_existing_result(brand, articul):
    from utils import _safe_filename
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    safe_articul = _safe_filename(articul)
    safe_brand = _safe_filename(brand)
    path = PROJECT_ROOT / "output" / today / f"{safe_brand}-{safe_articul}" / "result.json"
    if path.exists():
        return json.load(open(path, encoding="utf-8"))
    return None


def _run_with_timeout(articul, brand, timeout=240):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generate_package, articul, brand, None, True)
        return future.result(timeout=timeout)


summary = []
for idx, row in enumerate(rows, start=61):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    existing = _load_existing_result(brand, articul)
    if existing:
        print(f"[{idx}] {brand} {articul} -> loaded existing")
        summary.append(_extract_summary(idx, row, existing, 0.0))
        continue

    print(f"[{idx}] {brand} {articul} -> generating")
    t0 = time.time()
    try:
        result = _run_with_timeout(articul, brand, timeout=240)
    except concurrent.futures.TimeoutError:
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": "timeout after 240s"},
            "source_url": "",
            "source_tier": "error",
            "confidence_status": "manual_check_required",
            "note": "Превышен лимит времени генерации карточки",
        }
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
    summary.append(_extract_summary(idx, row, result, elapsed))

out = PROJECT_ROOT / "output" / "partial_summary_61_70.json"
out.parent.mkdir(parents=True, exist_ok=True)
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {out}")

# Print counts
tiers = {}
statuses = {}
for s in summary:
    tiers[s["source_tier"]] = tiers.get(s["source_tier"], 0) + 1
    statuses[s["confidence_status"]] = statuses.get(s["confidence_status"], 0) + 1
print("processed:", len(summary))
print("tiers:", tiers)
print("statuses:", statuses)
