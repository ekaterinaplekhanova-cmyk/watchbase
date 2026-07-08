import json
import os
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"


def find_latest_card():
    """Находит самый свежий characteristics.json в output/."""
    candidates = list(OUTPUT_DIR.rglob("characteristics.json"))
    if not candidates:
        raise FileNotFoundError("Не найдено файлов characteristics.json в output/")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def card_to_excel_row(card):
    """Преобразует карточку товара в строку для Excel."""
    def format_functions(funcs):
        if not funcs:
            return ""
        if isinstance(funcs, list):
            return ", ".join(funcs)
        return str(funcs)

    return {
        "Артикул": card.get("articul", ""),
        "Название": card.get("name", ""),
        "Бренд": card.get("brand", ""),
        "Коллекция": card.get("collection", ""),
        "Состояние": card.get("condition", ""),
        "Сортировка": card.get("sorting", ""),
        "Механизм": card.get("mechanism", ""),
        "Калибр": card.get("caliber", ""),
        "Количество камней": card.get("jewels", ""),
        "Запас хода": card.get("power_reserve", ""),
        "Количество полуколебаний": card.get("frequency", ""),
        "Автоподзавод": card.get("auto_winding", ""),
        "Дополнительные функции": format_functions(card.get("additional_functions")),
        "Материал корпуса": card.get("case_material", ""),
        "Материал браслета/ремня": card.get("bracelet_strap_material", ""),
        "Стекло": card.get("glass", ""),
        "Цвет циферблата": card.get("dial_color", ""),
        "Водозащита": card.get("water_resistance", ""),
        "Диаметр": card.get("diameter", ""),
        "Толщина": card.get("thickness", ""),
        "Страна": card.get("country", ""),
        "Гарантия": card.get("warranty", ""),
        "Цена": card.get("price", ""),
        "Описание": card.get("description", ""),
        "Безель": card.get("bezel", ""),
        "Комплектация": card.get("accessories", ""),
        "Состояние браслета/ремня": card.get("bracelet_strap_condition", ""),
        "Состояние корпуса": card.get("case_condition", ""),
        "Состояние стекла": card.get("glass_condition", ""),
        "Техническое состояние механизма": card.get("movement_condition", ""),
        "SEO-заголовок": card.get("seo_title", ""),
        "SEO-описание": card.get("seo_description", ""),
        "Ключевые слова": card.get("meta_keywords", ""),
        "URL источника": card.get("source_url", ""),
        "URL источника по калибру": card.get("caliber_source_url", ""),
        "Статус проверки": card.get("confidence_status", ""),
    }


def card_to_csv_row(card):
    """Преобразует карточку товара в строку для CSV."""
    def format_functions(funcs):
        if not funcs:
            return ""
        if isinstance(funcs, list):
            return ", ".join(funcs)
        return str(funcs)

    return {
        "articul": card.get("articul", ""),
        "name": card.get("name", ""),
        "brand": card.get("brand", ""),
        "collection": card.get("collection", ""),
        "condition": card.get("condition", ""),
        "sorting": card.get("sorting", ""),
        "mechanism": card.get("mechanism", ""),
        "caliber": card.get("caliber", ""),
        "jewels": card.get("jewels", ""),
        "power_reserve": card.get("power_reserve", ""),
        "frequency": card.get("frequency", ""),
        "auto_winding": card.get("auto_winding", ""),
        "additional_functions": format_functions(card.get("additional_functions")),
        "case_material": card.get("case_material", ""),
        "bracelet_strap_material": card.get("bracelet_strap_material", ""),
        "glass": card.get("glass", ""),
        "dial_color": card.get("dial_color", ""),
        "water_resistance": card.get("water_resistance", ""),
        "diameter": card.get("diameter", ""),
        "thickness": card.get("thickness", ""),
        "country": card.get("country", ""),
        "warranty": card.get("warranty", ""),
        "price": card.get("price", ""),
        "description": card.get("description", ""),
        "bezel": card.get("bezel", ""),
        "accessories": card.get("accessories", ""),
        "bracelet_strap_condition": card.get("bracelet_strap_condition", ""),
        "case_condition": card.get("case_condition", ""),
        "glass_condition": card.get("glass_condition", ""),
        "movement_condition": card.get("movement_condition", ""),
        "seo_title": card.get("seo_title", ""),
        "seo_description": card.get("seo_description", ""),
        "meta_keywords": card.get("meta_keywords", ""),
        "source_url": card.get("source_url", ""),
        "caliber_source_url": card.get("caliber_source_url", ""),
        "confidence_status": card.get("confidence_status", ""),
    }


def main():
    card_path = find_latest_card()
    print(f"[Excel-экспорт] Найдена карточка: {card_path}")

    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    out_dir = card_path.parent

    # Excel с человекочитаемыми заголовками
    excel_path = out_dir / "card_import.xlsx"
    df = pd.DataFrame([card_to_excel_row(card)])
    df.to_excel(excel_path, index=False)
    print(f"[Excel-экспорт] Сохранён Excel: {excel_path}")

    # CSV с техническими полями
    csv_path = out_dir / "card_import.csv"
    df_csv = pd.DataFrame([card_to_csv_row(card)])
    df_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[Excel-экспорт] Сохранён CSV: {csv_path}")


if __name__ == "__main__":
    main()
