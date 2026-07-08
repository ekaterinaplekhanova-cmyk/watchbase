import csv, json, time
from pathlib import Path
import sys
import io
import concurrent.futures
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
sys.path.insert(0, "app")

from generator import generate_characteristics, _source_tier_label
from search import fetch_page_text
from retailers import get_source_tier
from utils import save_result, _safe_filename

PROJECT_ROOT = Path(".").resolve()
CSV_PATH = PROJECT_ROOT / "input" / "brands_test.csv"
all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))

# Список артикулов для перезапуска с явным source_url.
# Ключ: (brand, articul), значение: source_url.
RERUN = [
    ("Alain Silberstein", "Krono Bauhaus", "https://bernsteinwatchco.com/products/alain-silberstein-krono-bauhaus-lwo5100-limited-edition-of-999"),
    ("Certina", "C035.407.11.031.00", "https://watchbase.com/certina/ds-caimano/c035-407-11-037-00"),
    ("Breguet", "5177BB/29/9V6", "https://watchbase.com/breguet/classique/5177bb-29-9v6"),
    ("Bovet", "R260004", "https://bovet.watchonista.com/watches/bovet-recital-26-brainstormr-chapter-one-0"),
    ("IWC", "IW328201", "https://www.iwc.com/ww-en/watches/pilot-watches/iw328201-pilots-watch-mark-xx"),
    ("Piaget", "G0A45005", "https://www.watches-of-switzerland.co.uk/Piaget-Polo-G0A45005/p/17800567"),
    ("Romain Jerome", "RJ.M.AU.001.01", "https://everywatch.com/romain-jerome/titanic-dna/watch-11675125"),
    ("Schwarz-etienne", "SECS 001", "https://www.hodinkee.com/articles/schwarz-etienne-roma-synergy-by-kari-voutilainen-introducing"),
    ("Swatch", "SO33M100", "https://www.swatch.com/en-my/mission-to-the-moon-so33m100/SO33M100.html"),
    ("Grand Seiko", "SBGA211", "https://www.grand-seiko.com/global-en/collections/sbga211g"),
    ("RADO", "R32501203", "https://watchbase.com/rado/captain-cook/r32501203"),
    ("Traser", "109052", "https://www.traser.com/eu/en/collection/our-collection/outdoor-watches/p67-officer-pro/"),
    ("Jaeger-LeCoultre", "Q1368470", "https://www.jaeger-lecoultre.com/eu-en/watches/master-ultra-thin/master-ultra-thin-moon-stainless-steel-q1368430"),
    ("Jaquet Droz", "J017510240", "https://www.thewatchpages.com/watches/jaquet-droz-grande-heure-minute-quantieme-silver-j017510240/"),
    ("Juvenia", "WTA2.4.054.20", "https://www.juvenia.ch/wta2.4.054.20"),
    ("U-BOAT", "8464", "https://www.uboatwatch.com/product/darkmoon-black-pvd/"),
    ("Audemars Piguet", "15510ST.OO.1320ST.06", "https://www.audemarspiguet.com/com/en/watch-collection/royal-oak/15510ST.OO.1320ST.06.html"),
    ("Bomberg", "NS44CHPBA", "https://www.timepiece.com/bomberg-bb-68-chronograph-quartz-black-dial-mens-watch-ns44chpba-200-9.html"),
    ("Breitling", "A17367D71B1S1", "https://www.breitling.com/ch-en/watches/superocean/superocean-automatic-44/A17367D71B1S1/"),
    ("Bulova", "96B358", "https://www.bulova.com/global/product/98B358.html"),
    ("Bvlgari", "103481", "https://www.bulgari.com/en-int/watches/automatic-watches/octo-roma-watch-steel-silver-103481"),
    ("Girard-Perregaux", "81010-11-634-11A", "https://www.girard-perregaux.com/watches/laureato/81010-11-634-11a"),
    ("Seiko", "SRPD21K1", "https://www.seikowatches.com/uk-en/products/prospex/srpd21"),
    ("Alpina", "AL-525LBG4V6", "https://www.tourneau.com/watches/alpina/seastrong-diver-300-automatic-al-525lbg4v6-APN0100080.html"),
]


def _extract_summary(row, result, elapsed):
    card = result.get("card", {})
    return {
        "brand": row["brand"].strip(),
        "articul": row["articul"].strip(),
        "note": row.get("note", ""),
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
    }


def _run_with_source(brand, articul, source_url):
    page_text = fetch_page_text(source_url, timeout=15, retries=1, stream=True, max_bytes=262144)
    if page_text.startswith("[Ошибка"):
        raise RuntimeError(page_text)
    tier = get_source_tier(source_url)
    card = generate_characteristics(articul.upper(), brand, page_text)
    card["source_url"] = source_url
    card["source_tier"] = _source_tier_label(tier)
    if "error" not in card:
        card["confidence_status"] = "partial"
    else:
        card["confidence_status"] = "manual_check_required"
    return {
        "articul": articul.upper(),
        "brand": brand,
        "card": card,
        "source_url": source_url,
        "source_tier": _source_tier_label(tier),
        "confidence_status": card["confidence_status"],
    }


def _find_row(brand, articul):
    for row in all_rows:
        if row["brand"].strip() == brand and row["articul"].strip() == articul:
            return row
    return None


summary = []
for brand, articul, source_url in RERUN:
    row = _find_row(brand, articul)
    print(f"[{brand} {articul}] -> {source_url}")
    t0 = time.time()
    try:
        result = _run_with_source(brand, articul, source_url)
    except Exception as e:
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": str(e)},
            "source_url": source_url,
            "source_tier": "error",
            "confidence_status": "manual_check_required",
            "note": str(e),
        }
    elapsed = time.time() - t0
    save_result(articul, brand, result)
    s = _extract_summary(row or {"brand": brand, "articul": articul, "note": ""}, result, elapsed)
    print(s)
    summary.append(s)

out = PROJECT_ROOT / "output" / "rerun_summary.json"
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {out}")
