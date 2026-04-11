"""
Open Food Facts - Full Recipe & Food Scraper
=============================================
100% FREE — No API key, no rate limits, no blocking.
4 million+ products from 150+ countries.

Fields collected (ALL possible):
  Identity      : barcode, product_name, generic_name, abbreviated_name, alt_names
  Brand         : brands, brand_owner, manufacturer
  Classification: categories, food_groups, pnns_groups
  Origin        : origins, countries, countries_sold, manufacturing_places
  Ingredients   : ingredients_text, ingredients_list, additives, allergens,
                  traces, palm_oil, vegan, vegetarian
  Nutrition     : energy_kcal, fat, saturated_fat, carbs, sugars, fiber,
                  protein, salt, sodium + 15 micronutrients
  Scores        : nutriscore_grade, nutriscore_score, nova_group,
                  ecoscore_grade, ecoscore_score
  Packaging     : packaging, packaging_materials, packaging_recycling
  Labels        : labels (organic, fair trade, etc.)
  Media         : image_url, image_nutrition_url, image_ingredients_url
  Meta          : last_modified, created, sources, states
"""

import requests
import pandas as pd
import time
import os
import logging
from datetime import datetime

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE   = "https://world.openfoodfacts.org"
PAGE_SIZE  = 100      # max products per page (API limit)
MAX_PAGES  = 50       # 50 pages x 100 = 5,000 products (change as needed)
DELAY      = 3.0      # seconds between successful requests
RETRY_MAX  = 5        # max retries on 503/error
RETRY_WAIT = 10.0     # seconds to wait before retrying after a 503

# Open Food Facts REQUIRES a proper User-Agent — without it you get 403 blocked
HEADERS = {
    "User-Agent": "MyRecipeDataProject/1.0 (contact@example.com)",
    "Accept":     "application/json",
}

# Search categories to scrape — covers wide variety of food types
SEARCH_CATEGORIES = [
    "meals",
    "breakfasts",
    "desserts",
    "snacks",
    "beverages",
    "soups",
    "salads",
    "sandwiches",
    "pastas",
    "pizzas",
    "meats",
    "seafood",
    "dairy",
    "breads",
    "sauces",
    "cereals",
    "fruits",
    "vegetables",
]

# All fields to request — sent as POST body to avoid URL length limits
FIELDS = ",".join([
    # Identity
    "code", "product_name", "generic_name", "abbreviated_product_name",
    "product_name_en", "product_name_fr", "product_name_ar",
    # Brand
    "brands", "brand_owner", "producer",
    # Classification
    "categories", "categories_tags", "food_groups", "food_groups_tags",
    "pnns_groups_1", "pnns_groups_2",
    # Origin
    "origins", "countries", "countries_tags",
    "manufacturing_places", "purchase_places",
    # Ingredients
    "ingredients_text", "ingredients_text_en",
    "additives_n", "additives_tags",
    "allergens", "allergens_tags",
    "traces", "traces_tags",
    "ingredients_from_palm_oil_n",
    "ingredients_that_may_be_from_palm_oil_n",
    # Diet tags
    "labels", "labels_tags",
    # Nutrition (per 100g)
    "nutriments",
    # Scores
    "nutriscore_grade", "nutriscore_score",
    "nova_group", "nova_groups",
    "ecoscore_grade", "ecoscore_score",
    # Packaging
    "packaging", "packaging_tags", "packaging_materials_tags",
    "packaging_recycling_tags",
    # Quantity & Serving
    "quantity", "serving_size", "serving_quantity",
    # Media
    "image_url", "image_small_url",
    "image_nutrition_url", "image_nutrition_small_url",
    "image_ingredients_url",
    # Meta
    "last_modified_t", "created_t",
    "states", "states_tags",
    "sources_fields",
    "completeness",
    "unique_scans_n",
])


# ── API Helper (with retry) ───────────────────────────────────────────────────

def search_products(category: str, page: int = 1) -> dict | None:
    """Search Open Food Facts by category using POST with automatic retry on 503."""
    url = f"{API_BASE}/cgi/search.pl"
    data = {
        "action":         "process",
        "tagtype_0":      "categories",
        "tag_contains_0": "contains",
        "tag_0":          category,
        "page_size":      PAGE_SIZE,
        "page":           page,
        "json":           1,
        "fields":         FIELDS,
    }

    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = requests.post(url, data=data, headers=HEADERS, timeout=30)

            # Handle 503 specifically — server overloaded, wait and retry
            if resp.status_code == 503:
                log.warning(f"  503 Server Unavailable (attempt {attempt}/{RETRY_MAX}) — waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT * attempt)  # exponential back-off
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            log.warning(f"  Timeout (attempt {attempt}/{RETRY_MAX}) — waiting {RETRY_WAIT}s...")
            time.sleep(RETRY_WAIT * attempt)

        except requests.exceptions.RequestException as e:
            log.warning(f"  Request error (attempt {attempt}/{RETRY_MAX}): {e}")
            time.sleep(RETRY_WAIT * attempt)

    log.error(f"  Failed after {RETRY_MAX} attempts: category='{category}' page={page}")
    return None


# ── Parser ────────────────────────────────────────────────────────────────────

def safe(val, default=""):
    """Return val if not None/empty, else default."""
    return val if val not in (None, "", [], {}) else default


def parse_product(p: dict) -> dict:
    """Flatten a single product JSON into a clean dict with ALL fields."""
    n = p.get("nutriments", {})

    def nutr(key):
        return n.get(f"{key}_100g") or n.get(key) or None

    return {
        # ── Identity ──────────────────────────────────────────────────────
        "barcode":                  safe(p.get("code")),
        "product_name":             safe(p.get("product_name")),
        "product_name_en":          safe(p.get("product_name_en")),
        "product_name_fr":          safe(p.get("product_name_fr")),
        "product_name_ar":          safe(p.get("product_name_ar")),
        "generic_name":             safe(p.get("generic_name")),
        "abbreviated_name":         safe(p.get("abbreviated_product_name")),
        "quantity":                 safe(p.get("quantity")),
        "serving_size":             safe(p.get("serving_size")),
        "serving_quantity_g":       safe(p.get("serving_quantity")),

        # ── Brand ─────────────────────────────────────────────────────────
        "brands":                   safe(p.get("brands")),
        "brand_owner":              safe(p.get("brand_owner")),
        "producer":                 safe(p.get("producer")),

        # ── Classification ────────────────────────────────────────────────
        "categories":               safe(p.get("categories")),
        "pnns_group_1":             safe(p.get("pnns_groups_1")),
        "pnns_group_2":             safe(p.get("pnns_groups_2")),
        "food_groups":              safe(p.get("food_groups")),

        # ── Origin ────────────────────────────────────────────────────────
        "origins":                  safe(p.get("origins")),
        "countries":                safe(p.get("countries")),
        "manufacturing_places":     safe(p.get("manufacturing_places")),
        "purchase_places":          safe(p.get("purchase_places")),

        # ── Ingredients ───────────────────────────────────────────────────
        "ingredients_text":         safe(p.get("ingredients_text")),
        "ingredients_text_en":      safe(p.get("ingredients_text_en")),
        "additives_count":          safe(p.get("additives_n")),
        "additives":                " | ".join(p.get("additives_tags", []) or []),
        "allergens":                safe(p.get("allergens")),
        "allergens_tags":           " | ".join(p.get("allergens_tags", []) or []),
        "traces":                   safe(p.get("traces")),
        "traces_tags":              " | ".join(p.get("traces_tags", []) or []),
        "palm_oil_ingredients":     safe(p.get("ingredients_from_palm_oil_n")),
        "may_have_palm_oil":        safe(p.get("ingredients_that_may_be_from_palm_oil_n")),

        # ── Labels (organic, fair trade, etc.) ────────────────────────────
        "labels":                   safe(p.get("labels")),

        # ── Nutrition per 100g ────────────────────────────────────────────
        "energy_kj":                nutr("energy"),
        "energy_kcal":              nutr("energy-kcal"),
        "fat_g":                    nutr("fat"),
        "saturated_fat_g":          nutr("saturated-fat"),
        "monounsaturated_fat_g":    nutr("monounsaturated-fat"),
        "polyunsaturated_fat_g":    nutr("polyunsaturated-fat"),
        "trans_fat_g":              nutr("trans-fat"),
        "cholesterol_mg":           nutr("cholesterol"),
        "carbohydrates_g":          nutr("carbohydrates"),
        "sugars_g":                 nutr("sugars"),
        "added_sugars_g":           nutr("added-sugars"),
        "fiber_g":                  nutr("fiber"),
        "protein_g":                nutr("proteins"),
        "salt_g":                   nutr("salt"),
        "sodium_mg":                nutr("sodium"),
        "vitamin_a_ug":             nutr("vitamin-a"),
        "vitamin_c_mg":             nutr("vitamin-c"),
        "vitamin_d_ug":             nutr("vitamin-d"),
        "vitamin_e_mg":             nutr("vitamin-e"),
        "vitamin_k_ug":             nutr("vitamin-k"),
        "calcium_mg":               nutr("calcium"),
        "iron_mg":                  nutr("iron"),
        "magnesium_mg":             nutr("magnesium"),
        "potassium_mg":             nutr("potassium"),
        "zinc_mg":                  nutr("zinc"),
        "folate_ug":                nutr("folate"),
        "omega_3_g":                nutr("omega-3-fat"),
        "caffeine_mg":              nutr("caffeine"),
        "alcohol_pct":              nutr("alcohol"),

        # ── Health Scores ─────────────────────────────────────────────────
        "nutriscore_grade":         safe(p.get("nutriscore_grade")),
        "nutriscore_score":         safe(p.get("nutriscore_score")),
        "nova_group":               safe(p.get("nova_group")),
        "ecoscore_grade":           safe(p.get("ecoscore_grade")),
        "ecoscore_score":           safe(p.get("ecoscore_score")),

        # ── Packaging ─────────────────────────────────────────────────────
        "packaging":                safe(p.get("packaging")),
        "packaging_tags":           " | ".join(p.get("packaging_tags", []) or []),

        # ── Media ─────────────────────────────────────────────────────────
        "image_url":                safe(p.get("image_url")),
        "image_small_url":          safe(p.get("image_small_url")),
        "image_nutrition_url":      safe(p.get("image_nutrition_url")),
        "image_ingredients_url":    safe(p.get("image_ingredients_url")),

        # ── Meta ──────────────────────────────────────────────────────────
        "completeness_pct":         safe(p.get("completeness")),
        "unique_scans":             safe(p.get("unique_scans_n")),
        "states":                   safe(p.get("states")),
        "last_modified":            (
            datetime.fromtimestamp(p["last_modified_t"]).strftime("%Y-%m-%d %H:%M:%S")
            if p.get("last_modified_t") else None
        ),
        "created":                  (
            datetime.fromtimestamp(p["created_t"]).strftime("%Y-%m-%d %H:%M:%S")
            if p.get("created_t") else None
        ),
    }


# ── Save Helper ───────────────────────────────────────────────────────────────

def save_csv(records: list[dict], label: str = ""):
    if not records:
        return
    df = pd.DataFrame(records)
    # Fill missing product_name or barcode with "N/A" — keep ALL records
    df["product_name"] = df["product_name"].replace("", "N/A").fillna("N/A")
    df["barcode"]      = df["barcode"].replace("", "N/A").fillna("N/A")
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"openfoodfacts_raw_{ts}{label}.csv"
    path = os.path.join(RAW_DIR, name)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"  Saved {len(df)} records -> {path}")
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Open Food Facts Full Scraper Starting ===")
    all_records = []
    seen_barcodes: set[str] = set()

    for category in SEARCH_CATEGORIES:
        log.info(f"\nCategory: '{category}'")
        for page in range(1, MAX_PAGES + 1):
            data = search_products(category, page)
            if not data or not data.get("products"):
                log.info(f"  No more results at page {page}")
                break

            products = data["products"]
            count_new = 0
            for p in products:
                barcode = p.get("code", "")
                if barcode in seen_barcodes:
                    continue
                seen_barcodes.add(barcode)
                parsed = parse_product(p)
                all_records.append(parsed)
                count_new += 1

            log.info(f"  Page {page}: {count_new} new products (total so far: {len(all_records)})")

            # Checkpoint every 1000 records
            if len(all_records) % 1000 < PAGE_SIZE:
                save_csv(all_records, label=f"_checkpoint_{len(all_records)}")

            time.sleep(DELAY)

            # Stop if we got fewer results than page size (last page)
            if len(products) < PAGE_SIZE:
                break

    # Final save
    final_path = save_csv(all_records, label="_FINAL")
    log.info(f"\n=== Done! {len(all_records)} unique products saved to {final_path} ===")


if __name__ == "__main__":
    main()