"""Массовый прогон брендов в режиме "только карточка".

Запуск из корня проекта:
    python app/batch_brands.py --input input/brands_test.csv
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Добавляем app/ в путь, чтобы импортировать generator и utils
APP_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = APP_DIR.parent.resolve()
sys.path.insert(0, str(APP_DIR))

from generator import generate_package
from utils import save_result


def load_brands_csv(csv_path):
    """Загружает CSV с колонками brand, articul, collection, note."""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Нормализуем ключи: убираем BOM, лишние пробелы и окружающие кавычки.
            rows.append({
                key.strip().strip('"').strip("﻿"): value
                for key, value in row.items()
            })
    return rows


def run_batch(csv_path, max_items=None):
    rows = load_brands_csv(csv_path)
    if max_items:
        rows = rows[:max_items]

    print(f"[{datetime.now().isoformat()}] Начинаем обработку {len(rows)} брендов (только карточка)")
    print(f"[{datetime.now().isoformat()}] Ожидаемое время: ~{len(rows) * 2} минут")

    summary = []
    for idx, row in enumerate(rows, start=1):
        brand = row.get("brand", "").strip()
        articul = row.get("articul", "").strip()
        note = row.get("note", "").strip()

        print(f"\n[{idx}/{len(rows)}] {brand} {articul}")
        start = time.time()

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
                "note": f"Exception: {e}",
            }
            print(f"    ⚠️ Ошибка: {e}")

        elapsed = time.time() - start
        print(f"    Время: {elapsed:.1f} сек | Источник: {result.get('source_tier', '-')}")

        out_dir = save_result(articul, brand, result)
        print(f"    Сохранено: {out_dir}")

        card = result.get("card", {})
        summary.append({
            "brand": brand,
            "articul": articul,
            "note": note,
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

    # Сохраняем сводку
    summary_path = PROJECT_ROOT / "output" / datetime.now().strftime("%Y-%m-%d") / "brands_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    csv_path_out = summary_path.with_suffix(".csv")
    with open(csv_path_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys() if summary else [])
        writer.writeheader()
        writer.writerows(summary)

    print(f"\n[{datetime.now().isoformat()}] Готово. Сводка: {summary_path}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Массовый прогон брендов в режиме карточки")
    parser.add_argument("--input", default="input/brands_test.csv", help="CSV с брендами/артикулами")
    parser.add_argument("--max", type=int, default=None, help="Ограничить число брендов")
    args = parser.parse_args()

    csv_full_path = PROJECT_ROOT / args.input
    run_batch(str(csv_full_path), max_items=args.max)


if __name__ == "__main__":
    main()
