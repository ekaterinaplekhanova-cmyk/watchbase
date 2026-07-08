import csv, json, subprocess, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "app")
from utils import _safe_filename

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT_SUMMARY = OUTPUT_DIR / "partial_summary_41_50.json"

all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
# According to the provided script: rows 40:50 with start=41
target_rows = [(i + 1, row) for i, row in enumerate(all_rows[40:50])]


def run_one(idx, brand, articul):
    brand = brand.strip()
    articul = articul.strip()
    safe_brand = _safe_filename(brand)
    safe_articul = _safe_filename(articul)
    result_dir = OUTPUT_DIR / TODAY / f"{safe_brand}-{safe_articul}"
    result_path = result_dir / "result.json"

    if result_path.exists():
        print(f"[{idx}] {brand} {articul} -> reusing saved result", flush=True)
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)
        return idx, brand, articul, result

    print(f"[{idx}] {brand} {articul} -> starting worker", flush=True)
    cmd = [sys.executable, "run_one_card.py", "--articul", articul, "--brand", brand]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        print(proc.stdout, end="", flush=True)
        if proc.returncode != 0 or not result_path.exists():
            err = proc.stderr.strip() or f"exit code {proc.returncode}"
            print(f"[{idx}] {brand} {articul} -> worker failed: {err}", flush=True)
            result = {
                "articul": articul,
                "brand": brand,
                "card": {"error": err},
                "source_url": "",
                "source_tier": "error",
                "confidence_status": "manual_check_required",
                "note": err,
            }
        else:
            with open(result_path, encoding="utf-8") as f:
                result = json.load(f)
    except subprocess.TimeoutExpired:
        print(f"[{idx}] {brand} {articul} -> TIMEOUT", flush=True)
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": "subprocess timeout after 300s"},
            "source_url": "",
            "source_tier": "error",
            "confidence_status": "manual_check_required",
            "note": "subprocess timeout after 300s",
        }
    return idx, brand, articul, result


def build_summary():
    summary = []
    for idx, row in target_rows:
        brand = row["brand"].strip()
        articul = row["articul"].strip()
        safe_brand = _safe_filename(brand)
        safe_articul = _safe_filename(articul)
        result_path = OUTPUT_DIR / TODAY / f"{safe_brand}-{safe_articul}" / "result.json"
        if result_path.exists():
            with open(result_path, encoding="utf-8") as f:
                result = json.load(f)
        else:
            result = {
                "articul": articul,
                "brand": brand,
                "card": {"error": "result not found"},
                "source_url": "",
                "source_tier": "error",
                "confidence_status": "manual_check_required",
                "note": "result not found",
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
        })
    return summary


results_by_idx = {}
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(run_one, idx, row["brand"], row["articul"]): idx
        for idx, row in target_rows[6:]  # only 47-50 are missing
    }
    for future in as_completed(futures):
        idx, brand, articul, result = future.result()
        results_by_idx[idx] = (brand, articul, result)

summary = build_summary()
OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
json.dump(summary, open(OUT_SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {OUT_SUMMARY}", flush=True)

tiers = dict(Counter(s["source_tier"] for s in summary))
statuses = dict(Counter(s["confidence_status"] for s in summary))
print(f"processed: {len(summary)}", flush=True)
print(f"tiers: {tiers}", flush=True)
print(f"statuses: {statuses}", flush=True)
