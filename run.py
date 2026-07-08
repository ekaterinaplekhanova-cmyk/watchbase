"""
Оркестратор MVP для генерации контента по артикулу часов.

Запуск вручную:
    python run.py --articul 116610LN --brand Rolex --collection Submariner --condition new

или:
    python run.py --input input/articuls.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.resolve()
TEMPLATES_DIR = PROJECT_ROOT / "templates"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"
INPUT_DIR = PROJECT_ROOT / "input"
DATA_DIR = PROJECT_ROOT / "data"


def load_template():
    """Загружает шаблон карточки товара."""
    path = TEMPLATES_DIR / "watch_card_template.json"
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompt(name):
    """Загружает промпт агента из prompts/."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Промпт не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_tov():
    """Загружает Tone of Voice из data/tov_social.md."""
    path = DATA_DIR / "tov_social.md"
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ask_user_questions(condition):
    """
    Запрашивает у пользователя обязательные уточнения.
    В MVP эти данные передаются через аргументы CLI или CSV.
    """
    questions = {
        "condition": None,
        "sorting_form": None,
        "warranty": None,
        "price": None,
        "bezel": None,
        "accessories": None,
        "bracelet_strap_condition": None,
        "case_condition": None,
        "glass_condition": None,
        "movement_condition": None,
    }

    # В MVP вопросы задаются через CLI; здесь оставляем структуру для будущего интерактива.
    return questions


def prepare_output_dir(brand, articul):
    """Создаёт папку для результатов: output/YYYY-MM-DD/brand-articul/."""
    today = datetime.now().strftime("%Y-%m-%d")
    safe_articul = articul.replace(" ", "_").replace("/", "-")
    safe_brand = brand.replace(" ", "_")
    out_dir = OUTPUT_DIR / today / f"{safe_brand}-{safe_articul}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_json(out_dir, filename, data):
    path = out_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_md(out_dir, filename, text):
    path = out_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def validate_card(card, template):
    """Проверяет карточку на соответствие шаблону и базовые правила."""
    errors = []
    required = ["articul", "brand", "name", "mechanism", "caliber", "case_material",
                "bracelet_strap_material", "diameter", "water_resistance", "description", "source_url"]
    for field in required:
        if not card.get(field):
            errors.append(f"Отсутствует обязательное поле: {field}")

    # Проверка формата артикула
    articul = card.get("articul", "")
    if articul and articul != articul.upper():
        errors.append("Артикул должен быть заглавными буквами")

    # Проверка формата водозащиты
    water = card.get("water_resistance", "")
    if water and not str(water).endswith(" м"):
        errors.append("Водозащита должна быть в метрах (например, '300 м')")

    return errors


def run_single(articul, brand, collection, condition, extra=None):
    """Запускает конвейер для одного артикула."""
    if extra is None:
        extra = {}

    print(f"\n[Оркестратор] Старт обработки: {brand} {collection} {articul}")
    print(f"[Оркестратор] Состояние: {condition}")

    template = load_template()
    prompts = {
        "search_agent": load_prompt("search_agent"),
        "card_agent": load_prompt("card_agent"),
        "fact_checker": load_prompt("fact_checker"),
        "tov_editor": load_prompt("tov_editor"),
        "article_agent": load_prompt("article_agent"),
        "social_agent": load_prompt("social_agent"),
    }
    tov = load_tov()

    out_dir = prepare_output_dir(brand, articul)
    print(f"[Оркестратор] Результаты будут сохранены в: {out_dir}")

    # Создаём черновик запроса для субагентов
    task_context = {
        "articul": articul,
        "brand": brand,
        "collection": collection,
        "condition": condition,
        "extra": extra,
        "template": template,
        "tov": tov,
    }

    save_json(out_dir, "task_context.json", task_context)
    save_md(out_dir, "prompts_for_agents.md", "\n\n".join([
        f"## {name}\n\n{text}" for name, text in prompts.items()
    ]))

    # В MVP результаты генерации контента пока не создаются автоматически —
    # это заготовка для ручного запуска субагентов через Claude Code.
    placeholder_card = {
        "articul": articul,
        "brand": brand,
        "collection": collection,
        "condition": condition,
        "name": f"{brand} {collection} {articul}".strip(),
    }
    placeholder_card.update(extra)

    save_json(out_dir, "card_draft.json", placeholder_card)

    print("[Оркестратор] Черновик карточки сохранён.")
    print("[Оркестратор] Следующий шаг: запустить search_agent для поиска характеристик.")
    print(f"[Оркестратор] Папка с результатами: {out_dir}\n")

    return out_dir


def run_batch(csv_path):
    """Запускает конвейер для пачки артикулов из CSV."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV-файл не найден: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[Оркестратор] Найдено артикулов: {len(rows)}")
    results = []
    for row in rows:
        out_dir = run_single(
            articul=row.get("articul", ""),
            brand=row.get("brand", ""),
            collection=row.get("collection", ""),
            condition=row.get("condition", "new"),
            extra=row,
        )
        results.append(out_dir)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Генератор контента для часов 316.watch"
    )
    parser.add_argument("--articul", help="Артикул часов")
    parser.add_argument("--brand", help="Бренд")
    parser.add_argument("--collection", default="", help="Коллекция")
    parser.add_argument("--condition", choices=["new", "pre-owned"], default="new",
                        help="Состояние: new или pre-owned")
    parser.add_argument("--input", dest="input_csv", help="Путь к CSV с артикулами")
    parser.add_argument("--warranty", default="", help="Гарантия")
    parser.add_argument("--price", default="", help="Цена")
    parser.add_argument("--bezel", default="", help="Безель (для б/у)")
    parser.add_argument("--accessories", default="", help="Комплектация (для б/у)")
    parser.add_argument("--bracelet-condition", default="", help="Состояние браслета/ремня (для б/у)")
    parser.add_argument("--case-condition", default="", help="Состояние корпуса (для б/у)")
    parser.add_argument("--glass-condition", default="", help="Состояние стекла (для б/у)")
    parser.add_argument("--movement-condition", default="", help="Техническое состояние механизма (для б/у)")

    args = parser.parse_args()

    if args.input_csv:
        run_batch(args.input_csv)
    elif args.articul and args.brand:
        extra = {
            "warranty": args.warranty,
            "price": args.price,
            "bezel": args.bezel,
            "accessories": args.accessories,
            "bracelet_strap_condition": args.bracelet_condition,
            "case_condition": args.case_condition,
            "glass_condition": args.glass_condition,
            "movement_condition": args.movement_condition,
        }
        run_single(
            articul=args.articul,
            brand=args.brand,
            collection=args.collection,
            condition="Новые" if args.condition == "new" else "С пробегом",
            extra={k: v for k, v in extra.items() if v},
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
