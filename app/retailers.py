"""Каталог ритейлеров, фильтры подлинности и resolver-функции.

Цель модуля — отделить оригинальные источники от подделок/маркетплейсов
и дать единую точку управления списком доверенных магазинов.
"""

import re
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# Уровни доверия источника. Чем ниже — тем надёжнее.
TIER_OFFICIAL = 1
TIER_AUTHORIZED = 2
TIER_REPUTABLE = 3
TIER_UNKNOWN = 4
TIER_BLOCKED = 0

# Официальные сайты брендов и авторизованные ритейлеры.
TRUSTED_DOMAINS = {
    # --- Официальные сайты брендов ---
    "tudorwatch.com": TIER_OFFICIAL,
    "rolex.com": TIER_OFFICIAL,
    "cartier.com": TIER_OFFICIAL,
    "omegawatches.com": TIER_OFFICIAL,
    "tagheuer.com": TIER_OFFICIAL,
    "breitling.com": TIER_OFFICIAL,
    "iwc.com": TIER_OFFICIAL,
    "zenith-watches.com": TIER_OFFICIAL,
    "traser.com": TIER_OFFICIAL,
    "union-glashuette.com": TIER_OFFICIAL,
    "unionglashuette.com": TIER_OFFICIAL,
    "luminox.com": TIER_OFFICIAL,
    "grand-seiko.com": TIER_OFFICIAL,
    "panerai.com": TIER_OFFICIAL,
    "longines.com": TIER_OFFICIAL,
    "bvlgari.com": TIER_OFFICIAL,
    "audemarspiguet.com": TIER_OFFICIAL,
    "patek.com": TIER_OFFICIAL,
    "patekphilippe.com": TIER_OFFICIAL,
    "vacheron-constantin.com": TIER_OFFICIAL,
    "jaeger-lecoultre.com": TIER_OFFICIAL,
    "blancpain.com": TIER_OFFICIAL,
    "breguet.com": TIER_OFFICIAL,
    "girard-perregaux.com": TIER_OFFICIAL,
    "hublot.com": TIER_OFFICIAL,
    "chopard.com": TIER_OFFICIAL,
    "piaget.com": TIER_OFFICIAL,
    "rado.com": TIER_OFFICIAL,
    "tissotwatches.com": TIER_OFFICIAL,
    "hamiltonwatch.com": TIER_OFFICIAL,
    "midowatches.com": TIER_OFFICIAL,
    "certina.com": TIER_OFFICIAL,
    "bulova.com": TIER_OFFICIAL,
    "citizenwatch.com": TIER_OFFICIAL,
    "seikowatches.com": TIER_OFFICIAL,
    "ballwatch.com": TIER_OFFICIAL,
    "bernhardhmayer.com": TIER_OFFICIAL,
    "baume-et-mercier.com": TIER_OFFICIAL,
    "bellross.com": TIER_OFFICIAL,
    "frederiqueconstant.com": TIER_OFFICIAL,
    "mauricelacroix.com": TIER_OFFICIAL,
    "eposwatches.com": TIER_OFFICIAL,
    "edox.ch": TIER_OFFICIAL,
    "ebel.com": TIER_OFFICIAL,
    "dior.com": TIER_OFFICIAL,
    "hermes.com": TIER_OFFICIAL,
    "louisvuitton.com": TIER_OFFICIAL,
    "montblanc.com": TIER_OFFICIAL,
    "oris.ch": TIER_OFFICIAL,
    "ulysse-nardin.com": TIER_OFFICIAL,
    "graham1695.com": TIER_OFFICIAL,
    "bovet.com": TIER_OFFICIAL,
    "jacobandco.com": TIER_OFFICIAL,
    "franckmuller.com": TIER_OFFICIAL,
    "rogerdubuis.com": TIER_OFFICIAL,
    "perrelet.com": TIER_OFFICIAL,
    "corum-watches.com": TIER_OFFICIAL,
    "corumwatch.jp": TIER_OFFICIAL,
    "parmigiani.com": TIER_OFFICIAL,
    "degrisogono.com": TIER_OFFICIAL,
    "clercwatches.com": TIER_OFFICIAL,
    "squale.ch": TIER_OFFICIAL,
    "steinhart-watches.com": TIER_OFFICIAL,
    "u-boat.it": TIER_OFFICIAL,
    "tsedro.com": TIER_OFFICIAL,
    "luxewood.com": TIER_OFFICIAL,
    "wgabus.com": TIER_OFFICIAL,
    "vanderbauwede.com": TIER_OFFICIAL,
    "romainjerome.ch": TIER_OFFICIAL,
    "schwarz-etienne.com": TIER_OFFICIAL,
    "jeanrichard.com": TIER_OFFICIAL,
    "juvenia.ch": TIER_OFFICIAL,
    "armandnicolet.com": TIER_OFFICIAL,
    "augustereymond.ch": TIER_OFFICIAL,
    "aerowatch.ch": TIER_OFFICIAL,
    "boegli.ch": TIER_OFFICIAL,
    "bomberg.com": TIER_OFFICIAL,
    "briller.com": TIER_OFFICIAL,
    "alainsilberstein.com": TIER_OFFICIAL,
    "charmex.ch": TIER_OFFICIAL,
    "icelink.com": TIER_OFFICIAL,
    "paulpicot.com": TIER_OFFICIAL,
    "rebellion-timepieces.com": TIER_OFFICIAL,
    "swatch.com": TIER_OFFICIAL,
    "alpina-watches.com": TIER_OFFICIAL,
    "alpinawatches.com": TIER_OFFICIAL,

    # --- Русскоязычные авторизованные/крупные ритейлеры ---
    "alltime.ru": TIER_AUTHORIZED,
    "watcheson.ru": TIER_AUTHORIZED,
    "bestwatch.ru": TIER_AUTHORIZED,
    "aswatch.ru": TIER_AUTHORIZED,
    "montre24.ru": TIER_AUTHORIZED,
    "shop-watches.ru": TIER_AUTHORIZED,
    "watches-shop.ru": TIER_AUTHORIZED,
    "316.watch": TIER_AUTHORIZED,
    "mercury.ru": TIER_AUTHORIZED,
    "n-watches.ru": TIER_AUTHORIZED,
    "watch.ru": TIER_AUTHORIZED,
    "timeshop.ru": TIER_AUTHORIZED,
    "chrono.ru": TIER_AUTHORIZED,
    "kronostime.ru": TIER_AUTHORIZED,
    "4-izmerenie.ru": TIER_AUTHORIZED,
    "2ti.ru": TIER_AUTHORIZED,

    # --- Глобальные авторизованные дилеры ---
    "the1916company.com": TIER_AUTHORIZED,
    "watches-of-switzerland.co.uk": TIER_AUTHORIZED,
    "watches-of-switzerland.com": TIER_AUTHORIZED,
    "watches-of-switzerland.com.au": TIER_AUTHORIZED,
    "caratco.com": TIER_AUTHORIZED,
    "mayors.com": TIER_AUTHORIZED,
    "crownandcaliber.com": TIER_AUTHORIZED,
    "thewatchbox.com": TIER_AUTHORIZED,
    "bucherer.com": TIER_AUTHORIZED,
    "tourneau.com": TIER_AUTHORIZED,
    "firstclasswatches.co.uk": TIER_AUTHORIZED,
    "jurawatches.co.uk": TIER_AUTHORIZED,
    "thbaker.co.uk": TIER_AUTHORIZED,
    "watchmaxx.com": TIER_AUTHORIZED,
    "ernestjones.co.uk": TIER_AUTHORIZED,
    "goldsmiths.co.uk": TIER_AUTHORIZED,
    "beaverbrooks.co.uk": TIER_AUTHORIZED,

    # --- Глобальные авторитетные площадки и обзорники ---
    "chrono24.com": TIER_REPUTABLE,
    "watchfinder.co.uk": TIER_REPUTABLE,
    "watchfinder.lu": TIER_REPUTABLE,
    "watchfinder.mt": TIER_REPUTABLE,
    "cortinawatch.com": TIER_REPUTABLE,
    "thewatchsource.co.uk": TIER_REPUTABLE,
    "uhren2000.de": TIER_REPUTABLE,
    "uhren-miquel.de": TIER_REPUTABLE,
    "carollinum.cz": TIER_REPUTABLE,
    "thewatchagency.com": TIER_REPUTABLE,
    "monochrome-watches.com": TIER_REPUTABLE,
    "hodinkee.com": TIER_REPUTABLE,
    "timeandtidewatches.com": TIER_REPUTABLE,
    "fratellowatches.com": TIER_REPUTABLE,
    "revolution.watch": TIER_REPUTABLE,
    "escapementmagazine.com": TIER_REPUTABLE,
    "ablogtowatch.com": TIER_REPUTABLE,
    "quillandpad.com": TIER_REPUTABLE,
    "thewatchcompany.com": TIER_REPUTABLE,
    "everywatch.com": TIER_REPUTABLE,
    "stablos.com": TIER_REPUTABLE,
    "12-24.com": TIER_REPUTABLE,
    "seriouswatches.com": TIER_REPUTABLE,
    "watches.ae": TIER_REPUTABLE,
    "lindajewellers.com": TIER_REPUTABLE,
    "thewatchpages.com": TIER_REPUTABLE,
    "watchbase.com": TIER_REPUTABLE,
    "watchthelegacy.com": TIER_REPUTABLE,
    "watchspecs.com": TIER_REPUTABLE,
    "chronomaster.co.uk": TIER_REPUTABLE,
    "zadwatch.com": TIER_REPUTABLE,
    "qbuzz.qnet.net": TIER_REPUTABLE,
    "qnet.hk": TIER_REPUTABLE,
    "chronext.de": TIER_REPUTABLE,
    "gioielleriatamburini.it": TIER_REPUTABLE,
    "monarchjewels.com": TIER_REPUTABLE,
    "timeonly.com": TIER_REPUTABLE,
    "brandizzi.com": TIER_REPUTABLE,
    "watchesandcrystals.com": TIER_REPUTABLE,
    "watches-swiss.com": TIER_REPUTABLE,
    "righttime.com": TIER_REPUTABLE,
    "gnomonwatches.com": TIER_REPUTABLE,
    "timepiece.com": TIER_REPUTABLE,
    "azfinetime.com": TIER_REPUTABLE,
    "jomashop.com": TIER_REPUTABLE,
    "bernsteinwatchco.com": TIER_REPUTABLE,
}

# Домены, где заведомо продаются реплики/подделки или нет контроля подлинности.
BLOCKED_DOMAINS = {
    "aliexpress.com",
    "dhgate.com",
    "wish.com",
    "taobao.com",
    "1688.com",
    "tmart.com",
    "bonanza.com",
    "ioffer.com",
    "replika-watch.ru",
    "replicawatches.ru",
    "fake-watches.ru",
    "replica-watch.ru",
    "replica-watches.ru",
    "copy-watches.ru",
    "aaa-watches.ru",
    "super-clone.ru",
    "watchreplica.ru",
}

# Ключевые слова в тексте страницы, которые однозначно указывают на подделку.
FAKE_KEYWORDS = {
    "replica", "replicas", "fake", "fakes",
    "knockoff", "knock-offs", "super clone", "superclone",
    "cloned", "imitation", "replica watch", "fake watch",
    "копия", "копии", "реплика", "реплики",
    "подделка", "подделки", "поддельные", "не оригинал",
    "aaa quality", "1:1 clone", "mirror clone",
}

# Ключевые слова, указывающие на то, что страница недоступна
# (HTTP-ошибки, аутентификация, запрет доступа), и её нельзя считать источником.
BLOCKED_PAGE_KEYWORDS = {
    "authentication required",
    "authorization required",
    "error 401",
    "error 403",
    "401 unauthorized",
    "403 forbidden",
    "server could not verify",
    "not authorized",
    "unauthorized access",
    "access denied",
    "access is denied",
}

# Подозрительные слова в домене.
SUSPICIOUS_DOMAIN_KEYWORDS = {"replica", "fake", "copy", "replika", "копия", "подделка", "aaa", "superclone"}


def _normalize_for_search(text):
    """Убирает разделители, чтобы искать артикул в разных написаниях."""
    if not text:
        return ""
    return re.sub(r"[\s\-_\.\/]", "", text.lower().strip())


def _domain_from_url(url):
    """Возвращает домен без www."""
    if not url:
        return ""
    m = re.search(r"https?://(?:www\.)?([^/]+)", url.lower())
    return m.group(1) if m else ""


def get_source_tier(url):
    """Возвращает уровень доверия источника по домену (целое число)."""
    domain = _domain_from_url(url)
    if not domain:
        return TIER_BLOCKED
    if any(domain == d or domain.endswith(f".{d}") for d in BLOCKED_DOMAINS):
        return TIER_BLOCKED
    for trusted, tier in TRUSTED_DOMAINS.items():
        if domain == trusted or domain.endswith(f".{trusted}"):
            return int(tier)
    # Домен сам по себе подозрительный?
    if any(k in domain for k in SUSPICIOUS_DOMAIN_KEYWORDS):
        return TIER_BLOCKED
    return TIER_UNKNOWN


def is_blocked_source(url, page_text=""):
    """True, если источник заведомо ненадёжный или страница недоступна."""
    if not url:
        return True
    if get_source_tier(url) == TIER_BLOCKED:
        return True
    if page_text:
        text_lower = page_text.lower()
        if any(kw in text_lower for kw in FAKE_KEYWORDS):
            return True
        if any(kw in text_lower for kw in BLOCKED_PAGE_KEYWORDS):
            return True
    return False


def is_trusted_source(url):
    """True, если источник в белом списке доверенных доменов."""
    return get_source_tier(url) in (TIER_OFFICIAL, TIER_AUTHORIZED, TIER_REPUTABLE)


def looks_fake(page_text):
    """Проверяет текст страницы на признаки реплик/подделок."""
    if not page_text:
        return False
    text_lower = page_text.lower()
    return any(kw in text_lower for kw in FAKE_KEYWORDS)


def _resolve_search_page(search_url, brand, articul, base_url, timeout=20):
    """Универсальный resolver: ищет на странице поиска ссылку на товар.

    Выбирает первую ссылку, в href которой есть нормализованный артикул
    и имя бренда.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
        }
        r = requests.get(search_url, headers=headers, timeout=timeout)
        r.raise_for_status()
        brand_lower = brand.strip().lower()
        brand_slug = brand_lower.replace(" ", "-")
        # "Baume & Mercier" в URL timeavenue кодируется как baume-amp-mercier
        brand_url_slug = brand_slug.replace("&", "-amp-")
        articul_norm = _normalize_for_search(articul)
        # Для Tissot на kronostime артикул в URL без разделителей (t1204101109100),
        # поэтому ищем также упрощённый вариант.
        articul_short = re.sub(r"[^a-z0-9]", "", articul.lower())
        # Time Avenue использует moa-10617 (дефис между MOA и цифрами)
        articul_alt = articul.lower().replace("m0a", "moa-").replace("moa", "moa-")
        variants = {articul_norm, articul_short, articul_alt}
        for a in BeautifulSoup(r.text, "html.parser").select("a"):
            href = a.get("href")
            if not href:
                continue
            href_lower = href.lower()
            text_lower = a.get_text(strip=True).lower()
            # Требуем присутствия бренда
            brand_match = (
                brand_lower in href_lower
                or brand_slug in href_lower
                or brand_url_slug in href_lower
                or brand_lower in text_lower
            )
            if not brand_match:
                continue
            if any(v in href_lower or v in text_lower for v in variants if v):
                return urljoin(base_url, href)
    except Exception:
        return ""
    return ""


# ---------------------------------------------------------------------------
# Resolver-функции для конкретных ритейлеров.
# Каждая возвращает прямой URL карточки товара или пустую строку.
# ---------------------------------------------------------------------------

def _resolve_montre24(brand, articul):
    url = f"https://www.montre24.ru/search/?q={quote_plus(_normalize_for_search(articul))}"
    return _resolve_search_page(url, brand, articul, "https://www.montre24.ru/")


def _resolve_shop_watches(brand, articul):
    url = f"https://www.shop-watches.ru/search/?q={quote_plus(_normalize_for_search(articul))}"
    return _resolve_search_page(url, brand, articul, "https://www.shop-watches.ru/")


def _resolve_watches_shop(brand, articul):
    url = f"https://www.watches-shop.ru/search/?q={quote_plus(_normalize_for_search(articul))}"
    return _resolve_search_page(url, brand, articul, "https://www.watches-shop.ru/")


def _resolve_watch_ru(brand, articul):
    url = f"https://www.watch.ru/search/?q={quote_plus(_normalize_for_search(articul))}"
    return _resolve_search_page(url, brand, articul, "https://www.watch.ru/")


def _resolve_timeshop(brand, articul):
    url = f"https://www.timeshop.ru/search/?q={quote_plus(_normalize_for_search(articul))}"
    return _resolve_search_page(url, brand, articul, "https://www.timeshop.ru/")


def _resolve_n_watches(brand, articul):
    url = f"https://www.n-watches.ru/search/?q={quote_plus(_normalize_for_search(articul))}"
    return _resolve_search_page(url, brand, articul, "https://www.n-watches.ru/")


def _resolve_kronostime(brand, articul):
    """Ищет карточку на kronostime.ru через прямой slug по артикулу.

    Kronostime использует URL вида /brand_norm_articul_norm/,
    где точки и слэши артикула убраны (t120.410.11.091.00 -> t1204101109100).
    """
    brand_lower = brand.strip().lower()
    articul_norm = _normalize_for_search(articul)
    if not brand_lower or not articul_norm:
        return ""
    direct = f"https://kronostime.ru/{brand_lower}_{articul_norm}/"
    try:
        r = requests.get(direct, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }, timeout=8)
        if r.status_code == 200 and "страница не найдена" not in r.text.lower():
            return direct
    except Exception:
        pass
    # Fallback: ищем через внутренний поиск
    search_url = f"https://kronostime.ru/search/?q={quote_plus(articul_norm)}"
    return _resolve_search_page(search_url, brand, articul, "https://kronostime.ru/", timeout=8)


def _resolve_4izmerenie(brand, articul):
    """Ищет карточку на 4-izmerenie.ru через внутренний поиск."""
    brand_lower = brand.strip().lower()
    articul_norm = _normalize_for_search(articul)
    search_url = f"https://4-izmerenie.ru/search/?search={quote_plus(articul_norm)}"
    return _resolve_search_page(search_url, brand, articul, "https://4-izmerenie.ru/")


from brand_urls import guess_collection


def _resolve_1224(brand, articul):
    """Прямой URL карточки на 12-24.com.

    URL имеет вид /watches/{brand_slug}/ref-{articul_lower_with_hyphens}/.
    """
    brand_lower = brand.strip().lower()
    if brand_lower == "bvlgari":
        brand_slug = "bulgari"
    else:
        brand_slug = brand_lower.replace(" ", "-")
    articul_slug = articul.strip().lower().replace("/", "-").replace(".", "-")
    return f"https://12-24.com/watches/{brand_slug}/ref-{articul_slug}"


def _resolve_thewatchcompany(brand, articul):
    """Прямой URL карточки на thewatchcompany.com.

    Пытается угадать slug коллекции; если не получилось — использует
    упрощённый вариант бренд-артикул.
    """
    brand_lower = brand.strip().lower().replace(" ", "-")
    articul_norm = _normalize_for_search(articul)
    collection = guess_collection(articul, brand)
    if collection:
        return f"https://www.thewatchcompany.com/{brand_lower}-{collection}-{articul_norm}.html"
    return f"https://www.thewatchcompany.com/{brand_lower}-{articul_norm}.html"


def _resolve_timeavenue(brand, articul):
    """Ищет карточку на timeavenue.ru.

    Внутренний поиск timeavenue.ru для артикула возвращает общий каталог бренда,
    поэтому сканируем страницы каталога и выбираем ссылку, содержащую артикул.
    URL карточки имеет вид /watches/{brand_slug}/{collection}/baume-...
    """
    brand_lower = brand.strip().lower()
    if not brand_lower:
        return ""
    brand_slug = brand_lower.replace(" ", "-").replace("&", "")
    if brand_lower == "baume & mercier":
        brand_slug = "baume-mercier"

    articul_norm = _normalize_for_search(articul)
    articul_alt = re.sub(r"-+", "-", articul.lower().replace("m0a", "moa-").replace("moa", "moa-"))
    variants = {v for v in (articul_norm, articul_alt, articul.lower()) if v}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    base = f"https://www.timeavenue.ru/watches/{brand_slug}/"
    for page in range(1, 8):
        url = base if page == 1 else f"{base}?PAGEN_1={page}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
            links = re.findall(r'href=\"/watches/' + re.escape(brand_slug) + r'/([^\"]+)\"', r.text, re.I)
            found = False
            for h in links:
                h_lower = h.lower()
                if any(v in h_lower for v in variants):
                    return f"https://www.timeavenue.ru/watches/{brand_slug}/{h}"
                if "pagen" in h_lower or h.count("/") <= 1:
                    found = True
            if not found and page > 1:
                # Нет товарных ссылок на странице — каталог закончился
                break
        except Exception:
            break

    # Fallback: внутренний поиск (редко работает для конкретного артикула)
    search_url = f"https://www.timeavenue.ru/search/?q={quote_plus(articul_norm)}"
    return _resolve_search_page(search_url, brand, articul, "https://www.timeavenue.ru/", timeout=10)


def _resolve_conquest_watches(brand, articul):
    """Ищет карточку на conquest-watches.ru через внутренний поиск.

    URL карточки имеет вид /catalog_watches/{brand_slug}/{brand}_{articul_lower}/.
    Сначала пробуем угадать slug, затем ищем через внутренний поиск.
    """
    brand_lower = brand.strip().lower()
    articul_norm = _normalize_for_search(articul)
    if not brand_lower or not articul_norm:
        return ""

    brand_slug = brand_lower.replace(" ", "-")
    direct = f"https://www.conquest-watches.ru/catalog_watches/{brand_slug}/{brand_lower}_{articul_norm}/"
    try:
        r = requests.get(direct, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }, timeout=8)
        if r.status_code == 200 and "404" not in r.text.lower() and "страница не найдена" not in r.text.lower():
            return direct
    except Exception:
        pass
    search_url = f"https://www.conquest-watches.ru/search/?q={quote_plus(articul_norm)}"
    return _resolve_search_page(search_url, brand, articul, "https://www.conquest-watches.ru/", timeout=10)


def _resolve_chrono_ru_search(brand, articul):
    """Ищет карточку на chrono.ru через внутренний поиск."""
    brand_lower = brand.strip().lower()
    articul_norm = _normalize_for_search(articul)
    search_url = f"https://chrono.ru/search/?q={quote_plus(articul_norm)}"
    return _resolve_search_page(search_url, brand, articul, "https://chrono.ru/")


# ---------------------------------------------------------------------------
# Публичный каталог resolver'ов для поиска по русским магазинам.
# ---------------------------------------------------------------------------

RU_RETAILER_RESOLVERS = [
    ("alltime.ru", None),          # специальный resolver в search.py
    ("watcheson.ru", None),        # специальный resolver в search.py
    ("bestwatch.ru", None),        # специальный resolver в search.py
    ("chrono.ru", _resolve_chrono_ru_search),
    ("thewatchcompany.com", _resolve_thewatchcompany),
    ("12-24.com", _resolve_1224),
    ("montre24.ru", _resolve_montre24),
    ("shop-watches.ru", _resolve_shop_watches),
    ("watches-shop.ru", _resolve_watches_shop),
    ("watch.ru", _resolve_watch_ru),
    ("timeshop.ru", _resolve_timeshop),
    ("n-watches.ru", _resolve_n_watches),
    ("kronostime.ru", _resolve_kronostime),
    ("4-izmerenie.ru", _resolve_4izmerenie),
    ("timeavenue.ru", _resolve_timeavenue),
    ("conquest-watches.ru", _resolve_conquest_watches),
]


# Предпочтительные fallback-шаблоны ритейлеров для брендов, у которых официальный
# сайт часто недоступен или не отдаёт данные. Каждая функция возвращает URL.
RETAILER_BRAND_TEMPLATES = {
    "epos": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "tissot": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "rado": [_resolve_conquest_watches, _resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "mido": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "certina": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "hamilton": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "longines": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "frederique constant": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "baume & mercier": [_resolve_timeavenue, _resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "maurice lacroix": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "oris": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "titoni": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "mathey-tissot": [_resolve_kronostime, _resolve_1224, _resolve_thewatchcompany],
    "tudor": [_resolve_1224, _resolve_thewatchcompany],
    "tag heuer": [_resolve_1224, _resolve_thewatchcompany],
}
