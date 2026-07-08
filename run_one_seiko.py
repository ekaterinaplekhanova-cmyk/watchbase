import json, time
from pathlib import Path
import sys
sys.path.insert(0, "app")
from generator import generate_package
from utils import save_result

PROJECT_ROOT = Path(".").resolve()
articul = "SRPD21K1"
brand = "Seiko"
print(f"Generating {brand} {articul}")
t0 = time.time()
try:
    result = generate_package(articul, brand, image_path=None, card_only=True)
except Exception as e:
    result = {"articul": articul, "brand": brand, "card": {"error": str(e)}, "source_url": "", "source_tier": "error", "confidence_status": "manual_check_required", "note": str(e)}
elapsed = time.time() - t0
save_result(articul, brand, result)
card = result.get("card", {})
summary = {
    "brand": brand,
    "articul": articul,
    "source_url": result.get("source_url", ""),
    "source_tier": result.get("source_tier", ""),
    "confidence_status": result.get("confidence_status", ""),
    "error": card.get("error", ""),
    "name": card.get("name", ""),
    "seconds": round(elapsed, 2),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
