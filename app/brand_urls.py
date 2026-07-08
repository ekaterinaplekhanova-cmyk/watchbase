"""Шаблоны URL официальных страниц для известных брендов."""

import re
from urllib.parse import urlparse


BRAND_TEMPLATES = {
    "tudor": lambda brand, collection, articul: f"https://www.tudorwatch.com/en/watches/tudor-{collection.lower()}/{articul.lower()}" if collection else f"https://www.tudorwatch.com/en/watches/{articul.lower()}",
    "rolex": lambda brand, collection, articul: f"https://www.rolex.com/watches/{collection.lower()}/{articul.lower()}.html",
    "cartier": lambda brand, collection, articul: _cartier_url(collection, articul),
    "traser": lambda brand, collection, articul: f"https://www.traser.com/en/product/{articul.lower()}",
    "panerai": lambda brand, collection, articul: f"https://www.panerai.com/en-us/collections/{collection.lower().replace(' ', '-')}/{articul.lower()}.html",
    "luminox": lambda brand, collection, articul: f"https://www.luminox.com/products/{articul.lower()}",
    "ball": lambda brand, collection, articul: f"https://www.ballwatch.com/global/1/collections/{collection.lower().replace(' ', '-')}/eternity---{articul.lower()}---2431.html",
    "baume & mercier": lambda brand, collection, articul: f"https://www.baume-et-mercier.com/en-us/watches/{collection.lower().replace(' ', '-')}/{articul}.html",
    "bell & ross": lambda brand, collection, articul: f"https://bellross.com/en-uk/products/{articul.lower()}",
    "frederique constant": lambda brand, collection, articul: f"https://www.frederiqueconstant.com/shop/{articul}/",
    "maurice lacroix": lambda brand, collection, articul: f"https://www.mauricelacroix.com/en/watches/{collection.lower().replace(' ', '-')}/{articul}",
    "oris": lambda brand, collection, articul: f"https://www.oris.ch/en/watch/{articul}",
    "ulysse nardin": lambda brand, collection, articul: f"https://www.ulysse-nardin.com/en-en/{articul}.html",
    "franck muller": lambda brand, collection, articul: f"https://www.franckmuller.com/en/collection/{collection.lower().replace(' ', '-')}/{articul}",
    "roger dubuis": lambda brand, collection, articul: f"https://www.rogerdubuis.com/en-en/watches/{collection.lower().replace(' ', '-')}/{articul}",
    "parmigiani": lambda brand, collection, articul: f"https://www.parmigiani.com/en/watch/{articul}",
    "de grisogono": lambda brand, collection, articul: f"https://www.degrisogono.com/en/watches/{articul}",
    "clerc": lambda brand, collection, articul: f"https://www.clercwatches.com/en/watches/{articul}",
    "ebel": lambda brand, collection, articul: f"https://www.ebel.com/en-us/watches/{articul}.html",
    "edox": lambda brand, collection, articul: f"https://www.edox.ch/en/watches/{articul}",
    "epos": lambda brand, collection, articul: f"https://www.eposwatches.com/en/watches/{articul}.html",
    "dior": lambda brand, collection, articul: f"https://www.dior.com/en_int/products/{articul}.html",
    "hermes": lambda brand, collection, articul: f"https://www.hermes.com/us/en/product/{articul}",
    "louis vuitton": lambda brand, collection, articul: f"https://www.louisvuitton.com/eng-us/products/{articul}",
    "montblanc": lambda brand, collection, articul: f"https://www.montblanc.com/en-us/watches/{collection.lower().replace(' ', '-')}/{articul}.html",
    "bovet": lambda brand, collection, articul: f"https://www.bovet.com/en/watch/{articul}",
    "jacob & co": lambda brand, collection, articul: f"https://www.jacobandco.com/timepieces/{articul}",
    "perrelet": lambda brand, collection, articul: f"https://www.perrelet.com/en/watches/{articul}",
    "graham": lambda brand, collection, articul: f"https://www.graham1695.com/en/watches/{articul}",
    "squale": lambda brand, collection, articul: f"https://www.squale.ch/en/watches/{articul}",
    "steinhart": lambda brand, collection, articul: f"https://www.steinhartwatches.de/en/{articul}.html",
    "u-boat": lambda brand, collection, articul: f"https://www.u-boat.it/en/watches/{articul}.html",
    "romain jerome": lambda brand, collection, articul: f"https://www.romainjerome.ch/en/watches/{articul}",
    "schwarz-etienne": lambda brand, collection, articul: f"https://www.schwarz-etienne.com/en/watches/{articul}",
    "jeanrichard": lambda brand, collection, articul: f"https://www.jeanrichard.com/en/watches/{articul}",
    "juvenia": lambda brand, collection, articul: f"https://www.juvenia.ch/en/watches/{articul}",
    "armand nicolet": lambda brand, collection, articul: f"https://www.armandnicolet.com/product-page/{articul.lower()}",
    "auguste reymond": lambda brand, collection, articul: f"https://augustereymond.ch/watch/{articul.lower()}/",
    "aerowatch": lambda brand, collection, articul: f"https://www.aerowatch.ch/en/product/{articul.lower()}",
    "boegli": lambda brand, collection, articul: f"https://www.boegli.ch/en/watches/{articul}",
    "bomberg": lambda brand, collection, articul: f"https://www.bomberg.com/en/watches/{articul}",
    "briller": lambda brand, collection, articul: f"https://www.briller.com/en/watches/{articul}",
    "alain silberstein": lambda brand, collection, articul: f"https://www.alainsilberstein.com/en/watches/{articul}",
    "charmex": lambda brand, collection, articul: f"https://www.charmex.ch/en/watches/{articul}",
    "icelink": lambda brand, collection, articul: f"https://www.icelink.com/en/watches/{articul}",
    "paul picot": lambda brand, collection, articul: f"https://www.paulpicot.com/en/watches/{articul}",
    "rebellion": lambda brand, collection, articul: f"https://www.rebellion-timepieces.com/en/watches/{articul}",
    "bernhard h. mayer": lambda brand, collection, articul: f"https://www.bernhardhmayer.com/en/watches/{articul}",
    "w.gabus": lambda brand, collection, articul: f"https://www.wgabus.com/en/watches/{articul}",
    "van der bauwede": lambda brand, collection, articul: f"https://www.vanderbauwede.com/en/watches/{articul}",
    "tsedro": lambda brand, collection, articul: f"https://www.tsedro.com/en/watches/{articul}",
    "luxewood": lambda brand, collection, articul: f"https://www.luxewood.com/en/watches/{articul}",
    "swatch": lambda brand, collection, articul: f"https://www.swatch.com/en-us/watches/{articul}.html",
    "alpina": lambda brand, collection, articul: f"https://www.alpinawatches.com/en/watches/{articul.lower()}",
    "union glashutte": lambda brand, collection, articul: f"https://www.union-glashuette.com/en/watches/{articul.lower()}",
    "union glashütte": lambda brand, collection, articul: f"https://www.union-glashuette.com/en/watches/{articul.lower()}",
    "grand seiko": lambda brand, collection, articul: f"https://www.grand-seiko.com/au-en/collections/{articul.lower().replace('/', '-')}",
    "breitling": lambda brand, collection, articul: f"https://www.breitling.com/us-en/watches/{collection.lower().replace(' ', '-')}/",
}


# Альтернативные пути для брендов, где официальный сайт меняет структуру URL
# в зависимости от локали или коллекции.
BRAND_EXTRA_PATTERNS = {
    "tudor": lambda b, c, a: [
        f"https://www.tudorwatch.com/en/watches/{c.lower()}/{a.lower()}" if c else None,
    ],
    # IWC/Omega/Tag Heuer/Breitling/Piaget часто блокируют requests или меняют
    # структуру URL (нужен slug названия модели), поэтому для них полагаемся
    # на поисковые движки и авторизованных ритейлеров.
    "bvlgari": lambda b, c, a: [
        f"https://www.bvlgari.com/en-gb/products/{a.lower()}.html",
        f"https://www.bvlgari.com/en-int/products/{a.lower()}.html",
    ],
    "audemars piguet": lambda b, c, a: [
        f"https://www.audemarspiguet.com/com/en/watches/{c.lower().replace(' ', '-')}/{a}.html" if c else None,
    ],
    "longines": lambda b, c, a: [
        f"https://www.longines.com/en-gb/watch/{a.lower()}",
    ],
    "rado": lambda b, c, a: [
        f"https://www.rado.com/en-gb/watches/{a}.html",
    ],
    "hamilton": lambda b, c, a: [
        f"https://www.hamiltonwatch.com/en-gb/{a}.html",
    ],
    "mido": lambda b, c, a: [
        f"https://www.midowatches.com/en-gb/{a}.html",
    ],
    "certina": lambda b, c, a: [
        f"https://www.certina.com/en-gb/{a}.html",
    ],
    "tissot": lambda b, c, a: [
        f"https://www.tissotwatches.com/en-gb/{a}.html",
    ],
    "grand seiko": lambda b, c, a: [
        f"https://www.grand-seiko.com/au-en/collections/{a.lower().replace('/', '-')}",
        f"https://www.grand-seiko.com/uk-en/collections/{a.lower().replace('/', '-')}",
        f"https://www.grand-seiko.com/sg-en/collections/{a.lower().replace('/', '-')}",
    ],
    "breitling": lambda b, c, a: [
        f"https://www.breitling.com/us-en/watches/{c.lower().replace(' ', '-')}/" if c else None,
        f"https://www.breitling.com/us-en/watches/{c.lower().replace(' ', '-')}/?search={a}" if c else None,
    ],
    "seiko": lambda b, c, a: [
        f"https://www.seikowatches.com/uk-en/products/{a}/index",
    ],
    "bulova": lambda b, c, a: [
        f"https://www.bulova.com/uk/en/catalog/product/{a}.html",
    ],
    "citizen": lambda b, c, a: [
        f"https://www.citizenwatch.com/uk/en/product/{a}.html",
    ],
    "baume & mercier": lambda b, c, a: [
        f"https://www.baume-et-mercier.com/en-gb/watches/{c.lower().replace(' ', '-')}/{a}.html" if c else None,
    ],
    "panerai": lambda b, c, a: [
        f"https://www.panerai.com/en-gb/collections/{c.lower().replace(' ', '-')}/{a.lower()}.html" if c else None,
    ],
    "ball": lambda b, c, a: [
        f"https://www.ballwatch.com/global/1/collections/{c.lower().replace(' ', '-')}/{a}" if c else None,
        f"https://www.ballwatch.com/en/watches/{a}",
    ],
    "bell & ross": lambda b, c, a: [
        f"https://www.bellross.com/en-us/products/{a.lower()}",
    ],
    "cartier": lambda b, c, a: [
        _cartier_url(c, a).replace("/en-gb/", "/en-us/") if c else None,
        (_cartier_url(c, a) + ".html") if c else None,
    ],
    "corum": lambda b, c, a: [
        f"https://corumwatch.jp/products/{c.lower().replace(' ', '-')}-{a.lower().replace('/', '-')}/" if c else f"https://corumwatch.jp/products/admiral-45-{a.lower().replace('/', '-')}/",
    ],
}


# Маппинг префиксов артикула Cartier на slug коллекции.
# Артикул на официальном сайте пишется как CRW + артикул, например CRWSSA0037.
# Префиксы артикулов Tudor на slug коллекции.
TUDOR_PREFIXES = {
    "M2543": "pelagos",
    "M2560": "pelagos",
    "M2580": "pelagos",
    "M2639": "monarch",
    "M2640": "monarch",
    "M7900": "black-bay",
    "M7920": "black-bay",
    "M7936": "black-bay",
    "M7940": "black-bay",
    "M7941": "black-bay",
    "M7954": "black-bay",
    "M7010": "black-bay",
    "M3800": "black-bay",
    "M2860": "black-bay",
    "M2870": "black-bay",
}

# Префиксы IWC.
IWC_PREFIXES = {
    "IW328": "pilots-watches",
    "IW329": "pilots-watches",
    "IW327": "pilots-watches",
    "IW377": "pilots-watches",
    "IW388": "pilots-watches",
    "IW371": "portugieser",
    "IW500": "portugieser",
    "IW501": "portugieser",
    "IW503": "portugieser",
    "IW504": "portugieser",
    "IW356": "portofino",
    "IW357": "portofino",
    "IW391": "portofino",
    "IW458": "portofino",
    "IW459": "portofino",
}

# Префиксы Alpina.
ALPINA_PREFIXES = {
    "AL-525": "seastrong",
    "AL-650": "seastrong",
    "AL-280": "startimer",
    "AL-240": "startimer",
    "AL-710": "alpiner",
    "AL-750": "alpiner",
    "AL-860": "extreme",
}

# Префиксы Steinhart.
STEINHART_PREFIXES = {
    "103": "ocean-one",
    "104": "ocean-one",
    "105": "ocean-one",
    "107": "ocean-one",
    "108": "ocean-44",
    "109": "ocean-44",
}

# Префиксы Corum.
CORUM_PREFIXES = {
    "A082": "admiral",
    "A395": "admiral",
    "B395": "admiral",
    "L082": "admiral",
    "B113": "bubble",
    "L390": "golden-bridge",
}

# Префиксы Swatch (MoonSwatch, Bioceramic).
SWATCH_PREFIXES = {
    "SO33": "moonswatch",
    "SO27": "bioceramic",
    "SO28": "bioceramic",
    "SO29": "bioceramic",
    "SO32": "bioceramic",
    "SO34": "bioceramic",
}

# Префиксы Piaget.
PIAGET_PREFIXES = {
    "G0A45": "polo",
    "G0A43": "polo",
    "G0A42": "polo",
    "G0A41": "altiplano",
    "G0A40": "altiplano",
    "G0A36": "possession",
}

# Префиксы Audemars Piguet.
AP_PREFIXES = {
    "15510": "royal-oak",
    "15500": "royal-oak",
    "15400": "royal-oak",
    "15202": "royal-oak",
    "26331": "royal-oak",
    "15710": "royal-oak-offshore",
    "26400": "royal-oak-offshore",
    "15210": "code-1159",
}

# Префиксы TAG Heuer.
TAG_PREFIXES = {
    "WBN": "carrera",
    "WAR": "carrera",
    "WBC": "carrera",
    "CAR": "carrera",
    "WAY": "aquaracer",
    "WBP": "aquaracer",
    "WBE": "autavia",
    "WAW": "monaco",
}

CARTIER_PREFIXES = {
    "WSSA": "santos-de-cartier",
    "WSSB": "santos-de-cartier",
    "W2SA": "santos-de-cartier",
    "WGBB": "santos-dumont",
    "WSPA": "pasha-de-cartier",
    "WSPN": "panthere-de-cartier",
    "WSBB": "ballon-bleu-de-cartier",
    "WSBC": "ballon-bleu-de-cartier",
    "W4BD": "ballon-bleu-de-cartier",
    "W690": "ballon-bleu-de-cartier",
    "WSTA": "tank",
    "WSTB": "tank",
    "W4TA": "tank",
    "W531": "tank",
    "WJTA": "tank",
    "WGTA": "tank",
    "W260": "tank",
    "W152": "tank",
    "WSRN": "ronde-de-cartier",
    "WSNM": "drive-de-cartier",
    "WGNM": "drive-de-cartier",
    "WHTN": "hypnose",
    "WGNB": "clash-de-cartier",
    "CRW": "",  # префикс уже содержит коллекцию, определим по следующим 3-4 символам
}


# Fallback-подбор коллекций для официальных сайтов, когда префикс не распознан.
BRAND_COLLECTION_GUESSES = {
    "iwc": ["pilots-watches", "portugieser", "portofino", "aquatimer", "ingenieur"],
    "piaget": ["polo", "altiplano", "possession"],
    "audemars piguet": ["royal-oak", "royal-oak-offshore", "code-1159"],
    "tag heuer": ["carrera", "aquaracer", "monaco", "autavia"],
    "breitling": ["superocean", "superocean-heritage", "navitimer", "chronomat", "avenger", "premier", "top-time", "classic-avi", "professional"],
    "longines": ["heritage", "master", "hydroconquest", "dolcevita"],
    "omega": ["seamaster", "speedmaster", "constellation", "de-ville"],
    "rado": ["captain-cook", "true", "centrix", "hyperchrome"],
    "hamilton": ["jazzmaster", "khaki", "american-classic"],
    "mido": ["commander", "ocean-star", "baroncelli"],
    "certina": ["ds-caimano", "ds-action", "ds-podum"],
    "tissot": ["le-locle", "prx", "seastar", "tradition"],
    "seiko": ["prospex", "presage", "seiko-5", "astron"],
    "bulova": ["precisionist", "classic", "maitre"],
    "citizen": ["promaster", "eco-drive", "attesa"],
    "baume & mercier": ["riviera", "classima", "clifton"],
    "panerai": ["luminor", "radiomir", "submersible"],
    "ball": ["engineer", "fireman", "trainmaster"],
    "bell & ross": ["br-05", "br-03", "br-v2"],
    "cartier": ["santos-de-cartier", "tank", "ballon-bleu-de-cartier", "pasha-de-cartier", "ronde-de-cartier"],
    "alpina": ["seastrong", "alpiner", "startimer", "extreme"],
    "steinhart": ["ocean-one", "ocean-44", "marine", "aviation"],
    "corum": ["admiral", "golden-bridge", "bubble"],
}

LOCALE_VARIANTS = [
    "en-us", "en-gb", "en", "us-en", "int/en", "us/en", "uk/en",
    "eu/en", "ch-en", "global-en", "eng-us", "eng-gb", "en_int",
    "au-en", "sg-en",
]

# Регулярка для поиска первого сегмента локали в URL.
LOCALE_RE = re.compile(
    r"/(en-us|en-gb|en-int|en_int|int/en|us/en|uk/en|eu/en|ch-en|us-en|global-en|eng-us|eng-gb|eng/|en/|fr/|de/|it/|es/|au-en|sg-en)/",
    re.IGNORECASE,
)


def _toggle_html_suffix(url):
    """Возвращает URL с переключённым суффиксом .html, если это разумно."""
    parsed = urlparse(url)
    path = parsed.path
    if not path or path == "/":
        return None
    if path.endswith(".html"):
        new_path = path[:-5]
        if not new_path:
            return None
    else:
        last = path.rstrip("/").split("/")[-1]
        if not last or "." in last:
            return None
        new_path = path.rstrip("/") + ".html"
    return url.replace(path, new_path, 1)


def _expand_locale_variants(url):
    """Генерирует варианты URL с разными локалями и суффиксом .html."""
    if not url:
        return []
    result = [url]
    toggled = _toggle_html_suffix(url)
    if toggled and toggled not in result:
        result.append(toggled)

    match = LOCALE_RE.search(url)
    if not match:
        return result

    original_locale = match.group(1)
    prefix = url[:match.start()]
    suffix = url[match.end():]
    for loc in LOCALE_VARIANTS:
        if loc.lower() == original_locale.lower():
            continue
        variant = f"{prefix}/{loc}/{suffix}"
        if variant not in result:
            result.append(variant)
        toggled_variant = _toggle_html_suffix(variant)
        if toggled_variant and toggled_variant not in result:
            result.append(toggled_variant)
    return result


def _cartier_url(collection, articul):
    """Собирает URL официальной страницы Cartier.

    Артикул на сайте Cartier пишется с префиксом CRW.
    URL имеет вид:
        /watches/collections/{collection}/{collection}-watch-CRW{articul}.html
    """
    collection_slug = collection.lower().replace(" ", "-") if collection else ""
    if not collection_slug:
        return None
    # Cartier использует артикул с префиксом CRW в URL.
    # Пользовательский артикул WSSA0037 на сайте пишется как CRWSSA0037.
    cartier_ref = articul.upper().strip()
    if cartier_ref.startswith("CRW"):
        pass  # уже в нужном формате
    elif cartier_ref.startswith("W"):
        cartier_ref = f"CRW{cartier_ref[1:]}"
    else:
        cartier_ref = f"CRW{cartier_ref}"
    # Cartier отдает 404 на .html для некоторых локалей (en-gb), поэтому URL без .html.
    return (
        f"https://www.cartier.com/en-gb/watches/collections/{collection_slug}/"
        f"{collection_slug}-watch-{cartier_ref}"
    )


def guess_cartier_collection(articul):
    """Пытается определить коллекцию Cartier по префиксу артикула."""
    ref = articul.upper().strip()
    # Если артикул уже с CRW — отрезаем префикс и смотрим дальше
    if ref.startswith("CRW"):
        ref = ref[3:]
    for prefix, collection in CARTIER_PREFIXES.items():
        if ref.startswith(prefix) and collection:
            return collection
    # Fallback по первым 4 символам
    prefix4 = ref[:4]
    for prefix, collection in CARTIER_PREFIXES.items():
        if prefix4.startswith(prefix) and collection:
            return collection
    return ""


def _match_prefix_map(ref, prefix_map):
    """Возвращает значение по самому длинному совпавшему префиксу артикула."""
    ref = ref.upper().strip()
    best = ""
    for prefix, value in prefix_map.items():
        if ref.startswith(prefix.upper()) and len(prefix) > len(best):
            best = prefix
    return prefix_map.get(best, "")


def guess_collection(articul, brand):
    """Пытается угадать коллекцию по артикулу."""
    brand_lower = brand.lower().strip()
    if brand_lower == "cartier":
        return guess_cartier_collection(articul)
    if brand_lower == "tudor":
        return _match_prefix_map(articul, TUDOR_PREFIXES) or "monarch"
    if brand_lower == "rolex":
        if articul.upper().startswith("116") or articul.upper().startswith("126"):
            return "submariner"
    if brand_lower == "panerai":
        # Panerai: PAMxxxxx -> luminor, radiomir, submersible определяем по префиксу
        ref = articul.upper()
        if ref.startswith("PAM"):
            # Грубое деление: 5-значные PAM >= 14000 часто Submersible/Luminor Due,
            # но без точного маппинга используем общий collection slug.
            return "luminor"
    if brand_lower == "bvlgari":
        # Bvlgari: 6-значные цифровые референсы обычно принадлежат линейке Octo.
        ref = articul.strip()
        if ref.isdigit():
            return "octo"
    if brand_lower == "iwc":
        return _match_prefix_map(articul, IWC_PREFIXES)
    if brand_lower == "piaget":
        return _match_prefix_map(articul, PIAGET_PREFIXES)
    if brand_lower == "audemars piguet":
        return _match_prefix_map(articul, AP_PREFIXES)
    if brand_lower == "tag heuer":
        return _match_prefix_map(articul, TAG_PREFIXES)
    if brand_lower == "breitling":
        ref = articul.upper()
        if ref.startswith("AB20"):
            return "superocean-heritage"
        if ref.startswith("A173") or ref.startswith("A174") or ref.startswith("E173") or ref.startswith("A2"):
            return "superocean"
        if ref.startswith("AB01") or ref.startswith("A133") or ref.startswith("RB01"):
            return "navitimer"
        if ref.startswith("A253") or ref.startswith("V133") or ref.startswith("E133") or ref.startswith("XB"):
            return "avenger"
        if ref.startswith("UB01") or ref.startswith("EB01") or ref.startswith("SB01") or ref.startswith("JB") or ref.startswith("KB"):
            return "chronomat"
        if ref.startswith("RB"):
            return "premier"
        return "superocean"
    if brand_lower == "alpina":
        return _match_prefix_map(articul, ALPINA_PREFIXES)
    if brand_lower == "steinhart":
        return _match_prefix_map(articul, STEINHART_PREFIXES)
    if brand_lower == "corum":
        return _match_prefix_map(articul, CORUM_PREFIXES)
    if brand_lower == "swatch":
        return _match_prefix_map(articul, SWATCH_PREFIXES)
    return ""


def _brand_domain_slug(brand):
    """Возвращает базовый slug бренда для построения доменов."""
    brand_lower = brand.lower().strip()
    replacements = {
        "bvlgari": "bulgari",
        "tag heuer": "tagheuer",
        "patek philippe": "patekphilippe",
        "audemars piguet": "audemarspiguet",
        "vacheron constantin": "vacheron-constantin",
        "jaeger-lecoultre": "jaeger-lecoultre",
        "a. lange & söhne": "alange-soehne",
        "franck muller": "franckmuller",
        "ulysse nardin": "ulysse-nardin",
        "bell & ross": "bellross",
        "h. moser & cie.": "moser",
        "richard mille": "richardmille",
        "frederique constant": "frederiqueconstant",
        "union glashutte": "union-glashuette",
        "union glashütte": "union-glashuette",
        "alpina": "alpinawatches",
        "steinhart": "steinhartwatches",
    }
    return replacements.get(brand_lower, brand_lower.replace(" ", "-").replace("&", "and"))


def guess_universal_urls(brand, articul):
    """Возвращает список универсальных официальных URL-кандидатов для любого бренда."""
    slug = _brand_domain_slug(brand)
    ref = articul.strip()
    ref_lower = ref.lower()
    ref_upper = ref.upper()
    candidates = []
    patterns = [
        f"https://www.{slug}.com/en-us/products/{ref_lower}.html",
        f"https://www.{slug}.com/en-us/watches/{ref_lower}",
        f"https://www.{slug}.com/en/watches/{ref_lower}",
        f"https://www.{slug}.com/us-en/watches/{ref_lower}",
        f"https://www.{slug}.com/en-gb/watches/{ref_lower}",
        f"https://www.{slug}.com/en-int/watches/{ref_lower}",
        f"https://www.{slug}.com/int/en/watches/{ref_lower}",
        f"https://www.{slug}.com/global-en/watches/{ref_lower}",
        f"https://www.{slug}watches.com/en-us/watch/{ref_lower}",
        f"https://www.{slug}watches.com/en/{ref_lower}",
        f"https://www.{slug}-watches.com/{ref_lower}",
        f"https://www.{slug}-watches.com/en/{ref_lower}",
        f"https://www.{slug}watch.com/{ref_lower}",
    ]
    for p in patterns:
        if p not in candidates:
            candidates.append(p)
    return candidates


def get_official_url(brand, articul, collection=""):
    """Возвращает предполагаемый официальный URL или None."""
    brand_lower = brand.lower().strip()
    if brand_lower not in BRAND_TEMPLATES:
        return None
    if not collection:
        collection = guess_collection(articul, brand)
    if not collection and brand_lower in ("cartier", "panerai"):
        # Для Cartier/Panerai без коллекции не можем построить URL
        return None
    return BRAND_TEMPLATES[brand_lower](brand, collection, articul)


def get_official_url_candidates(brand, articul, collection=""):
    """Возвращает список кандидатов официальных URL для бренда/артикула.

    Для известных брендов генерирует варианты локалей и альтернативных путей,
    чтобы обойти региональные блокировки и разные структуры сайтов.
    """
    brand_lower = brand.strip().lower()
    if brand_lower not in BRAND_TEMPLATES:
        # Для неизвестных брендов пробуем универсальные шаблоны с вариантами локали.
        base_urls = guess_universal_urls(brand, articul)
        candidates = []
        for u in base_urls:
            candidates.extend(_expand_locale_variants(u))
        return _unique_urls(candidates)

    if not collection:
        collection = guess_collection(articul, brand)

    # Для Cartier/Panerai без коллекции не можем построить URL — пробуем универсальные.
    if not collection and brand_lower in ("cartier", "panerai"):
        base_urls = guess_universal_urls(brand, articul)
        candidates = []
        for u in base_urls:
            candidates.extend(_expand_locale_variants(u))
        return _unique_urls(candidates)

    base = BRAND_TEMPLATES[brand_lower](brand, collection, articul)
    if not base:
        base_urls = guess_universal_urls(brand, articul)
        candidates = []
        for u in base_urls:
            candidates.extend(_expand_locale_variants(u))
        return _unique_urls(candidates)

    candidates = _expand_locale_variants(base)

    if collection and brand_lower in BRAND_EXTRA_PATTERNS:
        for extra_url in BRAND_EXTRA_PATTERNS[brand_lower](brand, collection, articul):
            if extra_url:
                candidates.extend(_expand_locale_variants(extra_url))

    # Если коллекция не определена, пробуем несколько типовых коллекций бренда.
    if not collection and brand_lower in BRAND_COLLECTION_GUESSES:
        for guess in BRAND_COLLECTION_GUESSES[brand_lower]:
            guess_url = BRAND_TEMPLATES[brand_lower](brand, guess, articul)
            if guess_url:
                candidates.extend(_expand_locale_variants(guess_url))

    return _unique_urls(candidates)


def _unique_urls(urls):
    """Убирает дубликаты из списка URL, сохраняя порядок."""
    seen = set()
    unique = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            unique.append(u)
    return unique
