import csv, json, subprocess, sys, time
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
rows = all_rows[40:50]

summary = []

for idx, row in enumerate(rows, start=41):
    brand = row["brand"].strip()
    articul = row["articul"].strip()
    print(f"[{idx}] {brand} {articul}", flush=True)

    safe_brand = _safe_filename(brand)
    safe_articul = _safe_filename(articul)
    result_dir = OUTPUT_DIR / TODAY / f"{safe_brand}-{safe_articul}"
    result_path = result_dir / "result.json"

    if result_path.exists():
        print(f"  -> reusing saved result", flush=True)
        result = json.load(open(result_path, encoding="utf-8"))
    else:
        cmd = [sys.executable, "run_one_card.py", "--articul", articul, "--brand", brand]
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            elapsed = time.time() - t0
            print(proc.stdout, end="", flush=True)
            if proc.returncode != 0 or not result_path.exists():
                print(f"  -> subprocess failed ({proc.returncode}) after {elapsed:.1f}s: {proc.stderr.strip()}", flush=True)
                result = {
                    "articul": articul,
                    "brand": brand,
                    "card": {"error": f"subprocess failed: {proc.stderr.strip() or proc.returncode}"},
                    "source_url": "",
                    "source_tier": "error",
                    "confidence_status": "manual_check_required",
                    "note": "subprocess failed",
                }
            else:
                result = json.load(open(result_path, encoding="utf-8"))
        except subprocess.TimeoutExpired as e:
            print(f"  -> TIMEOUT after 300s: {e.stderr.strip() if e.stderr else ''}", flush=True)
            result = {
                "articul": articul,
                "brand": brand,
                "card": {"error": "subprocess timeout after 300s"},
                "source_url": "",
                "source_tier": "error",
                "confidence_status": "manual_check_required",
                "note": "subprocess timeout after 300s",
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

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(OUT_SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  -> {result.get('source_tier')} / {result.get('confidence_status')}", flush=True)

print(f"Saved {OUT_SUMMARY}", flush=True)
