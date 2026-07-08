"""Шаблоны URL официальных страниц для известных брендов."""

import re


BRAND_TEMPLATES = {
    "tudor": lambda brand, collection, articul: f"https://www.tudorwatch.com/en/watches/tudor-{collection.lower()}/{articul.lower()}",
    "rolex": lambda brand, collection, articul: f"https://www.rolex.com/watches/{collection.lower()}/{articul.lower()}.html",
    "omega": lambda brand, collection, articul: f"https://www.omegawatches.com/en-us/watch/{articul.lower()}",
    "tag heuer": lambda brand, collection, articul: f"https://www.tagheuer.com/us/en/watches/{collection.lower().replace(' ', '-')}/{articul.lower()}.html",
    "breitling": lambda brand, collection, articul: f"https://www.breitling.com/us-en/watches/{collection.lower().replace(' ', '-')}/{articul.lower()}/",
    "cartier": lambda brand, collection, articul: f"https://www.cartier.com/en-us/watches/watches/{collection.lower().replace(' ', '-')}/{articul.lower()}.html",
    "iwc": lambda brand, collection, articul: f"https://www.iwc.com/en/watch-collections/{collection.lower().replace(' ', '-')}/{articul.lower()}.html",
    "zenith": lambda brand, collection, articul: f"https://www.zenith-watches.com/en_us/product/{articul.lower()}",
}


def guess_collection(articul, brand):
    """Пытается угадать коллекцию по артикулу."""
    brand_lower = brand.lower()
    if brand_lower == "tudor":
        # Tudor: MXXXX — Monarch, Pelagos, Black Bay и т.д.
        if articul.upper().startswith("M"):
            return "monarch"  # default, будет уточняться поиском
    if brand_lower == "rolex":
        if articul.upper().startswith("116") or articul.upper().startswith("126"):
            return "submariner"
    return ""


def get_official_url(brand, articul, collection=""):
    """Возвращает предполагаемый официальный URL или None."""
    brand_lower = brand.lower()
    if brand_lower not in BRAND_TEMPLATES:
        return None
    if not collection:
        collection = guess_collection(articul, brand)
    return BRAND_TEMPLATES[brand_lower](brand, collection, articul)
