import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, "app")
from generator import generate_package
from utils import save_result


def run(articul, brand):
    print(f"START {brand} {articul}", flush=True)
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
    print(f"DONE {brand} {articul} {result.get('confidence_status')} {result.get('source_tier')} {elapsed:.2f}s", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--articul", required=True)
    parser.add_argument("--brand", required=True)
    args = parser.parse_args()
    run(args.articul, args.brand)
