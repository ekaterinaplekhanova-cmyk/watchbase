"""Поиск по изображению для идентификации часов.

Реализован бесплатный обратный поиск через Yandex Images.
Опционально — Bing Visual Search API, если задан ключ BING_SEARCH_API_KEY.
"""

import io
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image

from retailers import get_source_tier, is_blocked_source
from search import _is_valid_source_url, fetch_page_text

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}

YANDEX_IMAGE_ENDPOINT = "https://yandex.ru/images/search"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".avif"}

YANDEX_HOSTS = {
    "yandex.ru",
    "yandex.com",
    "yandex.by",
    "yandex.kz",
    "yandex.ua",
    "yastatic.net",
    "avatars.mds.yandex.net",
    "static.yandex.net",
    "mc.yandex.ru",
}


def _prepare_image(image_path, max_size=(1400, 1400), quality=85, max_bytes=1_000_000):
    """Открывает локальное изображение, при необходимости уменьшает и конвертирует в JPEG."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = Image.open(path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size, Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    data = buffer.getvalue()

    while len(data) > max_bytes and quality > 40:
        quality -= 10
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        data = buffer.getvalue()

    return data, path.name, "image/jpeg"


def _is_image_url(url):
    """True, если URL явно ведёт на файл изображения."""
    if not url:
        return True
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS) or "/images/search?" in url


def _extract_source_url_from_yandex_href(href):
    """Из Yandex-редиректа достаёт реальный URL источника (img_url)."""
    if not href:
        return None
    try:
        qs = href.split("?", 1)[1] if "?" in href else ""
        parsed = parse_qs(qs)
        return parsed.get("img_url", [None])[0]
    except Exception:
        return None


def _yandex_result_url(data):
    """Строит URL страницы результатов из JSON-ответа Yandex."""
    params = data.get("blocks", [{}])[0].get("params", {})
    # Современный ответ содержит ссылку на загруженное изображение.
    original_url = params.get("originalImageUrl")
    if original_url:
        return f"{YANDEX_IMAGE_ENDPOINT}?source=collection&rpt=imageview&url={original_url}"
    # Fallback на старый формат.
    query_url = params.get("url")
    if query_url:
        return f"{YANDEX_IMAGE_ENDPOINT}?{query_url}"
    cbir_id = params.get("cbirId")
    if cbir_id:
        return f"{YANDEX_IMAGE_ENDPOINT}?rpt=imageview&cbirid={cbir_id}"
    return None


def _parse_yandex_result_page(html, max_results=20):
    """Парсит страницу результатов Yandex Images и возвращает список внешних источников."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    def add(url, title):
        if not url or not url.startswith("http"):
            return
        # protocol-relative ссылки
        if url.startswith("//"):
            url = "https:" + url
        parsed = urlparse(url)
        host = parsed.netloc.lower().lstrip("www.")
        if any(host == yh or host.endswith(f".{yh}") for yh in YANDEX_HOSTS):
            return
        if _is_image_url(url):
            return
        if not _is_valid_source_url(url):
            return
        if is_blocked_source(url):
            return
        if url in seen:
            return
        seen.add(url)
        results.append({"title": title or "", "url": url})

    # Вариант 1: внутренние редиректы Yandex, в которых спрятан img_url
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        source_url = _extract_source_url_from_yandex_href(href)
        if source_url:
            add(source_url, a.get_text(strip=True))
        elif href.startswith("http"):
            add(href, a.get_text(strip=True))
        elif href.startswith("//"):
            add(href, a.get_text(strip=True))

    return results[:max_results]


def yandex_reverse_search(image_path, max_results=10):
    """Загружает изображение в Yandex Images и возвращает список найденных источников.

    Каждый элемент:
        {"title": str, "url": str}
    """
    image_data, filename, mime = _prepare_image(image_path)

    files = {
        "upfile": ("blob", io.BytesIO(image_data), mime),
    }
    params = {
        "rpt": "imageview",
        "format": "json",
        "request": '{"blocks":[{"block":"b-page_type_search-by-image__link"}]}',
    }

    try:
        r = requests.post(
            YANDEX_IMAGE_ENDPOINT,
            params=params,
            files=files,
            headers=DEFAULT_HEADERS,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [{"error": f"Yandex upload failed: {e}"}]

    result_url = _yandex_result_url(data)
    if not result_url:
        return [{"error": "Yandex returned unexpected JSON: " + json.dumps(data, ensure_ascii=False)[:200]}]

    try:
        r2 = requests.get(result_url, headers=DEFAULT_HEADERS, timeout=60)
        r2.raise_for_status()
    except Exception as e:
        return [{"error": f"Yandex results page failed: {e}"}]

    results = _parse_yandex_result_page(r2.text, max_results=max_results)
    if not results:
        return [{"error": "Yandex returned results page, but no external sources found."}]
    return results


def yandex_reverse_search_by_url(image_url, max_results=10):
    """Обратный поиск по уже опубликованному URL изображения."""
    try:
        params = {
            "source": "collection",
            "rpt": "imageview",
            "url": image_url,
        }
        r = requests.get(
            YANDEX_IMAGE_ENDPOINT,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=60,
            allow_redirects=True,
        )
        r.raise_for_status()
    except Exception as e:
        return [{"error": f"Yandex by-url search failed: {e}"}]

    results = _parse_yandex_result_page(r.text, max_results=max_results)
    if not results:
        return [{"error": "Yandex by-url search returned no external sources."}]
    return results


def bing_visual_search(image_path, api_key=None):
    """Bing Visual Search API (требуется ключ). Возвращает список source-объектов."""
    key = api_key or os.getenv("BING_SEARCH_API_KEY")
    if not key:
        return []

    endpoint = "https://api.bing.microsoft.com/v7.0/images/visualsearch"
    headers = {"Ocp-Apim-Subscription-Key": key}

    image_data, filename, mime = _prepare_image(image_path)
    files = {"image": (filename, io.BytesIO(image_data), mime)}

    try:
        r = requests.post(endpoint, headers=headers, files=files, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [{"error": f"Bing Visual Search failed: {e}"}]

    results = []
    tags = data.get("tags", [])
    for tag in tags:
        actions = tag.get("actions", [])
        for action in actions:
            action_type = action.get("actionType", "")
            if action_type not in ("VisualSearch", "PagesIncluding"):
                continue
            for item in action.get("data", {}).get("value", []):
                url = item.get("contentUrl") or item.get("hostPageUrl")
                if url:
                    results.append({
                        "title": item.get("name", ""),
                        "url": url,
                        "snippet": item.get("description", ""),
                    })
    return results


def collect_image_context(image_path, max_pages=5, prefer_trusted=True):
    """Возвращает список (url, text, tier) по загруженному фото.

    Для каждого найденного источника загружает текст страницы и фильтрует
    подделки/маркетплейсы. Сортирует по уровню доверия (официальный → авторизованный
    → авторитетный → неизвестный) и возвращает не более max_pages.
    """
    results = yandex_reverse_search(image_path, max_results=20)
    if not results or any("error" in r for r in results):
        return results if results else [{"error": "Yandex image search returned no results."}]

    pages = []
    for res in results:
        url = res.get("url")
        if not url or not url.startswith("http"):
            continue
        if is_blocked_source(url):
            continue
        if not _is_valid_source_url(url):
            continue

        text = fetch_page_text(url, timeout=15, retries=1)
        if text.startswith("[Ошибка") or len(text) < 200:
            continue
        if is_blocked_source(url, text):
            continue

        tier = get_source_tier(url)
        pages.append((url, text, tier))

    if prefer_trusted:
        pages.sort(key=lambda x: x[2])

    return pages[:max_pages]


def identify_watch_from_image(image_path):
    """Пытается определить бренд/модель по фото через image search + LLM."""
    results = yandex_reverse_search(image_path)
    if not results or any("error" in r for r in results):
        return results

    texts = []
    for r in results[:10]:
        texts.append(f"{r.get('title', '')} {r.get('url', '')}")
    return {"results": results, "combined_text": "\n".join(texts)}
