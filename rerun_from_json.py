import json, time
from pathlib import Path
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
sys.path.insert(0, "app")

from generator import generate_characteristics, _source_tier_label
from retailers import get_source_tier
from utils import save_result

PROJECT_ROOT = Path(".").resolve()

# Готовые спеки из WebFetch / web-поиска для позиций, которые не смогли загрузить напрямую.
FIXUPS = {
    ("IWC", "IW328201"): {
        "source_url": "https://www.caratco.com/products/iw328201",
        "page_text": """Model name: IWC Pilot's Watch Mark XX. Collection: Pilot's Watches. Reference: IW328201. Case material: Stainless steel. Diameter: 40 mm. Thickness: 10.8 mm. Movement: Automatic. Caliber: 32111. Jewels: 21. Frequency: 28 800 vph. Power reserve: 120 hours. Water resistance: 10 bar / 100 meters. Glass: Sapphire crystal with anti-reflective coating. Dial color: Black. Strap material: Black calf leather. Additional functions: Date display at 3 o'clock, soft-iron inner case for magnetic protection, glass secured against displacement by drop in air pressure, luminescence."""
    },
    ("Piaget", "G0A45005"): {
        "source_url": "https://www.watches-of-switzerland.co.uk/Piaget-Polo-G0A45005/p/17800567",
        "page_text": """Model name: Piaget Polo. Collection: Polo. Reference: G0A45005. Case material: Stainless steel. Diameter: 42 mm. Movement: Automatic. Caliber: 1110P. Water resistance: 100 meters. Dial color: Green. Bracelet material: Stainless steel. Case back: Sapphire crystal."""
    },
    ("Swatch", "SO33M100"): {
        "source_url": "https://www.swatch.com/en-my/mission-to-the-moon-so33m100/SO33M100.html",
        "page_text": """Model name: Swatch Mission to the Moon. Collection: Bioceramic MoonSwatch. Reference: SO33M100. Case material: Bioceramic. Diameter: 42 mm. Thickness: 13.25 mm. Movement: Quartz chronograph. Caliber: ETA G10.212 AB ND. Jewels: 4. Water resistance: 30 meters. Glass: Biosourced glass. Dial color: Black. Strap material: Black VELCRO strap. Additional functions: Chronograph, tachymeter, date."""
    },
    ("U-BOAT", "8464"): {
        "source_url": "https://www.gnomonwatches.com/products/darkmoon-44mm-ipb-ref-8464-b",
        "page_text": """Model name: U-Boat Darkmoon 44mm IPB. Collection: Darkmoon. Reference: 8464/B. Case material: Stainless steel AISI 316L with IPB treatment. Diameter: 44 mm. Thickness: 13 mm. Movement: Quartz. Caliber: Ronda 712.3. Water resistance: 50 m. Glass: Domed sapphire. Dial color: Black. Strap material: Black vulcanised rubber. Additional functions: Oil-filled dial, left-hand crown, 60-month battery life, rear battery hatch."""
    },
    ("Audemars Piguet", "15510ST.OO.1320ST.06"): {
        "source_url": "https://www.audemarspiguet.com/com/en/watch-collection/royal-oak/15510ST.OO.1320ST.06.html",
        "page_text": """Model name: Royal Oak Selfwinding. Collection: Royal Oak. Reference: 15510ST.OO.1320ST.06. Case material: Stainless steel. Diameter: 41 mm. Movement: Selfwinding mechanical. Caliber: 4302. Jewels: 32. Frequency: 28 800 vph. Power reserve: 70 hours. Water resistance: 50 meters. Glass: Sapphire. Dial color: Bleu Nuit Nuage 50. Dial pattern: Grande Tapisserie. Bracelet material: Stainless steel. Additional functions: Date."""
    },
    ("Bvlgari", "103481"): {
        "source_url": "https://www.thewatchpages.com/watches/bulgari-octo-roma-worldtimer-steel-103481/",
        "page_text": """Model name: Bvlgari Octo Roma Worldtimer. Collection: Octo Roma. Reference: 103481. Case material: Stainless steel. Diameter: 41 mm. Thickness: 11.35 mm. Movement: Automatic mechanical. Caliber: BVL257. Jewels: 26. Frequency: 28 800 vph. Power reserve: 42 hours. Water resistance: 100 meters. Glass: Sapphire. Dial color: Blue satin-finished sunray. Bracelet material: Stainless steel. Additional functions: World time, 24 time zones, GMT, 24-hour display, small seconds, date."""
    },
    ("Alpina", "AL-525LBG4V6"): {
        "source_url": "https://azfinetime.com/products/alpina-al-525lbg4v6-seastrong-diver-300-automatic-black-dial",
        "page_text": """Model name: Alpina Seastrong Diver 300. Collection: Seastrong Diver 300. Reference: AL-525LBG4V6. Case material: Stainless steel. Diameter: 44 mm. Movement: Automatic. Caliber: AL-525. Jewels: 26. Frequency: 28 800 vph. Power reserve: 38 hours. Water resistance: 300 meters. Glass: Scratch-resistant sapphire crystal. Dial color: Matte black. Strap material: Rubberized nubuck. Additional functions: Date, unidirectional rotating bezel, screw-in crown."""
    },
    ("Bomberg", "NS44CHPBA"): {
        "source_url": "https://www.timepiece.com/bomberg-bb-68-chronograph-quartz-black-dial-mens-watch-ns44chpba-200-9.html",
        "page_text": """Model name: Bomberg BB-68 Chronograph. Collection: BB-68. Reference: NS44CHPBA.200.9. Case material: Stainless steel with black PVD. Diameter: 44 mm. Thickness: 13 mm. Movement: Quartz chronograph. Caliber: Ronda 3520. Jewels: not specified. Water resistance: 50 meters. Glass: Sapphire crystal. Dial color: Black. Strap material: Leather. Additional functions: Chronograph, date."""
    },
    ("Breitling", "A17367D71B1S1"): {
        "source_url": "https://www.breitling.com/ch-en/watches/superocean/superocean-automatic-44/A17367D71B1S1/",
        "page_text": """Model name: Breitling Superocean Automatic 44. Collection: Superocean. Reference: A17367D71B1S1. Case material: Stainless steel. Diameter: 44 mm. Thickness: 14.21 mm. Movement: Automatic mechanical. Caliber: Breitling 17 (base ETA 2824-2). Jewels: 25. Frequency: 28 800 vph. Power reserve: 38 hours. Water resistance: 1000 meters. Glass: Sapphire crystal glareproofed both sides. Dial color: Black. Strap material: Black rubber Diver Pro III. Additional functions: Date, unidirectional dive bezel, screw-locked crown."""
    },
}


def _run_from_text(brand, articul, source_url, page_text):
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


summary = []
for (brand, articul), fix in FIXUPS.items():
    print(f"[{brand} {articul}] -> from prepared text")
    t0 = time.time()
    try:
        result = _run_from_text(brand, articul, fix["source_url"], fix["page_text"])
    except Exception as e:
        result = {
            "articul": articul,
            "brand": brand,
            "card": {"error": str(e)},
            "source_url": fix["source_url"],
            "source_tier": "error",
            "confidence_status": "manual_check_required",
            "note": str(e),
        }
    elapsed = time.time() - t0
    save_result(articul, brand, result)
    card = result.get("card", {})
    s = {
        "brand": brand,
        "articul": articul,
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
    print(s)
    summary.append(s)

out = PROJECT_ROOT / "output" / "rerun_fixups_summary.json"
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Saved {out}")
