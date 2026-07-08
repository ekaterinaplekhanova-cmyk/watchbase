import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from caliber_reference import lookup_caliber_specs
from image_search import collect_image_context
from ollama_client import call_ollama, extract_json
from search import find_official_page, search_caliber_specs, search_watchbase, search_watchbase_model


PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PERF_LOG_PATH = PROJECT_ROOT / "output" / "perf.log"
CARD_CACHE_PATH = PROJECT_ROOT / "output" / "card_cache.json"
CARD_CACHE_TTL_SECONDS = 24 * 60 * 60  # сутки

_card_cache = {}


def _load_card_cache():
    global _card_cache
    if _card_cache:
        return _card_cache
    if CARD_CACHE_PATH.exists():
        try:
            with open(CARD_CACHE_PATH, "r", encoding="utf-8") as f:
                _card_cache = json.load(f)
            if not isinstance(_card_cache, dict):
                _card_cache = {}
        except Exception:
            _card_cache = {}
    else:
        _card_cache = {}
    return _card_cache


def _save_card_cache():
    try:
        CARD_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CARD_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_card_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _card_cache_key(articul, brand):
    return f"{str(brand).strip().lower()}:{str(articul).strip().upper()}"


def get_cached_package(articul, brand):
    cache = _load_card_cache()
    entry = cache.get(_card_cache_key(articul, brand))
    if not entry or not entry.get("card"):
        return None
    ts = entry.get("timestamp", 0)
    if time.time() - ts > CARD_CACHE_TTL_SECONDS:
        return None
    return entry


def set_cached_package(articul, brand, card, description_model="", telegram_post=""):
    cache = _load_card_cache()
    cache[_card_cache_key(articul, brand)] = {
        "timestamp": time.time(),
        "card": card,
        "description_model": description_model,
        "telegram_post": telegram_post,
    }
    _save_card_cache()


def _log_stage(articul, stage, seconds):
    try:
        PERF_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        with open(PERF_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | {articul} | {stage}: {seconds:.2f}s\n")
    except Exception:
        pass


def _clean_numeric(value, unit):
    """Приводит числовое значение к единому виду: число + единица измерения."""
    if not value or value in ("не найдено", "не указано"):
        return "не найдено"
    value = str(value).strip().lower()
    # Удаляем повторяющиеся пробелы и лишние слова
    value = re.sub(r"\s+", " ", value)
    # Ищем число с возможной десятичной точкой
    match = re.search(r"(\d+(?:[.,]\d+)?)", value)
    if not match:
        return "не найдено"
    number = match.group(1).replace(",", ".")
    return f"{number} {unit}"


def generate_characteristics(articul, brand, page_text, skip_watchbase=False):
    prompt = f"""Ты — эксперт по премиальным швейцарским часам и контент-редактор для магазина 316.watch. На основе текста официальной страницы заполни JSON-карточку товара.

Артикул: {articul}
Бренд: {brand}

Текст страницы (английский):
---
{page_text[:3500]}
---

КРИТИЧЕСКИ ВАЖНО: перед заполнением убедись, что текст страницы действительно относится к бренду {brand} и артикулу {articul}. Если в тексте явно упоминается другой бренд или другая модель (например, текст про Audemars Piguet, а запрошен Blancpain), заполни только поля "articul" и "brand" правильными значениями, а все остальные поля оставь "не найдено". НЕ используй характеристики чужой модели.

ВАЖНО: если в тексте рядом с метками (Calibre, Jewels, Frequency, Water Resistance, Diameter, Power Reserve и т.п.) есть числовые значения — обязательно используй их. Например, строки:
- "Water Resistance" без числа означают "не найдено".
- "Jewels" "26" означают "26".
- "Frequency" "28800 vph" означают "28 800 кол./час".
- "Reserve" "42 hours" означают "42 часа".
- "Diameter" "41 mm" означают "41 мм".

КРИТИЧЕСКИ ВАЖНО — не путай числа:
- Цена, артикул, год или номер коллекции НЕ являются запасом хода, частотой или водозащитой.
- Если рядом с меткой "Power Reserve" / "Reserve" нет явного числа часов — напиши "не найдено", даже если в тексте есть другие числа.
- Механические часы с автоподзаводом редко имеют запас хода менее 30 часов. Если получилось меньше 10 часов — это ошибка, пиши "не найдено".

Заполни следующие поля строго по правилам ниже. Если данных нет — напиши "не найдено". Пиши только JSON, без пояснений, без markdown, без комментариев.

ПРАВИЛА ЗАПОЛНЕНИЯ:
1. Язык: только русский. Переводи все материалы и термины с английского. Не оставляй английские слова в значениях.
2. name: "Бренд + Коллекция + Артикул" (например: "Tudor Monarch M2639W1A0U-0001").
3. mechanism: только "Механический" или "Кварцевый".
4. jewels: только целое число камней в механизме. Ищи рядом с меткой "Jewels" или "jewels" (например, строка "Jewels" сразу перед числом). Это технический параметр механизма, НЕ количество бриллиантов или декоративных камней. Если не указано — "не найдено".
5. power_reserve: число + "час"/"часа"/"часов". Ищи "power reserve". Пример: "42 часа", "65 часов", "40 часов".
6. frequency: только число + "кол./час", без слова "полуколебания". Ищи "frequency", "vph", "28,800", "4 Hz". Для 28 800 vph пиши строго "28 800 кол./час".
6a. caliber: только номер/название калибра, без слова "Calibre" в начале. Например: "1847 MC", "MT5662-2U", "3135". Если в тексте "Calibre 1847 MC" — пиши "1847 MC".
7. auto_winding: только один из вариантов: "да двунаправленный", "да однонаправленный", "нет", "не найдено".
8. additional_functions: массив строк. Только реальные функции часов: дата, хронограф, GMT, второй часовой пояс, тахиметр, люминесцентные метки, мировое время и т.п. НЕ включай отделку механизма (Côtes de Genève, perlage, золотой ротор, прозрачную заднюю крышку), сертификацию METAS/COSC, гарантию. "Chronometer" — это сертификация точности, НЕ функция; "Chronograph" / "хронограф" / "секундомер" — добавляй ТОЛЬКО если в исходном тексте явно есть слово chronograph/chronometer? Нет, chronometer — сертификация, не добавляй. "Seconds / Minutes / Watch" — это базовые указания времени, НЕ дополнительные функции. Если функций нет — пустой массив [].
9. case_material: переводи материалы корпуса на русский. "Stainless steel" всегда "сталь". Пример: "сталь", "сталь с PVD-покрытием", "титан", "золото 18 карат".
10. bracelet_strap_material: переводи материал браслета/ремня на русский. "Leather strap" или "leather" — это "кожаный ремень". Пример: "стальной браслет", "кожаный ремень", "каучуковый ремень".
11. glass: переводи. Пример: "сапфировое стекло", "минеральное стекло".
12. dial_color: только основной цвет циферблата на русском. "Silver" — "серебристый". Пример: "тёмно-шампаневый", "чёрный", "синий", "серебристый".
13. water_resistance: только метры. Пример: "100 м".
14. diameter: число + "мм".
15. thickness: число + "мм". Может быть с запятой или без.
16. country: страна производства на русском.
17. description: 10–20 предложений, художественный но информативный тон, соответствующий премиальному сегменту. Используй SEO-ключи (бренд, модель, механизм, материалы). Без упоминания состояния, комплектации и цены. Без пафоса, маркетинговых клише и слов "идеальный выбор", "отличный выбор", "уникальный", "невероятный". НЕ придумывай историю модели или бренда, если её нет в тексте страницы. "Bidirectional rotor" — это двунаправленный ротор автоподзавода, а не балансир. Frequency пиши как "полуколебания 28 800 кол./час", а не "частоту колебаний 28 800 колебаний в час". Используй глаголы точно: циферблат "оформлен", "украшен", "снабжён" метками, но не "применяет" метки.
18. source_url: оставь пустой строкой "".

Формат ответа — строго JSON:
{{
  "articul": "{articul}",
  "brand": "{brand}",
  "name": "",
  "collection": "",
  "mechanism": "",
  "caliber": "",
  "jewels": "",
  "power_reserve": "",
  "frequency": "",
  "auto_winding": "",
  "additional_functions": [],
  "case_material": "",
  "bracelet_strap_material": "",
  "glass": "",
  "dial_color": "",
  "water_resistance": "",
  "diameter": "",
  "thickness": "",
  "country": "",
  "description": "",
  "source_url": ""
}}
"""
    # Перед генерацией подмешиваем данные watchbase по модели, чтобы LLM сразу
    # видел правильный калибр и не выдумывал его из исходного текста.
    # Это дешёвый источник, поэтому делаем даже в режиме "только карточка".
    model_text = search_watchbase_model(brand, articul)
    if model_text:
        page_text = page_text + "\n\n[Дополнительный технический контекст из базы данных часов]\n" + model_text[:1500]

    response = call_ollama(prompt, temperature=0.2, max_tokens=1500)
    json_str = extract_json(response)
    try:
        card = json.loads(json_str)
    except Exception:
        return {
            "articul": articul,
            "brand": brand,
            "name": f"{brand} {articul}",
            "error": "Не удалось распарсить JSON",
            "raw_response": response,
        }

    # Sanity-check: запас хода меньше 10 часов для механического механизма — явная ошибка
    # (скорее всего LLM перепутала цену или артикул с часами). Механические часы обычно имеют
    # от 38 до 120 часов запаса хода, кварцевые — годы.
    pr = str(card.get("power_reserve", "")).strip().lower()
    mechanism = str(card.get("mechanism", "")).strip().lower()
    match = re.search(r"(\d+)", pr)
    if match and mechanism in ("механический", "mechanical"):
        hours = int(match.group(1))
        if 1 < hours < 10:
            card["power_reserve"] = "не найдено"

    # Дополняем/проверяем калибр и пустые поля данными с watchbase.com по модели.
    if model_text:
        card = _merge_watchbase_data(card, model_text)
    caliber = card.get("caliber") or ""
    if caliber and caliber != "не найдено":
        missing_caliber_fields = any(
            not card.get(field) or str(card.get(field)).strip().lower() in ("", "не найдено", "не указано")
            for field in ("jewels", "frequency", "power_reserve")
        )
        if missing_caliber_fields:
            if not skip_watchbase:
                caliber_text = search_watchbase(caliber, brand=brand)
                if not caliber_text:
                    caliber_text = search_caliber_specs(caliber, brand=brand)
                if caliber_text:
                    card = _merge_watchbase_data(card, caliber_text)
            # Если watchbase/calibercorner не дали характеристик — заполняем из справочника.
            still_missing = [
                field
                for field in ("jewels", "frequency", "power_reserve")
                if not card.get(field) or str(card.get(field)).strip().lower() in ("", "не найдено", "не указано")
            ]
            if still_missing:
                ref = lookup_caliber_specs(caliber)
                if ref:
                    for field in still_missing:
                        card[field] = ref[field]
                    card["reference_supplemented"] = still_missing

    # Нормализуем числовые поля
    card["diameter"] = _clean_numeric(card.get("diameter", ""), "мм")
    card["thickness"] = _clean_numeric(card.get("thickness", ""), "мм")
    card["water_resistance"] = _clean_numeric(card.get("water_resistance", ""), "м")

    # Если водозащита осталась неопределённой, но есть watchbase по модели — берём оттуда.
    wr = str(card.get("water_resistance", "")).strip().lower()
    if (not wr or wr in ("не найдено", "не указано", "да", "yes")) and model_text:
        match = re.search(r"Water Resistance[\s:]*([0-9]+)\s*m", model_text, re.IGNORECASE)
        if not match:
            match = re.search(r"([0-9]+)\s*metres?\s*water resistance", model_text, re.IGNORECASE)
        if not match:
            match = re.search(r"W/R\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*m", model_text, re.IGNORECASE)
        if match:
            card["water_resistance"] = f"{match.group(1)} м"

    # Приводим описание в карточке к чистому виду
    if "description" in card:
        card["description"] = _sanitize_russian_text(card["description"])
        # Убираем из описания выдуманные технические факты, если в карточке они не найдены.
        card["description"] = _strip_unverified_tech_claims(card["description"], card)
        # Если LLM в описании выдумал калибр или другие факты — корректируем по карточке.
        if _description_needs_fact_check(card):
            card["description"] = _tov_fact_check(card["description"], card)

    # Очищаем additional_functions от базовых указаний времени и конструктивных деталей
    functions = card.get("additional_functions", [])
    if isinstance(functions, list):
        forbidden = {
            "часы", "минуты", "секунды", "малые секунды", "small seconds", "стрелки", "часовые метки",
            "chronometer", "хронометр", "сертифицированный хронометр",
            "прозрачная задняя крышка", "transparent case back", "скелетон", "skeleton",
        }
        card["additional_functions"] = [
            f for f in functions
            if f and str(f).strip().lower() not in forbidden
        ]

    # Нормализуем поля, где модель может вернуть список или пустую строку
    bracelet = card.get("bracelet_strap_material", "")
    if isinstance(bracelet, list):
        card["bracelet_strap_material"] = " / ".join(str(b).strip() for b in bracelet if b)

    for field in ("caliber", "country", "glass", "dial_color", "frequency", "power_reserve"):
        value = card.get(field)
        if value is None or str(value).strip() == "":
            card[field] = "не найдено"

    # Для Cartier страна производства по умолчанию — Швейцария
    if str(card.get("brand", "")).strip().lower() == "cartier" and card.get("country") == "не найдено":
        card["country"] = "Швейцария"

    # Для известных швейцарских брендов, если страна не найдена — ставим Швейцарию.
    swiss_brands = {
        "rolex", "omega", "breitling", "tudor", "tag heuer", "iwc", "zenith", "panerai",
        "longines", "rado", "hamilton", "mido", "certina", "tissot", "oris", "baume & mercier",
        "bell & ross", "frederique constant", "maurice lacroix", "ulysse nardin", "franck muller",
        "roger dubuis", "parmigiani", "de grisogono", "graham", "vacheron constantin",
        "patek philippe", "audemars piguet", "jaeger-lecoultre", "blancpain", "breguet",
        "h. moser & cie.", "richard mille", "chopard", "bvlgari", "hublot", "grand seiko",
        "alpina", "union glashutte", "union glashütte", "steinhart", "nomos", "sinn",
    }
    if str(card.get("brand", "")).strip().lower() in swiss_brands and card.get("country") == "не найдено":
        card["country"] = "Швейцария"

    return card


def _strip_unverified_tech_claims(text, card):
    """Удаляет из описания технические утверждения, если соответствующие поля не заполнены."""
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    filtered = []
    pr = str(card.get("power_reserve", "")).strip().lower()
    freq = str(card.get("frequency", "")).strip().lower()
    caliber = str(card.get("caliber", "")).strip().lower()
    pr_hours = None
    pr_match = re.search(r"(\d+)", pr)
    if pr_match:
        pr_hours = int(pr_match.group(1))

    for sentence in sentences:
        s_lower = sentence.lower()
        # Если запас хода не найден — убираем предложения с подозрительно коротким запасом хода.
        if pr in ("", "не найдено", "не указано"):
            if re.search(r"запас[а-я]*\s+ход[а-я]*\s+(\d+|не найдено)", s_lower):
                continue
            # Убираем "7 часов" / "8 часов" и т.п. в техническом контексте.
            if re.search(r"\b\d{1,2}\s+час(а|ов)\b", s_lower) and ("время" in s_lower or "работ" in s_lower or "подзаряд" in s_lower):
                continue
        else:
            # Если запас хода известен — убираем утверждения с явно другим числом часов.
            s_hours_match = re.search(r"\b(\d{1,3})\s+час(а|ов)\b", s_lower)
            if s_hours_match:
                s_hours = int(s_hours_match.group(1))
                is_pr_context = (
                    "запас" in s_lower
                    or "время" in s_lower
                    or "работ" in s_lower
                    or "подзаряд" in s_lower
                    or "hod" in s_lower
                )
                if is_pr_context and s_hours != pr_hours:
                    continue
        # Если частота не найдена — убираем упоминания полуколебаний.
        if freq in ("", "не найдено", "не указано") and "кол./час" in s_lower:
            continue
        # Если калибр не найден — убираем предложения с конкретным номером калибра.
        if caliber in ("", "не найдено", "не указано"):
            # убираем предложения с похожими на калибр обозначениями (B01, MT5652, 1847 MC)
            if re.search(r"\b([A-Z]{1,3}\d{2,4}[A-Z0-9\.]*)\b", sentence):
                continue
        filtered.append(sentence)
    return " ".join(filtered).strip()


def _sanitize_russian_text(text):
    """Исправляет частые ошибки генерации: латинские буквы в русских словах, лишние пробелы, маркетинговые клише."""
    if not text:
        return text

    # Замена латинских букв, которые часто появляются внутри русских слов
    replacements = {
        "сапфiровое": "сапфировое",
        "сапфiroвое": "сапфировое",
        "сапфiровый": "сапфировый",
        "сапфiroвый": "сапфировый",
        "стальnой": "стальной",
        "браслетTUDOR": "браслет TUDOR",
        "TUDOR \"T-fit\"": "застёжка TUDOR T-fit",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Удаляем типичные маркетинговые клише (с учётом склонений)
    clichés = [
        "идеальный выбор",
        "идеальным выбором",
        "идеальном выборе",
        "идеально",
        "идеальное",
        "отличный выбор",
        "отличным выбором",
        "отличном выборе",
        "отличный",
        "отличная",
        "практичный выбор",
        "практичным выбором",
        "привлекательный выбор",
        "привлекательным выбором",
        "не упустите шанс",
        "спешите купить",
        "шедевр",
        "шедевра",
        "шедевром",
        "уникальный",
        "уникальным",
        "уникальная",
        "уникальное",
        "невероятный",
        "невероятным",
        "невероятная",
        "невероятное",
        "эксклюзивный",
        "эксклюзивным",
        "эксклюзивная",
        "эксклюзивное",
        "новинка",
        "новинку",
        "новинкой",
        "новая модель",
        "новой моделью",
        "новую модель",
        "появился",
        "появилась",
        "появились",
        "активный образ жизни",
        "активным образом жизни",
        "универсальный аксессуар",
        "универсальным аксессуаром",
        "в любых условиях",
        "водные процедуры",
        "неповторимый",
        "неповторимую",
        "неповторимое",
        "временепространственное устройство",
    ]
    for cliché in clichés:
        text = re.sub(re.escape(cliché), "", text, flags=re.IGNORECASE)

    # Убираем двойные пробелы и висящие знаки препинания
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" —\s*[.!?]*\s*$", ".", text, flags=re.MULTILINE)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text.strip()


def _tov_fact_check(text, card):
    """Проверяет и исправляет текст на соответствие фактам из карточки и ToV 316.watch."""
    if not text:
        return text

    has_chronograph = isinstance(card.get("additional_functions"), list) and "хронограф" in [
        f.lower() for f in card.get("additional_functions", [])
    ]

    prompt = f"""Ты — редактор фактов и стиля для премиального часового магазина 316.watch. Проверь текст ниже по критериям и исправь только ошибки. Верни исправленный текст, без пояснений, без markdown.

Критерии:
1. Если в тексте написано "хронограф", а в списке дополнительных функций нет хронографа — замени на корректное описание (сертифицированный хронометр / механизм). "Chronometer" — это сертификация, а не функция часов.
2. Не должно быть выдуманной истории модели: "вековая история", "исторический", "одна из последних разработок", "новая разработка", "новая модель", "мужчины и женщины".
3. Не должно быть маркетинговых клише: "идеальный выбор", "отличный выбор", "практичный выбор", "привлекательный выбор", "шедевр", "уникальный", "невероятный", "эксклюзивный", "новинка", "новая модель", "появился", "появилась", "активный образ жизни", "водные процедуры", "в любых условиях", "универсальный аксессуар".
4. Материалы и цвет циферблата должны соответствовать карточке: корпус — {card.get('case_material')}, браслет — {card.get('bracelet_strap_material')}, стекло — {card.get('glass')}, циферблат — {card.get('dial_color')}.
5. Технические параметры: калибр {card.get('caliber')}, камни {card.get('jewels')}, запас хода {card.get('power_reserve')}, полуколебания {card.get('frequency')}, автоподзавод {card.get('auto_winding')}, водозащита {card.get('water_resistance')}, диаметр {card.get('diameter')}, толщина {card.get('thickness')}.
6. Исправь латинские буквы внутри русских слов (например, "сапфiroвое" → "сапфировое").
7. Убедись, что текст заканчивается завершённым предложением.
8. Используй глаголы точно: циферблат "оформлен" или "украшен" метками, но не "применяет" метки.
9. Не используй слово "сертифицированный" по отношению к механизму, если в характеристиках нет явного указания на сертификацию хронометра (COSC, METAS). Для кварцевых механизмов пиши просто "кварцевый механизм", без "сертифицированный".

Хронограф в дополнительных функциях: {"да" if has_chronograph else "нет"}

Текст для проверки:
---
{text}
---

Исправленный текст:
"""
    checked = call_ollama(prompt, temperature=0.2, max_tokens=3000)
    return _sanitize_russian_text(checked)


def _extract_caliber_from_text(text):
    """Пытается найти номер калибра в тексте watchbase/calibercorner."""
    if not text:
        return ""
    # Ищем слова Caliber/Calibre/Movement + номер; точка в номере (L888.2) — допустима.
    # Два варианта: явная конструкция "Breitling caliber Caliber B20" и обычная "Calibre B20".
    patterns = [
        r"Breitling\s+(?:caliber|calibre)\s+(?:Caliber|Calibre)\s+([A-Z0-9.\-]+(?:\s+[A-Z0-9]+)?)",
        r"Breitling\s+(?:caliber|calibre)\s+([A-Z0-9.\-]+(?:\s+[A-Z0-9]+)?)",
        r"(?:Caliber|Calibre)\s+([A-Z0-9.\-]+(?:\s+[A-Z0-9]+)?)",
        r"(?: caliber| calibre)\s+([A-Z0-9.\-]+(?:\s+[A-Z0-9]+)?)",
        r"Movement\s*[:\-]?\s*([A-Z0-9.\-]+(?:\s+[A-Z0-9]+)?)",
    ]
    stop_words = {"caliber", "calibre", "movement", "model", "automatic", "mechanical", "quartz"}
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidate = match.group(1).strip().split()[0]
            if candidate.lower() not in stop_words:
                return candidate
    return ""


def _extract_jewels_from_text(text):
    """Извлекает количество камней из watchbase/calibercorner текста."""
    if not text:
        return ""
    match = re.search(r"Jewels?\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(\d+)\s*Jewels?", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _extract_frequency_from_text(text):
    """Извлекает частоту (vph) и переводит в 'X кол./час'."""
    if not text:
        return ""
    match = re.search(r"(\d{4,5})\s*vph", text, re.IGNORECASE)
    if match:
        vph = int(match.group(1))
        return f"{vph:,d} кол./час".replace(",", " ")
    match = re.search(r"Frequency\s*[:\-]?\s*(\d{4,5})", text, re.IGNORECASE)
    if match:
        vph = int(match.group(1))
        return f"{vph:,d} кол./час".replace(",", " ")
    return ""


def _extract_power_reserve_from_text(text):
    """Извлекает запас хода в часах."""
    if not text:
        return ""
    match = re.search(r"Power\s*Reserve\s*[:\-]?\s*(\d+)\s*h", text, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        return f"{hours} часов" if hours != 1 else "1 час"
    match = re.search(r"(\d+)\s*h\s*Power\s*Reserve", text, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        return f"{hours} часов" if hours != 1 else "1 час"
    return ""


def _description_needs_fact_check(card):
    """Определяет, противоречит ли описание фактам из карточки."""
    desc = card.get("description", "")
    if not desc:
        return False
    caliber = str(card.get("caliber", "")).strip().upper()
    if caliber and caliber != "не найдено":
        for match in re.finditer(r"\b([A-Z]{1,3}\d{2,4}(?:\.\d+)?)\b", desc, re.IGNORECASE):
            if match.group(1).upper() != caliber:
                return True
    return False


def _merge_watchbase_data(card, watchbase_text):
    """Дополняет карточку данными с watchbase.com по калибру без лишнего LLM-вызова.

    Если watchbase указывает другой калибр, чем LLM — доверяем watchbase,
    потому что LLM часто выдумывает номер, когда его нет в исходном тексте.
    """
    wb_caliber = _extract_caliber_from_text(watchbase_text)
    llm_caliber = str(card.get("caliber", "")).strip()
    if wb_caliber:
        if not llm_caliber or llm_caliber.lower() in ("не найдено", "не указано", ""):
            # LLM не смог определить калибр — берём из watchbase
            card["caliber"] = wb_caliber
        elif wb_caliber.upper() != llm_caliber.upper():
            # Если LLM выдумал калибр, а watchbase даёт другой — берём watchbase
            if "L" in wb_caliber.upper() and "L" in llm_caliber.upper():
                card["caliber"] = wb_caliber

    updates = {
        "jewels": _extract_jewels_from_text(watchbase_text),
        "frequency": _extract_frequency_from_text(watchbase_text),
        "power_reserve": _extract_power_reserve_from_text(watchbase_text),
    }
    for key, value in updates.items():
        if not value:
            continue
        current = card.get(key, "")
        if not current or str(current).strip().lower() in ("", "не найдено", "не указано"):
            card[key] = value
    return card


def generate_model_description(card):
    pr = str(card.get('power_reserve', '')).strip().lower()
    freq = str(card.get('frequency', '')).strip().lower()
    pr_hint = ""
    if pr in ("", "не найдено", "не указано"):
        pr_hint = "Запас хода неизвестен — НЕ упоминай его в описании."
    if freq in ("", "не найдено", "не указано"):
        pr_hint += " Полуколебания неизвестны — НЕ упоминай частоту механизма."
    prompt = f"""Напиши художественное описание модели для премиального интернет-магазина часов 316.watch. 7–10 предложений.

Тон: как у частного часового бутика и коллекционера-энтузиаста, который хорошо разбирается в механизмах. Спокойный, уважительный, информативный. Без пафоса и маркетинговых клише. НЕ используй слова: "уникальный", "невероятный", "эксклюзивный", "идеальный выбор", "отличный выбор", "шедевр", "новинка", "активный образ жизни", "универсальный аксессуар", "в любых условиях", "для него и для неё".

Опирайся только на факты из характеристик. Не выдумывай историю модели, год выпуска или сравнения с конкурентами. {pr_hint}

Бренд: {card.get('brand')}
Модель: {card.get('name')}
Коллекция: {card.get('collection')}
Механизм: {card.get('mechanism')}
Калибр: {card.get('caliber')}
Камни: {card.get('jewels')}
Запас хода: {card.get('power_reserve')}
Полуколебания: {card.get('frequency')}
Автоподзавод: {card.get('auto_winding')}
Материал корпуса: {card.get('case_material')}
Материал браслета/ремня: {card.get('bracelet_strap_material')}
Стекло: {card.get('glass')}
Цвет циферблата: {card.get('dial_color')}
Диаметр: {card.get('diameter')}
Толщина: {card.get('thickness')}
Водозащита: {card.get('water_resistance')}
Страна: {card.get('country')}
Техническое описание из источника: {card.get('description', '')}

Описание модели:
"""
    text = _sanitize_russian_text(call_ollama(prompt, temperature=0.3, max_tokens=700))
    text = _strip_unverified_tech_claims(text, card)
    return _tov_fact_check(text, card)


# TODO: блог временно отключён по запросу пользователя.
def generate_blog_article(card):
    prompt = f"""Напиши SEO-статью для блога интернет-магазина премиальных часов 316.watch.

Заголовок H1: {card.get('name')}: обзор

Характеристики:
- Бренд: {card.get('brand')}
- Модель: {card.get('name')}
- Коллекция: {card.get('collection')}
- Механизм: {card.get('mechanism')}
- Калибр: {card.get('caliber')}
- Камни: {card.get('jewels')}
- Запас хода: {card.get('power_reserve')}
- Полуколебания: {card.get('frequency')}
- Автоподзавод: {card.get('auto_winding')}
- Дополнительные функции: {', '.join(card.get('additional_functions', [])) if isinstance(card.get('additional_functions'), list) else card.get('additional_functions', '')}
- Материал корпуса: {card.get('case_material')}
- Материал браслета/ремня: {card.get('bracelet_strap_material')}
- Стекло: {card.get('glass')}
- Цвет циферблата: {card.get('dial_color')}
- Водозащита: {card.get('water_resistance')}
- Диаметр: {card.get('diameter')}
- Толщина: {card.get('thickness')}
- Страна: {card.get('country')}

Требования:
- Структура: H1, вводная (2 абзаца), 3 раздела с H2, вывод (1 абзац).
- Тон: экспертный, спокойный, респектабельный. Как у издания о премиальных часах.
- Не выдумывай факты, которых нет в характеристиках.
- НЕ пиши разделы "недостатки", "сравнение с конкурентами", "стоит ли покупать".
- НЕ называй часы хронографом, если в дополнительных функциях нет хронографа. "Chronometer" (сертифицированный хронометр) и "chronograph" (хронограф) — разные понятия.
- НЕ придумывай год выпуска коллекции или модели, историю бренда, если они не указаны в характеристиках.
- НЕ используй слова "идеальный выбор", "отличный выбор", "шедевр", "уникальный", "невероятный", "эксклюзивный", "активный образ жизни", "универсальный аксессуар".
- НЕ упоминай "мужчины и женщины", "для него и для неё", "для любого образа".
- Используй термины: "корпус", "браслет", "циферблат", "механизм", "автоподзавод", "водозащита". НЕ используй слово "стропа".
- Объём: 800–1200 слов.
- Без эмодзи, без маркетинговых клише.
- Заключение: 2–3 предложения. Скажи, что модель сочетает [два ключевых качества из характеристик] и может заинтересовать ценителей премиальных часов. НЕ заканчивай фразой "что делает её".
"""
    text = _sanitize_russian_text(call_ollama(prompt, temperature=0.3, max_tokens=2500))
    return _tov_fact_check(text, card)


def generate_telegram_post(card):
    prompt = f"""Напиши пост для Telegram-канала интернет-магазина премиальных часов 316.watch.

Модель: {card.get('name')}
Ключевые характеристики:
- Механизм: {card.get('mechanism')}
- Калибр: {card.get('caliber')}
- Камни: {card.get('jewels')}
- Запас хода: {card.get('power_reserve')}
- Полуколебания: {card.get('frequency')}
- Автоподзавод: {card.get('auto_winding')}
- Материал корпуса: {card.get('case_material')}
- Материал браслета/ремня: {card.get('bracelet_strap_material')}
- Стекло: {card.get('glass')}
- Цвет циферблата: {card.get('dial_color')}
- Диаметр: {card.get('diameter')}
- Толщина: {card.get('thickness')}
- Водозащита: {card.get('water_resistance')}
- Страна: {card.get('country')}

Требования:
- 3–4 коротких абзаца.
- Начни просто: назови часы или модель. Пример: "Tudor Monarch M2639W1A0U-0001 — часы с механическим механизмом..." НЕ используй синонимы вроде "временепространственное устройство".
- Тон спокойный, премиальный, информативный. Без пафоса.
- НЕ используй эмодзи.
- НЕ используй markdown: никаких звёздочек, жирного шрифта, заголовков.
- НЕ пиши "новинка", "появилась", "не упустите шанс", "спешите купить", "шедевр", "идеальный выбор", "отличный выбор", "уникальный", "невероятный", "эксклюзивный", "неповторимый", "активный образ жизни".
- НЕ пиши "в любых условиях", "под любой наряд", "для самых требовательных", "универсальный аксессуар".
- В конце хэштег #316[бренд в нижнем регистре].
- Можно добавить короткий призыв узнать цену или задать вопрос, без агрессивных продаж.
"""
    text = _sanitize_russian_text(call_ollama(prompt, temperature=0.3, max_tokens=500))
    return text


def _has_meaningful_data(card):
    """Проверяет, что карточка содержит минимум заполненных технических полей."""
    key_fields = [
        "mechanism",
        "caliber",
        "case_material",
        "bracelet_strap_material",
        "dial_color",
        "water_resistance",
        "diameter",
    ]
    filled = 0
    for field in key_fields:
        value = card.get(field)
        if value and str(value).strip().lower() not in ("", "не найдено", "не указано"):
            filled += 1
    return filled >= 3


def _source_tier_label(tier):
    """Преобразует числовой tier в человекочитаемую метку."""
    try:
        tier_int = int(tier)
    except (TypeError, ValueError):
        return "blocked"
    if tier_int == 1:
        return "official"
    if tier_int == 2:
        return "authorized"
    if tier_int == 3:
        return "reputable"
    if tier_int == 4:
        return "unknown"
    return "blocked"


def generate_texts_from_card(card):
    """По готовой карточке догенерирует описание модели и Telegram-пост параллельно."""
    total_start = time.time()
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def run(fn, label):
        start = time.time()
        try:
            out = fn(card)
        except Exception as e:
            out = f"[Ошибка генерации {label}: {e}]"
        _log_stage(card.get("articul", ""), label, time.time() - start)
        return label, out

    tasks = {
        "description_model": generate_model_description,
        "telegram_post": generate_telegram_post,
    }
    outputs = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(run, fn, label): label for label, fn in tasks.items()}
        for future in as_completed(futures):
            label, out = future.result()
            outputs[label] = out

    _log_stage(card.get("articul", ""), "texts_total", time.time() - total_start)
    return outputs


def generate_package(articul, brand, image_path=None, card_only=False):
    """Генерирует пакет контента.

    Если card_only=True — возвращает только карточку характеристик, пропуская
    SEO/блог/Telegram. Это в 3–4 раза быстрее.
    """
    articul_clean = str(articul).strip().upper()
    brand_clean = str(brand).strip()

    if not articul_clean or not brand_clean:
        return {
            "articul": articul_clean,
            "brand": brand_clean,
            "card": {"error": "Не указан артикул или бренд"},
            "description_model": "",
            "telegram_post": "",
            "source_url": "",
            "source_tier": None,
            "confidence_status": "manual_check_required",
        }

    total_start = time.time()

    # Если пакет уже в кэше — возвращаем сразу, не лезем в интернет и не зовём LLM.
    cached_package = get_cached_package(articul_clean, brand_clean)
    if cached_package:
        _log_stage(articul_clean, "cache_hit", 0)
        cached_card = cached_package["card"]
        result = {
            "articul": articul_clean,
            "brand": brand_clean,
            "card": cached_card,
            "description_model": "",
            "telegram_post": "",
            "source_url": cached_card.get("source_url", ""),
            "source_tier": cached_card.get("source_tier", ""),
            "confidence_status": cached_card.get("confidence_status", "partial"),
            "card_only": True,
        }
        if not card_only:
            # Если тексты тоже закэшированы — берём их, иначе генерируем.
            if cached_package.get("description_model") and cached_package.get("telegram_post"):
                result["description_model"] = cached_package["description_model"]
                result["telegram_post"] = cached_package["telegram_post"]
            else:
                texts = generate_texts_from_card(cached_card)
                result["description_model"] = texts.get("description_model", "")
                result["telegram_post"] = texts.get("telegram_post", "")
                set_cached_package(
                    articul_clean,
                    brand_clean,
                    cached_card,
                    result["description_model"],
                    result["telegram_post"],
                )
            result.pop("card_only", None)
        return result

    search_start = time.time()
    official_url, page_text, source_tier = find_official_page(articul_clean, brand_clean)
    _log_stage(articul_clean, "search", time.time() - search_start)

    # Если источник не найден и нет фото для поиска — не вызываем LLM,
    # чтобы не сгенерировать выдуманную карточку.
    has_text_source = bool(page_text) and not page_text.startswith("[Ошибка")
    if not has_text_source and not image_path:
        return {
            "articul": articul_clean,
            "brand": brand_clean,
            "card": {
                "articul": articul_clean,
                "brand": brand_clean,
                "name": f"{brand_clean} {articul_clean}",
            },
            "description_model": "",
            "telegram_post": "",
            "source_url": "",
            "source_tier": _source_tier_label(source_tier),
            "confidence_status": "manual_check_required",
            "note": "Источник характеристик не найден. Проверьте артикул/бренд или попробуйте загрузить фото.",
        }

    image_context = ""
    image_sources = []
    image_search_error = ""
    if image_path:
        img_start = time.time()
        try:
            image_pages = collect_image_context(image_path, max_pages=3)
            if image_pages and isinstance(image_pages[0], dict) and "error" in image_pages[0]:
                image_search_error = image_pages[0]["error"]
            else:
                for url, text, tier in image_pages:
                    image_sources.append({"url": url, "tier": _source_tier_label(tier)})
                    image_context += f"\n\n[Источник по изображению: {url}]\n{text[:2000]}"
        except Exception as e:
            image_search_error = str(e)
        _log_stage(articul_clean, "image_search", time.time() - img_start)

    if image_context:
        combined_text = page_text + "\n\n[Контекст из поиска по изображению]" + image_context
    else:
        combined_text = page_text

    card_start = time.time()
    card = generate_characteristics(articul_clean, brand_clean, combined_text, skip_watchbase=card_only)
    _log_stage(articul_clean, "card_llm", time.time() - card_start)

    if "error" not in card:
        card["source_url"] = official_url
        card["source_tier"] = _source_tier_label(source_tier)

    # Если источник плохой или LLM не заполнил ключевые поля — требуем ручную проверку.
    source_ok = has_text_source and _source_tier_label(source_tier) not in ("blocked", None, "")
    if not source_ok or not _has_meaningful_data(card):
        card["confidence_status"] = "manual_check_required"
        result = {
            "articul": articul_clean,
            "brand": brand_clean,
            "card": card,
            "description_model": "",
            "telegram_post": "",
            "source_url": official_url,
            "source_tier": _source_tier_label(source_tier),
            "confidence_status": "manual_check_required",
            "note": "Не удалось найти достоверные характеристики. Требуется ручная проверка.",
            "image_sources": image_sources,
        }
        if image_search_error:
            result["image_search_error"] = image_search_error
        _log_stage(articul_clean, "total", time.time() - total_start)
        return result

    card["confidence_status"] = "partial"

    if card_only:
        result = {
            "articul": articul_clean,
            "brand": brand_clean,
            "card": card,
            "description_model": "",
            "telegram_post": "",
            "source_url": official_url,
            "source_tier": _source_tier_label(source_tier),
            "confidence_status": "partial",
            "image_sources": image_sources,
            "card_only": True,
        }
        if image_search_error:
            result["image_search_error"] = image_search_error
        set_cached_package(articul_clean, brand_clean, card)
        _log_stage(articul_clean, "total", time.time() - total_start)
        return result

    texts = generate_texts_from_card(card)

    result = {
        "articul": articul_clean,
        "brand": brand_clean,
        "card": card,
        "description_model": texts.get("description_model", ""),
        "telegram_post": texts.get("telegram_post", ""),
        "source_url": official_url,
        "source_tier": _source_tier_label(source_tier),
        "confidence_status": "partial",
        "image_sources": image_sources,
    }
    if image_search_error:
        result["image_search_error"] = image_search_error
    set_cached_package(
        articul_clean,
        brand_clean,
        card,
        result["description_model"],
        result["telegram_post"],
    )
    _log_stage(articul_clean, "total", time.time() - total_start)
    return result
