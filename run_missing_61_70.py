import csv, json, time
from pathlib import Path
import sys
import concurrent.futures
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
sys.path.insert(0, "app")
from generator import generate_package
from utils import save_result

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
rows = all_rows[60:70]


def _extract_summary(row, result, elapsed):
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


def _run_with_timeout(articul, brand, timeout=360):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generate_package, articul, brand, None, True)
        return future.result(timeout=timeout)


for idx, row in enumerate(rows, start=61):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    existing = _load_existing_result(brand, articul)
    if existing and not existing.get("card", {}).get("error"):
        print(f"[{idx}] {brand} {articul} -> keep existing")
        continue
    print(f"[{idx}] {brand} {articul} -> generating")
    t0 = time.time()
    try:
        result = _run_with_timeout(articul, brand, timeout=360)
    except concurrent.futures.TimeoutError:
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": "timeout after 360s"},
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
    print(_extract_summary(row, result, elapsed))
