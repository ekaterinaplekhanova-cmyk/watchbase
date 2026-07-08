import sys, time
sys.path.insert(0, "app")
from generator import generate_package

brand = "Bvlgari"
articul = "103481"
print(f"Start {brand} {articul}", flush=True)
t0 = time.time()
try:
    result = generate_package(articul, brand, image_path=None, card_only=True)
    print(f"Done in {time.time()-t0:.1f}s", flush=True)
    print(result.get("source_tier"), result.get("confidence_status"), flush=True)
    print(result.get("card", {}).get("name"), flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
