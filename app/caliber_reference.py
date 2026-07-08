"""Справочник проверенных характеристик распространённых часовых калибров.

Используется как fallback: если источник подтвердил конкретный калибр, а карточка
не содержит камней, частоты или запаса хода, подставляем данные из справочника.
Это позволяет не выдумывать параметры, а дополнять карточку проверенными фактами.
"""

CALIBER_REFERENCE = {
    # Breitling
    "B01": {"jewels": "41", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "B04": {"jewels": "47", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "B09": {"jewels": "39", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "B12": {"jewels": "47", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "B13": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B17": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B19": {"jewels": "38", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B20": {"jewels": "28", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "B25": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "48 часов"},
    "B35": {"jewels": "41", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "B40": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B44": {"jewels": "38", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B46": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B50": {"jewels": "22", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B55": {"jewels": "23", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B62": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B69": {"jewels": "26", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B71": {"jewels": "23", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B72": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B73": {"jewels": "22", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B74": {"jewels": "24", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B75": {"jewels": "22", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "B80": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B85": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B90": {"jewels": "22", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "B92": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "Caliber 10": {"jewels": "17", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "Caliber 11": {"jewels": "17", "frequency": "19 800 кол./час", "power_reserve": "42 часа"},
    "Caliber 12": {"jewels": "17", "frequency": "21 600 кол./час", "power_reserve": "42 часа"},
    "Caliber 13": {"jewels": "17", "frequency": "21 600 кол./час", "power_reserve": "42 часа"},
    "SuperQuartz": {"jewels": "8", "frequency": "не найдено", "power_reserve": "не найдено"},

    # Tudor
    "MT5400": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5402": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5412": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5601": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5602": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5612": {"jewels": "26", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5621": {"jewels": "26", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5652": {"jewels": "28", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5652-2U": {"jewels": "28", "frequency": "28 800 кол./час", "power_reserve": "65 часов"},
    "MT5602-1U": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5400-1U": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5402-1U": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5813": {"jewels": "41", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "MT5892": {"jewels": "28", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "T603": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "38 часов"},
    "T601": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "38 часов"},

    # Rolex
    "3186": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "50 часов"},
    "3187": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "50 часов"},
    "3230": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "3235": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "3255": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "3285": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "70 часов"},
    "3300": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "55 часов"},
    "3305": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "55 часов"},
    "4130": {"jewels": "44", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "4131": {"jewels": "44", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "4160": {"jewels": "42", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "4161": {"jewels": "42", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "9001": {"jewels": "40", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "2236": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "55 часов"},
    "2235": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "48 часов"},
    "3135": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "48 часов"},

    # Omega
    "2500": {"jewels": "27", "frequency": "25 200 кол./час", "power_reserve": "48 часов"},
    "2627": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "55 часов"},
    "3330": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "52 часа"},
    "3861": {"jewels": "26", "frequency": "21 600 кол./час", "power_reserve": "50 часов"},
    "8900": {"jewels": "39", "frequency": "25 200 кол./час", "power_reserve": "60 часов"},
    "8901": {"jewels": "39", "frequency": "25 200 кол./час", "power_reserve": "60 часов"},
    "8912": {"jewels": "38", "frequency": "25 200 кол./час", "power_reserve": "60 часов"},
    "8922": {"jewels": "38", "frequency": "25 200 кол./час", "power_reserve": "55 часов"},
    "8926": {"jewels": "39", "frequency": "25 200 кол./час", "power_reserve": "55 часов"},
    "8938": {"jewels": "38", "frequency": "25 200 кол./час", "power_reserve": "60 часов"},
    "8939": {"jewels": "38", "frequency": "25 200 кол./час", "power_reserve": "60 часов"},
    "9900": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9901": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9904": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9905": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9906": {"jewels": "44", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9907": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9908": {"jewels": "44", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9909": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9910": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9913": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "9914": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},

    # Tag Heuer
    "Calibre 5": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "38 часов"},
    "Calibre 7": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "Calibre 11": {"jewels": "59", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "Calibre 12": {"jewels": "59", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "Calibre 16": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "Calibre 17": {"jewels": "37", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "Heuer 02": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "80 часов"},
    "Heuer 02T": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "65 часов"},

    # IWC
    "32110": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "32111": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "120 часов"},
    "32115": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "120 часов"},
    "69355": {"jewels": "27", "frequency": "28 800 кол./час", "power_reserve": "46 часов"},
    "69370": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "46 часов"},
    "69375": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "46 часов"},
    "69380": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "46 часов"},
    "69385": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "46 часов"},
    "69800": {"jewels": "28", "frequency": "28 800 кол./час", "power_reserve": "40 часов"},
    "82760": {"jewels": "22", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "82650": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "82905": {"jewels": "42", "frequency": "28 800 кол./час", "power_reserve": "60 часов"},
    "52010": {"jewels": "32", "frequency": "28 800 кол./час", "power_reserve": "168 часов"},
    "52310": {"jewels": "32", "frequency": "28 800 кол./час", "power_reserve": "168 часов"},
    "52610": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "168 часов"},
    "52615": {"jewels": "54", "frequency": "28 800 кол./час", "power_reserve": "168 часов"},
    "59210": {"jewels": "30", "frequency": "28 800 кол./час", "power_reserve": "192 часа"},
    "59215": {"jewels": "32", "frequency": "28 800 кол./час", "power_reserve": "192 часа"},
    "59220": {"jewels": "35", "frequency": "28 800 кол./час", "power_reserve": "192 часа"},

    # Panerai
    "P.5000": {"jewels": "19", "frequency": "21 600 кол./час", "power_reserve": "96 часов"},
    "P.6000": {"jewels": "19", "frequency": "21 600 кол./час", "power_reserve": "72 часа"},
    "P.9010": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.9011": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.9012": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.9200": {"jewels": "41", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "P.9203": {"jewels": "41", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "P.4000": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.4001": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.4002": {"jewels": "31", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.4100": {"jewels": "28", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "P.3000": {"jewels": "21", "frequency": "21 600 кол./час", "power_reserve": "72 часа"},

    # Grand Seiko
    "9S64": {"jewels": "24", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "9S65": {"jewels": "35", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "9S66": {"jewels": "35", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "9S85": {"jewels": "37", "frequency": "36 000 кол./час", "power_reserve": "55 часов"},
    "9S86": {"jewels": "37", "frequency": "36 000 кол./час", "power_reserve": "55 часов"},
    "9S25": {"jewels": "33", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "9S63": {"jewels": "24", "frequency": "28 800 кол./час", "power_reserve": "72 часа"},
    "9SA5": {"jewels": "47", "frequency": "36 000 кол./час", "power_reserve": "80 часов"},
    "9SA4": {"jewels": "47", "frequency": "36 000 кол./час", "power_reserve": "80 часов"},
    "9RA2": {"jewels": "38", "frequency": "не найдено", "power_reserve": "120 часов"},
    "9RA5": {"jewels": "38", "frequency": "не найдено", "power_reserve": "120 часов"},
    "9F82": {"jewels": "не найдено", "frequency": "32 768 кол./час", "power_reserve": "не найдено"},
    "9F85": {"jewels": "не найдено", "frequency": "32 768 кол./час", "power_reserve": "не найдено"},
    "9R02": {"jewels": "39", "frequency": "не найдено", "power_reserve": "84 часа"},
    "9R31": {"jewels": "30", "frequency": "не найдено", "power_reserve": "72 часа"},
    "9R65": {"jewels": "30", "frequency": "не найдено", "power_reserve": "72 часа"},
    "9R66": {"jewels": "30", "frequency": "не найдено", "power_reserve": "72 часа"},
    "9R15": {"jewels": "30", "frequency": "не найдено", "power_reserve": "72 часа"},
    "9R96": {"jewels": "38", "frequency": "не найдено", "power_reserve": "72 часа"},
    "9R01": {"jewels": "56", "frequency": "не найдено", "power_reserve": "120 часов"},
    "9ST1": {"jewels": "44", "frequency": "28 800 кол./час", "power_reserve": "80 часов"},

    # Longines
    "L888.2": {"jewels": "21", "frequency": "25 200 кол./час", "power_reserve": "64 часа"},
    "L888.3": {"jewels": "21", "frequency": "25 200 кол./час", "power_reserve": "64 часа"},
    "L888.4": {"jewels": "21", "frequency": "25 200 кол./час", "power_reserve": "72 часа"},
    "L888.5": {"jewels": "21", "frequency": "25 200 кол./час", "power_reserve": "72 часа"},

    # ETA / Sellita (универсальные базовые калибры)
    "2824-2": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "38 часов"},
    "2892-A2": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "2893-2": {"jewels": "21", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "7750": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "SW200": {"jewels": "26", "frequency": "28 800 кол./час", "power_reserve": "38 часов"},
    "SW200-1": {"jewels": "26", "frequency": "28 800 кол./час", "power_reserve": "38 часов"},
    "SW300": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
    "SW500": {"jewels": "25", "frequency": "28 800 кол./час", "power_reserve": "42 часа"},
}


def normalize_caliber_name(name):
    """Приводит название калибра к ключу справочника.

    Убирает префиксы Calibre/Caliber/Movement, лишние пробелы и точки.
    Возвращает None, если нормализовать не удалось.
    """
    if not name or str(name).strip().lower() in ("не найдено", "не указано", "", "none"):
        return None
    normalized = str(name).strip()
    # Убираем префиксы
    for prefix in ("Calibre", "Caliber", "Movement", "Модель"):
        if normalized.lower().startswith(prefix.lower()):
            normalized = normalized[len(prefix):].strip()
    # Убираем точку на конце
    normalized = normalized.rstrip(".").strip()
    # Заменяем множественные пробелы на один
    normalized = " ".join(normalized.split())
    return normalized or None


def lookup_caliber_specs(caliber_name):
    """Ищет калибр в справочнике. Возвращает dict с jewels/frequency/power_reserve
    или None, если калибр неизвестен.
    """
    key = normalize_caliber_name(caliber_name)
    if not key:
        return None
    # Точное совпадение
    if key in CALIBER_REFERENCE:
        return dict(CALIBER_REFERENCE[key])
    # Регистронезависимое совпадение
    for ref_key, specs in CALIBER_REFERENCE.items():
        if ref_key.lower() == key.lower():
            return dict(specs)
    return None
