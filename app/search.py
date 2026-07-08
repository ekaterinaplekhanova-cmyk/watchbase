import json
import random
import re
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from brand_urls import (
    get_official_url,
    get_official_url_candidates,
    guess_collection,
    guess_universal_urls,
)
from retailers import (
    RETAILER_BRAND_TEMPLATES,
    RU_RETAILER_RESOLVERS,
    TIER_OFFICIAL,
    get_source_tier,
    is_blocked_source,
    is_trusted_source,
)

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


# Набор User-Agent'ов с разной степенью детализации. Chrome-like UA часто
# провоцирует таймауты на официальных сайтах (iwc.com, breitling.com),
# поэтому первыми идут нейтральные/браузерные UA без Chrome.
USER_AGENT_VARIANTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Bing скрывает li.b_algo h2 a для User-Agent'ов, явно помеченных как Chrome,
# поэтому используем нейтральный Windows-Firefox UA для поисковых движков.
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT_VARIANTS[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

HEADER_VARIANTS = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Referer": "https://www.google.com/",
    },
]


# Жёсткий лимит на поиск характеристик (сек).
SEARCH_OVERALL_TIMEOUT = 42


# Домены, которые не являются источниками характеристик часов.
BLOCKED_DOMAINS = {
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "reddit.com",
    "startpage.com",
    "startpage.media",
}


# ---------------------------------------------------------------------------
# Простой JSON-кэш поиска (articul -> {"url": ..., "text": ..., "tier": ...})
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SEARCH_CACHE_PATH = PROJECT_ROOT / "output" / "search_cache.json"
_search_cache = {}


def _load_search_cache():
    global _search_cache
    if _search_cache:
        return _search_cache
    if SEARCH_CACHE_PATH.exists():
        try:
            with open(SEARCH_CACHE_PATH, "r", encoding="utf-8") as f:
                _search_cache = json.load(f)
            if not isinstance(_search_cache, dict):
                _search_cache = {}
        except Exception:
            _search_cache = {}
    else:
        _search_cache = {}
    return _search_cache


def _save_search_cache():
    try:
        SEARCH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SEARCH_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_search_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_cached_search(articul, brand):
    cache = _load_search_cache()
    key = f"{brand.strip().lower()}:{articul.strip().upper()}"
    entry = cache.get(key)
    if entry and entry.get("text"):
        url = entry.get("url")
        text = entry.get("text")
        # Пересчитываем tier, потому что список доверенных доменов может меняться.
        tier = get_source_tier(url)
        # Не возвращаем закэшированные ошибки / страницы с HTTP-401/403.
        if not is_blocked_source(url, text):
            return url, text, tier
    return None


def set_cached_search(articul, brand, url, text, tier):
    cache = _load_search_cache()
    key = f"{brand.strip().lower()}:{articul.strip().upper()}"
    cache[key] = {"url": url, "text": text, "tier": tier}
    _save_search_cache()


# ---------------------------------------------------------------------------
# Кэш для Playwright-рендеринга (URL -> текст), чтобы не рендерить повторно.
# ---------------------------------------------------------------------------
RENDER_CACHE_PATH = PROJECT_ROOT / "output" / "render_cache.json"
_render_cache = {}


def _load_render_cache():
    global _render_cache
    if _render_cache:
        return _render_cache
    if RENDER_CACHE_PATH.exists():
        try:
            with open(RENDER_CACHE_PATH, "r", encoding="utf-8") as f:
                _render_cache = json.load(f)
        except Exception:
            _render_cache = {}
    else:
        _render_cache = {}
    return _render_cache


def _save_render_cache():
    try:
        RENDER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RENDER_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_render_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_cached_render(url):
    cache = _load_render_cache()
    return cache.get(url)


def set_cached_render(url, text):
    cache = _load_render_cache()
    cache[url] = text
    _save_render_cache()


def _is_valid_source_url(url):
    """Проверяет, что URL не ведёт на соцсеть, поисковик, мусорный или поддельный сайт."""
    if not url or not url.startswith("http"):
        return False
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    if any(host == d or host.endswith(f".{d}") for d in BLOCKED_DOMAINS):
        return False
    if is_blocked_source(url):
        return False
    # Исключаем страницы корневых доменов без пути, если это поисковики
    if host in ("google.com", "bing.com", "duckduckgo.com", "startpage.com"):
        return False
    return True


def _resolve_alltime_url(brand, articul):
    """Ищет точный URL товара на alltime.ru через страницу каталога бренда."""
    brand_lower = brand.strip().lower()
    articul_lower = articul.strip().lower()
    catalog_url = f"https://www.alltime.ru/watch/filter/brand:{brand_lower}/"
    try:
        r = requests.get(catalog_url, headers=DEFAULT_HEADERS, timeout=12)
        r.raise_for_status()
        text = r.text
        pattern = re.compile(
            r'(?:href|data-href)="(/watch/' + re.escape(brand_lower) + r'/\s*' +
            re.escape(articul_lower) + r'/\d+/)"',
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return "https://www.alltime.ru" + match.group(1)
        for a in BeautifulSoup(text, "html.parser").select("a"):
            href = a.get("href")
            if href and articul_lower in href.lower() and "/watch/" in href and brand_lower in href.lower():
                return href if href.startswith("http") else "https://www.alltime.ru" + href
    except Exception:
        return ""
    return ""


def _resolve_watcheson_url(brand, articul):
    """Ищет карточку товара на watcheson.ru через внутренний поиск."""
    brand_lower = brand.strip().lower()
    articul_lower = articul.strip().lower()
    search_url = f"https://www.watcheson.ru/search/?q={quote_plus(articul)}"
    try:
        r = requests.get(search_url, headers=DEFAULT_HEADERS, timeout=10)
        r.raise_for_status()
        for a in BeautifulSoup(r.text, "html.parser").select("a"):
            href = a.get("href")
            if not href:
                continue
            href_lower = href.lower()
            if brand_lower not in href_lower:
                continue
            if articul_lower.replace("-", "").replace("_", "") not in href_lower:
                continue
            return href if href.startswith("http") else "https://watcheson.ru" + href
    except Exception:
        return ""
    return ""


def _resolve_bestwatch_url(brand, articul):
    """Ищет карточку товара на bestwatch.ru через внутренний поиск."""
    brand_lower = brand.strip().lower()
    articul_lower = articul.strip().lower()
    search_url = f"https://www.bestwatch.ru/search/?q={quote_plus(articul)}"
    try:
        r = requests.get(search_url, headers=DEFAULT_HEADERS, timeout=10)
        r.raise_for_status()
        for a in BeautifulSoup(r.text, "html.parser").select("a"):
            href = a.get("href")
            if not href:
                continue
            href_lower = href.lower()
            if brand_lower not in href_lower:
                continue
            if articul_lower.replace("-", "").replace("_", "") not in href_lower:
                continue
            return href if href.startswith("http") else "https://www.bestwatch.ru" + href
    except Exception:
        return ""
    return ""


def resolve_bing_redirect(url):
    """Распаковывает редирект Bing и возвращает реальный URL."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "u" in qs:
            encoded = qs["u"][0]
            if encoded.startswith("a1"):
                decoded = encoded[2:]
                import base64
                try:
                    real = base64.urlsafe_b64decode(decoded + "==").decode("utf-8")
                    if real.startswith("http"):
                        return real
                except Exception:
                    pass
        r = requests.head(url, allow_redirects=True, timeout=8, headers=DEFAULT_HEADERS)
        if r.url and r.url.startswith("http"):
            return r.url
    except Exception:
        pass
    return url


def bing_search(query, num_results=5):
    """Поиск через Bing с распаковкой редиректов.

    Используем setmkt=en-us&setlang=en, чтобы Bing не подменял результаты
    локальными/несвязанными страницами из-за гео- или языкового таргетинга.
    """
    url = (
        f"https://www.bing.com/search?q={quote_plus(query)}"
        f"&count={num_results}&setmkt=en-us&setlang=en"
    )
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []

        for a in soup.select("li.b_algo h2 a"):
            href = a.get("href")
            if href and href.startswith("http") and "bing.com" not in href:
                links.append(href)
            elif href and href.startswith("https://www.bing.com/ck/a"):
                real = resolve_bing_redirect(href)
                if real.startswith("http") and "bing.com" not in real:
                    links.append(real)

        for a in soup.select("a"):
            href = a.get("href")
            if not href or href in links:
                continue
            if href.startswith("https://www.bing.com/ck/a"):
                real = resolve_bing_redirect(href)
                if real.startswith("http") and "bing.com" not in real:
                    links.append(real)
            elif href.startswith("http") and "bing.com" not in href:
                links.append(href)

        seen = set()
        unique = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique.append(link)
        return unique[:num_results]
    except Exception as e:
        return [f"[Ошибка поиска: {e}"]


def google_search(query, num_results=5):
    """Простой поиск через Google."""
    headers = {"User-Agent": DEFAULT_HEADERS["User-Agent"]}
    url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for g in soup.select("a[href]"):
            href = g.get("href")
            if href and href.startswith("/url?q="):
                real_url = href.split("/url?q=")[1].split("&")[0]
                if real_url.startswith("http"):
                    links.append(real_url)
        return links[:num_results]
    except Exception as e:
        return [f"[Ошибка поиска: {e}"]


def duckduckgo_search(query, num_results=5):
    """Поиск через DuckDuckGo HTML-версию."""
    headers = {"User-Agent": DEFAULT_HEADERS["User-Agent"]}
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)
        return links[:num_results]
    except Exception as e:
        return [f"[Ошибка поиска: {e}"]


def startpage_search(query, num_results=5):
    """Поиск через Startpage. Часто работает, когда Bing/Google требуют JS/капчу."""
    url = "https://www.startpage.com/sp/search"
    params = {
        "query": query,
        "cat": "web",
        "pl": "opensearch",
    }
    headers = {
        "User-Agent": DEFAULT_HEADERS["User-Agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.select("a"):
            href = a.get("href")
            text = a.get_text(strip=True)
            if not href or not href.startswith("http"):
                continue
            if "startpage.com" in href:
                continue
            if href in links:
                continue
            links.append(href)

        seen = set()
        unique = []
        for link in links:
            parsed = urlparse(link)
            host_parts = parsed.netloc.split(".")
            if len(host_parts) > 2 and re.match(r"^[a-z]{2}-[a-z]{2}$", host_parts[0]):
                normalized_host = ".".join(host_parts[1:])
            else:
                normalized_host = parsed.netloc
            key = (normalized_host, parsed.path)
            if key not in seen:
                seen.add(key)
                unique.append(link)
        return unique[:num_results]
    except Exception as e:
        return [f"[Ошибка поиска: {e}"]






def _search_all(query, num_results=5, prefer=None):
    """Запускает поиск ПАРАЛЛЕЛЬНО через несколько движков и объединяет результаты.

    prefer — список движков, которые должны быть первыми.
    """
    engines = [startpage_search, bing_search, duckduckgo_search, google_search]
    if prefer:
        preferred = [e for e in prefer if e in engines]
        rest = [e for e in engines if e not in preferred]
        engines = preferred + rest

    results = {}
    try:
        with ThreadPoolExecutor(max_workers=len(engines)) as executor:
            future_to_engine = {executor.submit(e, query, num_results): e for e in engines}
            for future in as_completed(future_to_engine, timeout=10):
                engine = future_to_engine[future]
                try:
                    results[engine.__name__] = future.result()
                except Exception:
                    results[engine.__name__] = []
    except TimeoutError:
        # Часть движков не ответила вовремя — используем то, что успело вернуться
        for engine in engines:
            if engine.__name__ not in results:
                results[engine.__name__] = []

    seen = set()
    unique = []
    for engine in engines:
        for url in results.get(engine.__name__, []):
            if not url.startswith("http") or url.startswith("["):
                continue
            if not _is_valid_source_url(url):
                continue
            if url not in seen:
                seen.add(url)
                unique.append(url)
    return unique[:num_results]


def _search_ru(query, num_results=5):
    """Поиск с приоритетом Google/Bing для русскоязычных site-запросов."""
    return _search_all(query, num_results=num_results, prefer=[google_search, bing_search])


def _search_fast_fallback(brand, articul, deadline=None):
    """Быстрый общий поиск: поисковые движки + короткая валидация.

    Возвращает первого кандидата, прошедшего проверку по бренду и артикулу.
    Early-exit, чтобы не ждать медленные официальные сайты в stage1.
    """
    query = f"{brand} {articul} official specifications watch"
    try:
        urls = _search_all(query, num_results=8, prefer=[bing_search, google_search, duckduckgo_search])
    except Exception:
        return None

    executor = ThreadPoolExecutor(max_workers=min(4, len(urls)))
    futures = {executor.submit(fetch_page_text, url, 4): url for url in urls if _url_contains_articul(url, articul)}
    try:
        remaining = min(7, max(1, int(deadline - time.time()))) if deadline else 7
        for future in as_completed(futures, timeout=remaining):
            url = futures[future]
            try:
                text = future.result()
                if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                    if not is_blocked_source(url, text):
                        executor.shutdown(wait=False, cancel_futures=True)
                        return get_source_tier(url), url, text
            except Exception:
                continue
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)
    return None


def search_thewatchpages(articul, brand, deadline=None):
    """Ищет карточку на The Watch Pages через их поиск.

    Thewatchpages.com часто знает малоизвестные бренды (U-Boat, Bomberg,
    Piaget и др.), поэтому используем его как дополнительный источник.
    """
    query = quote_plus(articul)
    search_url = f"https://www.thewatchpages.com/?s={query}"
    try:
        r = requests.get(search_url, headers=DEFAULT_HEADERS, timeout=6)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href or not href.startswith("https://www.thewatchpages.com/watches/"):
                continue
            if _url_contains_articul(href, articul) and href not in links:
                links.append(href)
        for url in links[:3]:
            if _deadline_reached(deadline):
                break
            text = fetch_page_text(url, timeout=5)
            if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                if not is_blocked_source(url, text):
                    return url, text
    except Exception:
        pass
    return "", ""


def _clean_page_text(raw_html):
    """Извлекает читаемый текст из HTML и ставит спек-строки первыми.

    Для карточек conquest-watches.ru и других сайтов с блочными
    характеристиками формирует парные строки "Метка: Значение".
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    spec_pairs = []
    # conquest-watches.ru: .product-card_properties_item > .name + .value
    for item in soup.find_all("div", class_="product-card_properties_item"):
        name = item.find("div", class_="name")
        value = item.find("div", class_="value")
        if name and value:
            n = " ".join(name.stripped_strings)
            v = " ".join(value.stripped_strings)
            if n and v:
                spec_pairs.append(f"{n}: {v}")

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    spec_keywords = [
        "калибр", "механизм", "корпус", "браслет", "ремешок", "ремінь",
        "стекло", "циферблат", "водозащита", "водонепроницаем", "водостойк",
        "диаметр", "толщина", "высота", "вес", "страна", "производство",
        "гарантия", "кварцев", "механическ", "автоподзавод", "sapphire",
        "минеральное", "заводная", "материал", "полиамид", "карбон", "титан",
        # английские спек-метки, встречающиеся на карточках ритейлеров
        "calibre", "caliber", "movement", "jewels", "frequency", "power reserve",
        "case size", "case material", "bracelet", "strap", "dial", "water resistance",
    ]
    spec_lines = [l for l in lines if any(k in l.lower() for k in spec_keywords)]
    other_lines = [l for l in lines if l not in spec_lines]
    ordered = spec_pairs + spec_lines + other_lines
    return "\n".join(ordered[:400])


def _requests_page_text(url, timeout=10, stream=False, max_bytes=262144, headers=None):
    """Низкоуровневая загрузка через requests."""
    if stream:
        r = requests.get(url, headers=headers, timeout=timeout, stream=True)
        r.raise_for_status()
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                continue
            chunks.append(chunk)
            total += len(chunk)
            if total >= max_bytes:
                break
        raw = b"".join(chunks).decode("utf-8", errors="ignore")
    else:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        # Time Avenue и некоторые другие русские сайты не указывают charset в
        # Content-Type, тогда requests выбирает ISO-8859-1. Принудительно
        # используем UTF-8, если декодирование как UTF-8 даёт русские буквы.
        if r.encoding and r.encoding.lower() in ("iso-8859-1", "latin-1"):
            try:
                raw = r.content.decode("utf-8")
            except UnicodeDecodeError:
                raw = r.text
        else:
            raw = r.text
    return _clean_page_text(raw)


def _fetch_page_text_js(url, timeout=20):
    """Загружает страницу через Playwright (Chromium) и возвращает текст body."""
    if not PLAYWRIGHT_AVAILABLE:
        return "[Ошибка JS-загрузки: Playwright не установлен]"

    cached = get_cached_render(url)
    if cached:
        return cached

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENT_VARIANTS),
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            # Небольшая пауза, чтобы ленивый контент успел отрендериться.
            time.sleep(0.5)
            text = page.inner_text("body")
            browser.close()
            if text and len(text.strip()) > 100:
                cleaned = _clean_page_text(text)
                set_cached_render(url, cleaned)
                return cleaned
            return "[Ошибка JS-загрузки: пустой текст страницы]"
    except Exception as e:
        return f"[Ошибка JS-загрузки: {e}]"


def _error_suggests_js_block(error_text):
    """True, если ошибка requests похожа на защиту официального сайта."""
    if not error_text:
        return False
    lower = error_text.lower()
    markers = [
        "403",
        "forbidden",
        "timeout",
        "connecttimeout",
        "readtimeout",
        "cloudflare",
        "js challenge",
        "enable javascript",
    ]
    return any(m in lower for m in markers)


def _is_official_domain(url, brand=""):
    """True, если домен является официальным сайтом бренда или похож на него."""
    if not url:
        return False
    if get_source_tier(url) == TIER_OFFICIAL:
        return True
    if brand:
        brand_slug = brand.strip().lower().replace(" ", "")
        host = urlparse(url).netloc.lower().replace("www.", "").replace("-", "")
        if brand_slug in host:
            return True
    return False


def fetch_page_text(url, timeout=10, retries=0, stream=False, max_bytes=262144, use_js=False):
    """Загружает текст страницы с повторными попытками и ротацией заголовков.

    Если use_js=True или requests получает блок/таймаут на официальном домене,
    пробует Playwright-рендеринг.
    """
    last_error = ""

    if use_js:
        return _fetch_page_text_js(url, timeout=max(timeout, 15))

    for attempt in range(retries + 1):
        try:
            headers = {"User-Agent": USER_AGENT_VARIANTS[attempt % len(USER_AGENT_VARIANTS)]}
            headers.update(HEADER_VARIANTS[attempt % len(HEADER_VARIANTS)])
            text = _requests_page_text(
                url,
                timeout=timeout,
                stream=stream,
                max_bytes=max_bytes,
                headers=headers,
            )
            return text
        except Exception as e:
            last_error = str(e)
            if attempt < retries:
                time.sleep(1)
                continue

    return f"[Ошибка загрузки страницы: {last_error}]"


def fetch_page_text_with_js_fallback(url, timeout=10, retries=1, brand=""):
    """Сначала requests, при неудаче (особенно на официальном сайте) — Playwright."""
    text = fetch_page_text(url, timeout=timeout, retries=retries)
    if not text.startswith("["):
        return text
    if _is_official_domain(url, brand) or _error_suggests_js_block(text):
        js_text = _fetch_page_text_js(url, timeout=max(timeout + 10, 20))
        if not js_text.startswith("["):
            return js_text
    return text


def extract_collection_from_url(url):
    """Извлекает slug коллекции из URL официального сайта Cartier."""
    match = re.search(r"/watches/collections/([^/]+)/", url)
    if match:
        return match.group(1)
    return ""


def _cartier_ref_variants(articul):
    """Возвращает варианты написания артикула Cartier для поиска."""
    ref = articul.upper().strip()
    variants = {ref}
    if not ref.startswith("CRW"):
        variants.add(f"CRW{ref}")
    else:
        variants.add(ref[3:])
    return variants


def search_cartier_official(articul, brand="cartier"):
    """Ищет официальную страницу Cartier через Startpage, определяя коллекцию из URL."""
    variants = _cartier_ref_variants(articul)
    for ref in variants:
        query = f"site:cartier.com {ref}"
        urls = _search_all(query, num_results=5)
        for url in urls:
            if not url.startswith("http"):
                continue
            if "cartier.com" not in url:
                continue
            collection = extract_collection_from_url(url)
            if collection:
                text = fetch_page_text(url, timeout=10)
                if not text.startswith("[Ошибка") and len(text) > 200:
                    return url, text, collection
    return "", "", ""


def search_caliber_specs(caliber, brand=""):
    """Ищет калибровые данные (jewels, frequency, power reserve) через поиск."""
    if not caliber or caliber == "не найдено":
        return ""

    brand_part = f"{brand} " if brand else ""
    queries = [
        f'"{caliber}" {brand_part}caliber jewels frequency specifications',
        f'"{caliber}" {brand_part}movement jewels power reserve',
        f'"{caliber}" site:calibercorner.com',
        f'"{caliber}" site:monochrome-watches.com caliber',
        f'"{caliber}" site:hodinkee.com',
    ]

    for query in queries:
        urls = _search_all(query, num_results=3)
        for url in urls:
            if not url.startswith("http") or url.startswith("["):
                continue
            text = fetch_page_text(url, timeout=10)
            if not text.startswith("[Ошибка") and len(text) > 200:
                return text
    return ""


def search_watchbase(caliber, brand=""):
    """Ищет страницу калибра на watchbase.com и возвращает текст."""
    if not caliber or caliber == "не найдено":
        return ""
    clean_caliber = re.sub(r"[^\w\-]", "", caliber).strip()
    if not clean_caliber:
        return ""

    brand_slug = brand.strip().lower() if brand else ""
    lower_cal = clean_caliber.lower()

    urls_to_try = [
        f"https://watchbase.com/{brand_slug}/caliber/{lower_cal}" if brand_slug else f"https://watchbase.com/caliber/{lower_cal}",
        f"https://watchbase.com/caliber/{lower_cal}",
    ]

    query = f"site:watchbase.com {clean_caliber}"
    try:
        urls = _search_all(query, num_results=3)
        for url in urls:
            if "watchbase.com" in url and lower_cal in url.lower():
                if url not in urls_to_try:
                    urls_to_try.append(url)
    except Exception:
        pass

    for url in urls_to_try:
        if not url:
            continue
        text = fetch_page_text(url, timeout=10)
        if not text.startswith("[Ошибка") and len(text) > 100:
            return text
    return ""


def search_watchbase_model(brand, articul):
    """Ищет страницу конкретной модели на watchbase.com и возвращает текст.

    Это полезнее страницы калибра, т.к. watchbase для модели указывает
    реальный калибр (например, Longines L888.2 вместо выдуманного LLM-ом).
    """
    brand_slug = brand.strip().lower()
    articul_slug = re.sub(r"[^\w\-]", "", articul).strip().lower()
    if not brand_slug or not articul_slug:
        return ""

    urls_to_try = [
        f"https://watchbase.com/{brand_slug}/{articul_slug}",
        f"https://watchbase.com/{brand_slug}/watch/{articul_slug}",
    ]

    # Grand Seiko: на WatchBase артикулы без суффикса G и вложены в /mechanical/ или /quartz/.
    if brand_slug == "grand seiko":
        base_ref = articul_slug.rstrip("g")
        urls_to_try = [
            f"https://watchbase.com/grand-seiko/mechanical/{base_ref}",
            f"https://watchbase.com/grand-seiko/quartz/{base_ref}",
            f"https://watchbase.com/grand-seiko/{base_ref}",
        ]

    collection = guess_collection(articul, brand)
    if collection and brand_slug != "grand seiko":
        collection_slug = collection.lower().replace(" ", "-")
        urls_to_try.insert(
            0, f"https://watchbase.com/{brand_slug}/{collection_slug}/{articul_slug}"
        )

    query = f"site:watchbase.com {brand} {articul}"
    try:
        urls = _search_all(query, num_results=3)
        for url in urls:
            if "watchbase.com" in url and articul_slug in url.lower():
                if url not in urls_to_try:
                    urls_to_try.append(url)
    except Exception:
        pass

    for url in urls_to_try:
        if not url:
            continue
        text = fetch_page_text(url, timeout=10)
        if not text.startswith("[Ошибка") and len(text) > 200:
            return text
    return ""


def search_watchbase_page(brand, articul, deadline=None):
    """Возвращает (URL, текст) страницы модели на watchbase.com.

    WatchBase предсказуемо покрывает Swatch, Breitling и ряд других брендов.
    Не используем здесь общий поиск, чтобы не ждать медленных поисковых движков.
    """
    brand_slug = brand.strip().lower()
    articul_slug = re.sub(r"[^\w\-]", "", articul).strip().lower()
    if not brand_slug or not articul_slug:
        return "", ""

    urls_to_try = [
        f"https://watchbase.com/{brand_slug}/{articul_slug}",
        f"https://watchbase.com/{brand_slug}/watch/{articul_slug}",
    ]

    # Grand Seiko: на WatchBase артикулы без суффикса G и вложены в /mechanical/ или /quartz/.
    if brand_slug == "grand seiko":
        base_ref = articul_slug.rstrip("g")
        urls_to_try = [
            f"https://watchbase.com/grand-seiko/mechanical/{base_ref}",
            f"https://watchbase.com/grand-seiko/quartz/{base_ref}",
            f"https://watchbase.com/grand-seiko/{base_ref}",
        ]

    collection = guess_collection(articul, brand)
    if collection and brand_slug != "grand seiko":
        collection_slug = collection.lower().replace(" ", "-")
        urls_to_try.insert(0, f"https://watchbase.com/{brand_slug}/{collection_slug}/{articul_slug}")
        # Альтернативные slug'и коллекции (например, superocean vs super-ocean)
        if " " in collection:
            urls_to_try.insert(
                1, f"https://watchbase.com/{brand_slug}/{collection_slug.replace(' ', '-')}/{articul_slug}"
            )
        if "-" in collection:
            urls_to_try.insert(
                2, f"https://watchbase.com/{brand_slug}/{collection_slug.replace('-', '')}/{articul_slug}"
            )

    seen = set()
    for url in urls_to_try:
        if _deadline_reached(deadline):
            break
        if url in seen:
            continue
        seen.add(url)
        # WatchBase часто медленный из текущей сети — даём больше времени и ретрай.
        text = fetch_page_text(url, timeout=15, retries=2 if "watchbase.com" in url else 0)
        if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
            if not is_blocked_source(url, text):
                return url, text
    return "", ""


# Бренды, для которых у chronomaster.co.uk есть отдельная страница каталога.
# Ссылки на ней содержат артикул в тексте/URL, поэтому можно вытащить
# прямую карточку товара без поисковых движков.
CHRONOMASTER_BRAND_SLUGS = {
    "steinhart": "steinhart",
}


def _loose_alnum(text):
    """Убирает всё, кроме букв и цифр, для гибкого сравнения артикулов."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def search_chronomaster(brand, articul, deadline=None):
    """Ищет карточку на chronomaster.co.uk через страницу бренда.

    Chronomaster публикует полные списки моделей бренда; по артикулу в тексте
    ссылки находим прямой URL карточки. Пока используем для Steinhart.
    """
    brand_lower = brand.strip().lower()
    slug = CHRONOMASTER_BRAND_SLUGS.get(brand_lower)
    if not slug:
        return "", ""

    brand_page = f"https://www.chronomaster.co.uk/{slug}/"
    try:
        r = requests.get(brand_page, headers=DEFAULT_HEADERS, timeout=5)
        if r.status_code != 200:
            return "", ""
    except Exception:
        return "", ""

    if _deadline_reached(deadline):
        return "", ""

    loose_articul = _loose_alnum(articul)
    if not loose_articul:
        return "", ""

    seen = set()
    product_urls = []
    for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        loose_href = _loose_alnum(href)
        loose_text = _loose_alnum(text)
        if loose_articul not in loose_href and loose_articul not in loose_text:
            continue
        if href.startswith("/"):
            url = "https://www.chronomaster.co.uk" + href
        elif href.startswith("http"):
            url = href
        else:
            continue
        if url not in seen:
            seen.add(url)
            product_urls.append(url)
            if len(product_urls) >= 3:
                break

    for url in product_urls:
        if _deadline_reached(deadline):
            break
        text = fetch_page_text(url, timeout=4)
        if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
            if not is_blocked_source(url, text):
                return url, text
    return "", ""


# Список авторизованных дилеров и профильных площадок с шаблонами URL.
DEALER_TEMPLATES = {
    "caratco": "https://www.caratco.com/products/{articul_lower}",
    "thewatchsource": "https://www.thewatchsource.co.uk/{brand_title}/{articul_upper}.html",
    "uhren2000": "https://www.uhren2000.de/en/products/{brand_lower}-{articul_lower}",
    "watches-swiss": "https://www.watches-swiss.com/{articul_upper}-{brand_title}-",
    "carollinum": "https://www.carollinum.cz/en/{brand_lower}-{articul_lower}",
    "thewatchagency": "https://www.thewatchagency.com/{brand_lower}/{articul_lower}/",
    "the1916company": "https://www.the1916company.com/watches/{brand_lower}/{articul_lower}/",
    "cortinawatch": "https://www.cortinawatch.com/en/{brand_lower}/{collection_slug}/{articul_lower}/",
    "watchfinder": "https://www.watchfinder.co.uk/{brand_lower}/{articul_upper}/detail",
    "chron24": "https://www.chrono24.com/search.htm?query={articul_upper}+{brand_title}",
}


def _fetch_dealer_url(url, articul, brand, seen):
    if not url or url in seen:
        return None
    seen.add(url)
    text = fetch_page_text(url, timeout=8, retries=0)
    if not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
        return url, text
    return None


def _resolve_watchfinder_url(brand, articul):
    """Возвращает URL watchfinder.co.uk по бренду и артикулу."""
    brand_lower = brand.strip().lower().replace(" ", "-")
    articul_upper = articul.strip().upper()
    return f"https://www.watchfinder.co.uk/{brand_lower}/{articul_upper}/detail"


def search_dealer_pages(articul, brand):
    """Пробует загрузить страницы авторизованных дилеров по артикулу (параллельно).

    Возвращает лучший результат по tier, а не первый попавшийся.
    """
    brand_lower = brand.strip().lower()
    articul_lower = articul.strip().lower()
    articul_upper = articul.strip().upper()
    brand_title = brand.strip().title()
    brand_slug_hyphen = brand_lower.replace(" ", "-")
    collection_slug = guess_collection(articul, brand)
    if brand_lower == "bvlgari":
        brand_slug = "bulgari"
    else:
        brand_slug = brand_slug_hyphen

    dealer_templates = [
        f"https://www.caratco.com/products/{articul_lower}",
        f"https://www.the1916company.com/watches/{brand_slug_hyphen}/{articul_lower}/",
        f"https://www.watches-of-switzerland.co.uk/{brand_title}/{articul_upper}/detail",
        f"https://www.firstclasswatches.co.uk/{brand_slug_hyphen}-{articul_lower}.html",
        f"https://www.mayors.com/{brand_slug_hyphen}-{articul_lower}.html",
        f"https://www.crownandcaliber.com/watches/{brand_slug_hyphen}/{articul_lower}",
        f"https://www.thewatchsource.co.uk/{brand_title}/{articul_upper}.html",
        f"https://www.uhren2000.de/en/products/{brand_lower}-{articul_lower}",
        f"https://www.watches-swiss.com/{articul_upper}-{brand_title}-",
        f"https://www.carollinum.cz/en/{brand_lower}-{articul_lower}",
        f"https://www.thewatchagency.com/{brand_lower}/{articul_lower}/",
    ]
    if collection_slug:
        dealer_templates.append(
            f"https://www.cortinawatch.com/en/{brand_lower}/{collection_slug}/{articul_lower}/"
        )
        dealer_templates.append(
            f"https://www.thewatchcompany.com/{brand_slug}-{collection_slug}-{articul_lower}.html"
        )
        dealer_templates.append(
            f"https://www.watchfinder.mt/watches/{brand_slug_hyphen}/{collection_slug}/{articul_lower}/"
        )

    dealer_templates.append(_resolve_watchfinder_url(brand, articul))

    seen = set()
    results = []
    try:
        with ThreadPoolExecutor(max_workers=min(8, len(dealer_templates))) as executor:
            futures = [executor.submit(_fetch_dealer_url, url, articul, brand, seen) for url in dealer_templates]
            for future in as_completed(futures, timeout=8):
                result = future.result()
                if result:
                    url, text = result
                    tier = get_source_tier(url)
                    results.append((tier, url, text))
                if results:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)

    if results:
        results.sort(key=lambda x: x[0])
        _, url, text = results[0]
        return url, text
    return "", ""


def _normalize_articul(articul):
    """Убирает разделители из артикула для гибкого поиска."""
    if not articul:
        return ""
    return re.sub(r"[\s\-_\.\/]", "", articul.lower().strip())


# Варианты написания бренда, которые легко спутать с другими словами.
# Для них требуем полное совпадение, а не подстроку.
BRAND_EXACT_MATCH = {"tag", "ap", "iwc", "tissot", "rado", "mido", "oris", "ebel", "dior", "hermes"}


def _brand_variants(brand):
    """Возвращает множество строк для гибкой проверки бренда в тексте/URL."""
    if not brand:
        return set()
    brand_lower = brand.strip().lower()
    brand_norm = re.sub(r"[\s&\.\-]", "", brand_lower)
    variants = {brand_lower, brand_norm}
    # Доменный slug (например, audemarspiguet, tagheuer)
    from brand_urls import _brand_domain_slug
    variants.add(_brand_domain_slug(brand))
    # Для брендов из двух слов — оба слова отдельно, если они не слишком общие.
    parts = [p for p in re.split(r"[\s&\-]", brand_lower) if len(p) > 1]
    # "boat" встречается слишком часто отдельно от бренда U-BOAT.
    if brand_lower == "u-boat":
        parts = [p for p in parts if p != "boat"]
    variants.update(parts)
    # Специфические псевдонимы
    aliases = {
        "blancpain": {"blancpain"},
        "bvlgari": {"bulgari", "bvlgar"},
        "a. lange & söhne": {"alange", "lange"},
        "tag heuer": {"tagheuer"},
        "audemars piguet": {"audemarspiguet", "audemars", "piguet"},
    }
    variants.update(aliases.get(brand_lower, set()))
    return {v for v in variants if v}


def _url_contains_brand(url, brand):
    """Проверяет, что URL содержит slug бренда (или домен бренда)."""
    if not url or not brand:
        return False
    host = urlparse(url).netloc.lower().replace("www.", "")
    path = urlparse(url).path.lower()
    variants = _brand_variants(brand)
    for v in variants:
        if not v:
            continue
        if v in host or v in path:
            return True
    return False


def _text_contains_brand(text, brand):
    """Проверяет, что текст страницы явно упоминает запрошенный бренд."""
    if not text or not brand:
        return False
    text_lower = text.lower()
    variants = _brand_variants(brand)
    for v in variants:
        if not v or len(v) < 2:
            continue
        if v in BRAND_EXACT_MATCH:
            # Требуем точное слово, чтобы "tag" не ловил "tagged"
            if re.search(rf"\b{re.escape(v)}\b", text_lower):
                return True
        else:
            if v in text_lower:
                return True
    return False


def _url_contains_articul(url, articul):
    """Проверяет, что URL содержит артикул (с учётом вариантов написания)."""
    if not url:
        return False
    url_lower = url.lower()
    articul_lower = articul.lower().strip()
    normalized = _normalize_articul(articul)
    # URL часто заменяет "/" и "." на "-" (a082/03209 -> a082-03209)
    hyphenated = articul_lower.replace("/", "-").replace(".", "-")
    variants = {
        articul_lower,
        normalized,
        hyphenated,
        f"tr_{articul_lower}",
        f"tr.{articul_lower}",
        f"tr{normalized}",
    }
    return any(v in url_lower for v in variants if v)


def _text_contains_articul(text, articul):
    """Проверяет, что текст содержит артикул в любом распространённом виде."""
    if not text:
        return False
    text_lower = text.lower()
    articul_lower = articul.lower().strip()
    normalized = _normalize_articul(articul)
    variants = {
        articul_lower,
        normalized,
        articul_lower.replace(".", " "),
        articul_lower.replace("-", " "),
        articul_lower.replace("_", " "),
    }
    # Grand Seiko часто пишет артикул без рыночного суффикса G (SBGH201G -> SBGH201).
    if normalized.endswith("g") and len(normalized) >= 5:
        variants.add(normalized[:-1])
    return any(v in text_lower for v in variants if len(v) >= 3)


def _fetch_ru_resolver(name_resolver, brand, articul):
    name, resolver = name_resolver
    if resolver is None:
        return None
    try:
        url = resolver(brand, articul)
        if not url or is_blocked_source(url):
            return None
        text = fetch_page_text(url, timeout=5)
        if not text.startswith("[Ошибка") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
            return url, text
    except Exception:
        return None
    return None


def search_universal_fast_retailers(articul, brand, deadline=None):
    """Быстрый параллельный этап: универсальные ритейлеры для любого бренда.

    Пробуем chrono24, watchfinder, thewatchcompany, 12-24.com, everywatch.com.
    Возвращаем первый успешный результат.
    """
    brand_slug = brand.strip().lower()
    if brand_slug == "bvlgari":
        brand_slug = "bulgari"
    brand_slug_hyphen = brand_slug.replace(" ", "-")
    ref = articul.strip()
    ref_lower = ref.lower()
    ref_upper = ref.upper()
    # 12-24.com использует нормализованный артикул: без / и . и в нижнем регистре
    ref_1224 = ref_lower.replace("/", "-").replace(".", "-")
    # thewatchcompany использует slug без слэшей/точек
    ref_twc = ref_1224
    collection = guess_collection(ref, brand)

    fast_candidates = [
        (f"https://www.chrono24.com/search.htm?query={quote_plus(ref + ' ' + brand)}", 6, False),
        (f"https://www.watchfinder.co.uk/{brand_slug_hyphen}/{ref_upper}/detail", 6, False),
        (f"https://12-24.com/watches/{brand_slug}/ref-{ref_1224}", 6, False),
        (f"https://www.thewatchcompany.com/{brand_slug}-{ref_twc}.html", 6, True),
        (f"https://www.everywatch.com/{brand_slug}-{ref_lower}", 6, False),
        (f"https://www.stablos.com/{brand_slug}-{ref_lower}", 6, False),
    ]
    if collection:
        fast_candidates.insert(
            0,
            (f"https://www.thewatchcompany.com/{brand_slug}-{collection}-{ref_twc}.html", 6, True),
        )

    executor = ThreadPoolExecutor(max_workers=min(6, len(fast_candidates)))
    futures = {executor.submit(fetch_page_text, url, to, 1, stream): (url, to, stream) for url, to, stream in fast_candidates}
    try:
        remaining = min(8, max(1, int(deadline - time.time()))) if deadline else 8
        for future in as_completed(futures, timeout=remaining):
            url, _, _ = futures[future]
            try:
                text = future.result()
                if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                    if not is_blocked_source(url, text):
                        executor.shutdown(wait=False, cancel_futures=True)
                        return url, text
            except Exception:
                continue
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)

    # Fallback: если thewatchcompany таймаутился из-за chunked-передачи,
    # пробуем забрать меньший объём данных потоково с коротким таймаутом.
    twc_url = None
    if collection:
        twc_url = f"https://www.thewatchcompany.com/{brand_slug}-{collection}-{ref_twc}.html"
    else:
        twc_url = f"https://www.thewatchcompany.com/{brand_slug}-{ref_twc}.html"
    text = fetch_page_text(twc_url, timeout=6, retries=1, stream=True, max_bytes=65536)
    if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(twc_url, text, articul, brand):
        if not is_blocked_source(twc_url, text):
            return twc_url, text
    return "", ""


def _fetch_brand_template_url(fn, brand, articul):
    try:
        url = fn(brand, articul)
        if not url or is_blocked_source(url):
            return None
        text = fetch_page_text(url, timeout=6)
        if not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
            return url, text
    except Exception:
        return None
    return None


def search_brand_retailer_templates(articul, brand, deadline=None):
    """Использует проверенные шаблоны ритейлеров для брендов с проблемными официальными сайтами."""
    brand_lower = brand.strip().lower()
    templates = RETAILER_BRAND_TEMPLATES.get(brand_lower, [])
    if not templates:
        return "", ""

    try:
        with ThreadPoolExecutor(max_workers=min(4, len(templates))) as executor:
            futures = [executor.submit(_fetch_brand_template_url, fn, brand, articul) for fn in templates]
            remaining = min(8, max(1, int(deadline - time.time()))) if deadline else 8
            for future in as_completed(futures, timeout=remaining):
                result = future.result()
                if result:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return result
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)
    return "", ""


def search_russian_retailers(articul, brand, deadline=None):
    """Ищет страницы в русскоязычных магазинах через прямые каталоги/поиск (параллельно).

    Если передан deadline — прерываемся, как только время истекает.
    """
    brand_lower = brand.strip().lower()

    resolver_chain = [
        ("alltime.ru", _resolve_alltime_url),
        ("watcheson.ru", _resolve_watcheson_url),
        ("bestwatch.ru", _resolve_bestwatch_url),
    ]
    for host, resolver in RU_RETAILER_RESOLVERS:
        if resolver is None:
            continue
        if host in {"alltime.ru", "watcheson.ru", "bestwatch.ru"}:
            continue
        resolver_chain.append((host, resolver))

    try:
        with ThreadPoolExecutor(max_workers=min(6, len(resolver_chain))) as executor:
            futures = [executor.submit(_fetch_ru_resolver, nr, brand, articul) for nr in resolver_chain]
            remaining = min(8, max(1, int(deadline - time.time()))) if deadline else 8
            for future in as_completed(futures, timeout=remaining):
                result = future.result()
                if result:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return result
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)

    if _deadline_reached(deadline):
        return "", ""

    # Fallback на поисковые движки с site-запросами — только крупные магазины.
    norm = _normalize_articul(articul)
    ru_domains = [
        "alltime.ru", "watcheson.ru", "bestwatch.ru", "aswatch.ru",
    ]
    queries = [f"{brand} {norm} site:{d}" for d in ru_domains]
    queries += [f"{brand} {articul} site:{d}" for d in ru_domains]

    for query in queries:
        if _deadline_reached(deadline):
            break
        urls = _search_ru(query, num_results=2)
        # Сначала URL с артикулом
        for url in urls:
            if not url.startswith("http") or url.startswith("["):
                continue
            if is_blocked_source(url):
                continue
            if not _url_contains_articul(url, articul):
                continue
            text = fetch_page_text(url, timeout=5)
            if not text.startswith("[Ошибка") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                return url, text
        # Fallback: любой URL
        for url in urls:
            if not url.startswith("http") or url.startswith("["):
                continue
            if is_blocked_source(url):
                continue
            text = fetch_page_text(url, timeout=5)
            if not text.startswith("[Ошибка") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                return url, text
    return "", ""


def search_retailer_pages(articul, brand, deadline=None):
    """Ищет страницы крупных ритейлеров и профильных площадок через поиск (параллельно)."""
    articul_clean = articul.strip().upper()
    brand_title = brand.strip().title()
    queries = [
        f"{brand_title} {articul_clean} site:chrono24.com",
        f"{brand_title} {articul_clean} site:hodinkee.com",
        f"{brand_title} {articul_clean} site:monochrome-watches.com",
        f"{brand_title} {articul_clean} site:timeandtidewatches.com",
        f"{brand_title} {articul_clean} site:everywatch.com",
        f"{brand_title} {articul_clean} site:thewatchcompany.com",
    ]

    def fetch_query(query):
        urls = _search_all(query, num_results=2)
        for url in urls:
            if not url.startswith("http") or url.startswith("["):
                continue
            text = fetch_page_text(url, timeout=5)
            if not text.startswith("[Ошибка") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                return url, text
        return None

    try:
        with ThreadPoolExecutor(max_workers=min(3, len(queries))) as executor:
            futures = [executor.submit(fetch_query, q) for q in queries]
            remaining = min(8, max(1, int(deadline - time.time()))) if deadline else 8
            for future in as_completed(futures, timeout=remaining):
                result = future.result()
                if result:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return result
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)
    return "", ""


def _fetch_direct_official(brand, articul):
    """Прямая загрузка официального сайта с вариантами локали (requests)."""
    urls = get_official_url_candidates(brand, articul)
    if not urls:
        return None

    # Для Grand Seiko стартовая локаль global-en часто отдаёт 404,
    # поэтому сначала пробуем приоритетные au-en / uk-en / sg-en.
    priority_locales = {"au-en", "uk-en", "sg-en"}

    def _priority(url):
        lower = url.lower()
        for loc in priority_locales:
            if f"/{loc}/" in lower:
                return 0
        return 1

    urls = sorted(urls[:16], key=_priority)

    try:
        with ThreadPoolExecutor(max_workers=min(6, len(urls))) as executor:
            futures = {executor.submit(fetch_page_text, url, 5, 0): url for url in urls}
            for future in as_completed(futures, timeout=10):
                try:
                    text = future.result()
                    url = futures[future]
                    if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                        if not is_blocked_source(url, text):
                            executor.shutdown(wait=False, cancel_futures=True)
                            return url, text, get_source_tier(url)
                except Exception:
                    continue
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)
    return None


def _fetch_direct_official_js(brand, articul, deadline=None):
    """Playwright-рендеринг официальных кандидатов, если requests не справился."""
    if not PLAYWRIGHT_AVAILABLE:
        return None
    urls = get_official_url_candidates(brand, articul)
    official_urls = [u for u in urls if _is_official_domain(u, brand)][:2]
    if not official_urls:
        return None

    for url in official_urls:
        if _deadline_reached(deadline):
            break
        text = fetch_page_text(url, timeout=8, use_js=True)
        if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
            if not is_blocked_source(url, text):
                return url, text, get_source_tier(url)
    return None


def search_chrono24_model(brand, articul, deadline=None):
    """Ищет прямую карточку модели на chrono24.com по артикулу.

    Chrono24 выдаёт страницу поиска; внутри неё есть ссылки на конкретные
    лоты. Мы берём первый лот, в URL/тексте которого есть артикул, и
    возвращаем текст его карточки. На карточке обычно есть полные спеки.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return "", ""

    # Примерные manufacturerIds Chrono24 для популярных брендов.
    chrono24_brand_ids = {
        "breitling": "32",
        "omega": "121",
        "rolex": "171",
        "tag heuer": "191",
        "iwc": "103",
        "cartier": "41",
        "tudor": "201",
        "panerai": "148",
        "longines": "114",
        "zenith": "221",
        "patek philippe": "150",
        "audemars piguet": "18",
        "vacheron constantin": "211",
        "jaeger-lecoultre": "105",
        "hublot": "91",
        "ulysse nardin": "207",
        "grand seiko": "81",
        "oris": "141",
        "rado": "167",
        "hamilton": "85",
        "mido": "127",
        "certina": "43",
        "tissot": "197",
        "bulova": "37",
        "citizen": "48",
        "seiko": "179",
    }

    brand_lower = brand.strip().lower()
    brand_id = chrono24_brand_ids.get(brand_lower, "")
    ref = articul.strip().upper()
    ref_normalized = re.sub(r"[^A-Z0-9]", "", ref)

    # Chrono24 лучше ищет по короткому референсу (первые 6–8 символов).
    search_terms = []
    if len(ref_normalized) >= 6:
        search_terms.append(ref_normalized[:6])
        search_terms.append(ref_normalized[:8])
    search_terms.append(ref)

    for term in search_terms:
        if _deadline_reached(deadline):
            return "", ""
        brand_param = f"&manufacturerIds={brand_id}" if brand_id else ""
        search_url = (
            f"https://www.chrono24.com/search/index.htm?"
            f"query={quote_plus(term)}{brand_param}"
            f"&currencyId=USD&sortorder=0&pageSize=60&dosearch=true"
        )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENT_VARIANTS),
                    locale="en-US",
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                page = context.new_page()
                page.goto(search_url, wait_until="networkidle", timeout=35000)
                time.sleep(2.0)

                product_links = []
                for a in page.locator("a").all():
                    try:
                        href = a.get_attribute("href") or ""
                        text = (a.inner_text() or "").strip()
                    except Exception:
                        continue
                    if "/watch/" not in href and "/breitling/" not in href.lower():
                        continue
                    if href.startswith("/"):
                        url = "https://www.chrono24.com" + href
                    elif href.startswith("https://www.chrono24.com"):
                        url = href
                    else:
                        continue
                    if url in product_links:
                        continue
                    # Принимаем ссылки, в которых есть либо полный артикул,
                    # либо короткий поисковый терм (AB2020 и т.п.).
                    if (
                        _url_contains_articul(url, articul)
                        or _text_contains_articul(text, articul)
                        or term.upper().replace("-", "") in (url + " " + text).upper().replace("-", "")
                    ):
                        product_links.append(url)
                    if len(product_links) >= 5:
                        break

                for url in product_links:
                    if _deadline_reached(deadline):
                        break
                    text = _fetch_page_text_js(url, timeout=15)
                    if text and not text.startswith("[") and len(text) > 400:
                        # На странице лота должен быть полный артикул или бренд+модель.
                        if _source_matches_request(url, text, articul, brand) or _text_contains_articul(text, articul):
                            if not is_blocked_source(url, text):
                                browser.close()
                                return url, text

                # Если карточки лотов заблокированы или не содержат полный артикул,
                # используем текст страницы поиска как fallback.
                search_text = page.inner_text("body")
                if search_text and len(search_text.strip()) > 500 and _text_contains_brand(search_text, brand):
                    cleaned = _clean_page_text(search_text)
                    if not is_blocked_source(search_url, cleaned):
                        browser.close()
                        return search_url, cleaned

                browser.close()
        except Exception:
            continue
    return "", ""


def search_breitling_official(articul, brand, deadline=None):
    """Ищет карточку конкретной модели на breitling.com.

    Breitling использует slug коллекции в URL, а не артикул. Поэтому
    перебираем страницы всех известных коллекций бренда через Playwright,
    находим ссылку, в тексте которой есть артикул, и забираем текст карточки модели.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return "", ""

    from brand_urls import BRAND_COLLECTION_GUESSES

    brand_lower = brand.strip().lower()
    collections = BRAND_COLLECTION_GUESSES.get(brand_lower, [])
    if not collections:
        return "", ""

    # Первой проверяем коллекцию, угаданную по префиксу.
    from brand_urls import guess_collection
    guessed = guess_collection(articul, brand)
    if guessed and guessed not in collections:
        collections = [guessed] + list(collections)
    elif guessed:
        collections = [guessed] + [c for c in collections if c != guessed]

    articul_variants = {
        articul.upper().strip(),
        articul.upper().strip().replace("-", ""),
        articul.upper().strip().replace(".", ""),
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENT_VARIANTS),
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = context.new_page()
            # Блокируем тяжёлые ресурсы, чтобы ускорить загрузку страниц Breitling.
            page.route(
                re.compile(r".*\.(png|jpg|jpeg|webp|gif|svg|ico|css|woff|woff2|ttf|js)$"),
                lambda route: route.abort(),
            )

            product_url = None
            # Сначала пробуем угаданную коллекцию с коротким таймаутом;
            # если не нашли — fallback на остальные известные коллекции.
            for collection in collections[:6]:
                if _deadline_reached(deadline):
                    break
                coll_url = f"https://www.breitling.com/us-en/watches/{collection}/"
                try:
                    page.goto(coll_url, wait_until="domcontentloaded", timeout=12000)
                    time.sleep(0.6)
                    links = page.locator("a").all()
                    for a in links:
                        try:
                            href = a.get_attribute("href") or ""
                            text = (a.inner_text() or "").upper().replace(" ", "")
                        except Exception:
                            continue
                        clean_href = href.upper().replace("-", "").replace(".", "")
                        if any(v.replace("-", "").replace(".", "") in text for v in articul_variants):
                            if href.startswith("/"):
                                product_url = f"https://www.breitling.com{href}"
                            elif href.startswith("http"):
                                product_url = href
                            break
                        if any(v.replace("-", "").replace(".", "") in clean_href for v in articul_variants):
                            if href.startswith("/"):
                                product_url = f"https://www.breitling.com{href}"
                            elif href.startswith("http"):
                                product_url = href
                            break
                    if product_url:
                        break
                except Exception:
                    continue

            if not product_url:
                browser.close()
                return "", ""

            try:
                page.goto(product_url, wait_until="domcontentloaded", timeout=12000)
                time.sleep(0.5)
                body_text = page.inner_text("body")
                browser.close()
                if body_text and len(body_text.strip()) > 300:
                    cleaned = _clean_page_text(body_text)
                    return product_url, cleaned
            except Exception:
                browser.close()
                return "", ""
    except Exception:
        return "", ""
    return "", ""


def search_review_sources(articul, brand, deadline=None):
    """Ищет обзоры на профильных медиа: Hodinkee, Monochrome, Revolution, Time+Tide.

    Используем как fallback для премиальных брендов, где официальные сайты
    часто не отдают технические спеки или блокируют requests.
    """
    brand_title = brand.strip().title()
    ref = articul.strip().upper()
    queries = [
        f"{brand_title} {ref} site:hodinkee.com",
        f"{brand_title} {ref} site:monochrome-watches.com",
        f"{brand_title} {ref} site:revolution.watch",
        f"{brand_title} {ref} site:thewatchobserver.com",
        f"{brand_title} {ref} site:timeandtidewatches.com",
        f"{brand_title} {ref} site:fratellowatches.com",
    ]

    def fetch_query(query):
        urls = _search_all(query, num_results=2)
        for url in urls:
            if not url.startswith("http") or url.startswith("["):
                continue
            text = fetch_page_text(url, timeout=6)
            if not text.startswith("[") and len(text) > 300 and _source_matches_request(url, text, articul, brand):
                if not is_blocked_source(url, text):
                    return url, text
        return None

    try:
        with ThreadPoolExecutor(max_workers=min(3, len(queries))) as executor:
            futures = [executor.submit(fetch_query, q) for q in queries]
            remaining = min(12, max(1, int(deadline - time.time()))) if deadline else 12
            for future in as_completed(futures, timeout=remaining):
                result = future.result()
                if result:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return result
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)
    return "", ""


def _fetch_universal_official(brand, articul):
    """Перебирает универсальные URL официальных сайтов для неизвестных брендов."""
    urls = guess_universal_urls(brand, articul)
    seen = set()
    try:
        with ThreadPoolExecutor(max_workers=min(4, len(urls))) as executor:
            futures = [executor.submit(fetch_page_text, url, 5, 1) for url in urls]
            for future in as_completed(futures, timeout=10):
                try:
                    text = future.result()
                    url = urls[futures.index(future)]
                    if text and not text.startswith("[") and len(text) > 200 and _source_matches_request(url, text, articul, brand):
                        if url not in seen and not is_blocked_source(url, text):
                            seen.add(url)
                            return url, text, get_source_tier(url)
                except Exception:
                    continue
    except TimeoutError:
        pass
    return None


def _deadline_reached(deadline):
    return deadline is not None and time.time() > deadline


def _source_matches_request(url, text, articul, brand):
    """True, если источник явно относится к запрошенному бренду и артикулу.

    Проверяем только текст страницы: в нём должен быть и артикул, и бренд.
    URL-проверка намеренно не используется, потому что поисковики и ритейлеры
    часто возвращают редиректы/алиасы, а текст страницы достовернее.
    """
    if not _text_contains_articul(text, articul):
        return False
    if not _text_contains_brand(text, brand):
        return False
    return True


# Вес спек-меток для оценки полноты источника.
_SPEC_KEYWORDS = [
    "calibre", "caliber", "movement", "jewels", "frequency", "power reserve",
    "case size", "case material", "bracelet", "strap", "dial", "water resistance",
    "калибр", "механизм", "камни", "полуколебания", "запас хода", "корпус",
    "браслет", "ремешок", "стекло", "циферблат", "водозащита", "водонепроницаем",
    "диаметр", "толщина", "страна", "производство", "sapphire", "автоподзавод",
]


def _score_source_text(text):
    """Оценивает полноту технического текста по числу спек-меток."""
    if not text:
        return 0
    text_lower = text.lower()
    return sum(1 for kw in _SPEC_KEYWORDS if kw in text_lower)


def _extract_stage1_candidate(name, result, articul, brand):
    """Превращает результат одного из stage1-источников в (tier, url, text) или None."""
    if not result:
        return None
    # Официальные fetch-функции возвращают (url, text, tier), а общий
    # fast-fallback — (tier, url, text). Приводим к единому виду.
    if name in ("official", "universal_official", "general"):
        if name == "general":
            tier, url, text = result
        else:
            url, text, tier = result
        if text and isinstance(text, str) and not text.startswith("[Ошибка") and not is_blocked_source(url, text):
            if _text_contains_articul(text, articul) and _text_contains_brand(text, brand):
                return (tier, url, text)
    else:
        url, text = result
        if url and text and isinstance(text, str) and not text.startswith("[Ошибка") and not is_blocked_source(url, text):
            # Для Chrono24 и некоторых официальных коллекций страница поиска/каталога
            # может содержать базовый референс, а не полный артикул. Проверяем бренд
            # и совпадение по базовому префиксу артикула.
            if _source_matches_request(url, text, articul, brand):
                tier = get_source_tier(url)
                return (tier, url, text)
            if name in ("chrono24_model", "breitling_official") and _text_contains_brand(text, brand):
                # Для Breitling используем 6-символьный базовый референс (AB2020...).
                base = re.sub(r"[^A-Z0-9]", "", articul.upper())[:6]
                if len(base) >= 4 and base in (url + text).upper():
                    tier = get_source_tier(url)
                    return (tier, url, text)
    return None


def find_official_page(articul, brand):
    """Ищет источник характеристик и возвращает (URL, текст, tier).

    Общий лимит по времени — SEARCH_OVERALL_TIMEOUT секунд. После его истечения
    возвращаем лучший найденный результат или пустоту, чтобы не держать
    пользователя десятки секунд.
    """
    brand_lower = brand.strip().lower()
    deadline = time.time() + SEARCH_OVERALL_TIMEOUT

    cached = get_cached_search(articul, brand)
    if cached:
        return cached

    # 1. Параллельный первый этап: официальный сайт + дилеры + ритейлеры +
    # быстрый общий поиск + специализированные базы (thewatchpages, watchbase).
    # Общий поиск идёт сразу, чтобы не ждать, пока официальные сайты или
    # thewatchcompany отвалятся по таймауту.
    results = {}
    executor = ThreadPoolExecutor(max_workers=10)
    future_to_name = {
        executor.submit(_fetch_direct_official, brand, articul): "official",
        executor.submit(_fetch_universal_official, brand, articul): "universal_official",
        executor.submit(search_dealer_pages, articul, brand): "dealer",
        executor.submit(search_universal_fast_retailers, articul, brand, deadline): "fast_retailer",
        executor.submit(_search_fast_fallback, brand, articul, deadline): "general",
        executor.submit(search_thewatchpages, articul, brand, deadline): "thewatchpages",
        executor.submit(search_watchbase_page, brand, articul, deadline): "watchbase_page",
        executor.submit(search_chronomaster, brand, articul, deadline): "chronomaster",
        executor.submit(search_russian_retailers, articul, brand, deadline): "ru_retailers",
        executor.submit(search_brand_retailer_templates, articul, brand, deadline): "brand_templates",
        executor.submit(search_chrono24_model, brand, articul, deadline): "chrono24_model",
        executor.submit(search_review_sources, articul, brand, deadline): "review_sources",
        executor.submit(search_breitling_official, articul, brand, deadline): "breitling_official",
    }
    try:
        for future in as_completed(future_to_name, timeout=min(24, SEARCH_OVERALL_TIMEOUT)):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = None
    except TimeoutError:
        pass
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False, cancel_futures=True)

    # Собираем всех кандидатов и выбираем лучшего по совокупности tier и полноты текста.
    candidates = []
    for name, result in results.items():
        candidate = _extract_stage1_candidate(name, result, articul, brand)
        if candidate:
            candidates.append(candidate)

    if candidates:
        # tier — главный критерий; при равных tier выбираем источник с большим числом спек-меток.
        candidates.sort(key=lambda x: (x[0], -_score_source_text(x[2])))
        tier, url, text = candidates[0]
        if not is_blocked_source(url, text):
            set_cached_search(articul, brand, url, text, tier)
            return url, text, tier

    print(f"[DEBUG {brand} {articul}] stage1 no candidate, results: { {k: (v[0] if isinstance(v, tuple) else None) for k, v in results.items()} }")

    if _deadline_reached(deadline):
        return "", "", None

    # 2. Специальная логика для Cartier
    if brand_lower == "cartier":
        cartier_url, cartier_text, collection = search_cartier_official(articul, brand)
        if cartier_url:
            tier = get_source_tier(cartier_url)
            if not is_blocked_source(cartier_url, cartier_text):
                set_cached_search(articul, brand, cartier_url, cartier_text, tier)
                return cartier_url, cartier_text, tier
        if collection:
            rebuilt_url = get_official_url(brand, articul, collection=collection)
            if rebuilt_url:
                text = fetch_page_text_with_js_fallback(rebuilt_url, timeout=10, brand=brand)
                if not text.startswith("["):
                    tier = get_source_tier(rebuilt_url)
                    if not is_blocked_source(rebuilt_url, text):
                        set_cached_search(articul, brand, rebuilt_url, text, tier)
                        return rebuilt_url, text, tier

    if _deadline_reached(deadline):
        return "", "", None

    # Быстрые источники исчерпаны. Дальнейшие этапы (профильные ритейлеры,
    # JS-рендеринг, русскоязычные площадки) редко дают результат, но сильно
    # увеличивают время поиска, поэтому возвращаем пустоту, не тратя лишние
    # секунды на таймауты.
    return "", "", None


def _is_known_luxury_brand(brand_lower):
    """Возвращает True, если бренд есть в нашем списке официальных шаблонов."""
    return brand_lower in {
        "tudor", "rolex", "omega", "cartier", "iwc", "zenith", "breitling", "tag heuer"
    }
