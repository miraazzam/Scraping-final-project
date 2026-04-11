"""
Open Food Facts - Data Cleaning Script
=======================================
Reads the latest raw CSV from data/raw/
Cleans and saves the result to data/clean/

Cleaning steps:
  1.  Load latest raw CSV automatically
  2.  Drop fully empty rows
  3.  Drop duplicate barcodes
  4.  Fill missing product_name and barcode with "N/A"
  5.  Strip whitespace from all string columns
  6.  Replace empty strings with NaN
  7.  Title-case text columns (product_name, brands, etc.)
  8.  Clean numeric columns (remove units, convert to float)
  9.  Cap impossible nutrition values per 100g
  10. Standardize nutriscore_grade / ecoscore_grade (a-e or unknown)
  11. Validate nova_group (must be 1-4, else NaN)
  12. Clean tag columns (remove 'en:' / 'fr:' prefixes)
  13. Standardize date columns to YYYY-MM-DD
  14. Add cleaned_at timestamp column
  15. Save clean CSV to data/clean/
"""

import os
import glob
import logging
import re
import numpy as np
import pandas as pd
from datetime import datetime

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR   = os.path.join(BASE_DIR, "data", "raw")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

# ── Column Groups ─────────────────────────────────────────────────────────────
NUMERIC_COLS = [
    "energy_kj", "energy_kcal",
    "fat_g", "saturated_fat_g", "monounsaturated_fat_g",
    "polyunsaturated_fat_g", "trans_fat_g", "cholesterol_mg",
    "carbohydrates_g", "sugars_g", "added_sugars_g", "fiber_g",
    "protein_g", "salt_g", "sodium_mg",
    "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug", "vitamin_e_mg",
    "vitamin_k_ug", "calcium_mg", "iron_mg", "magnesium_mg",
    "potassium_mg", "zinc_mg", "folate_ug", "omega_3_g",
    "caffeine_mg", "alcohol_pct",
    "nutriscore_score", "ecoscore_score",
    "completeness_pct", "unique_scans",
    "additives_count", "palm_oil_ingredients", "may_have_palm_oil",
    "serving_quantity_g",
]

TITLE_CASE_COLS = [
    "product_name", "product_name_en", "product_name_fr", "product_name_ar",
    "generic_name", "abbreviated_name",
    "brands", "brand_owner", "producer",
    "origins", "countries", "manufacturing_places", "purchase_places",
]

GRADE_COLS = ["nutriscore_grade", "ecoscore_grade"]

TAG_COLS = [
    "allergens_tags", "traces_tags", "additives",
    "packaging_tags", "labels",
]

DATE_COLS = ["last_modified", "created"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_latest_raw() -> pd.DataFrame:
    """Load the most recently created FINAL raw CSV from data/raw/."""
    finals  = sorted(glob.glob(os.path.join(RAW_DIR, "*_FINAL.csv")), reverse=True)
    all_raw = sorted(glob.glob(os.path.join(RAW_DIR, "openfoodfacts_raw_*.csv")), reverse=True)
    candidates = finals if finals else all_raw
    if not candidates:
        raise FileNotFoundError(
            f"No raw CSV found in {RAW_DIR}. Run scraper_openfoodfacts.py first."
        )
    path = candidates[0]
    log.info(f"Loading: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    log.info(f"Loaded {len(df):,} rows x {len(df.columns)} columns")
    return df


def strip_unit(val):
    """Remove trailing units like g, mg, kcal, % from a string value."""
    if pd.isna(val):
        return np.nan
    val = str(val).strip()
    val = re.sub(r"[a-zA-Z%µ]+$", "", val).strip()
    try:
        return float(val)
    except ValueError:
        return np.nan


def clean_tags(series: pd.Series) -> pd.Series:
    """Remove 'en:' / 'fr:' language prefixes from pipe-separated tag strings."""
    def _clean(val):
        if pd.isna(val) or str(val).strip() in ("", "N/A"):
            return np.nan
        tags = [re.sub(r"^[a-z]{2}:", "", t.strip()) for t in str(val).split("|")]
        tags = [t.replace("-", " ").strip() for t in tags if t.strip()]
        return " | ".join(tags) if tags else np.nan
    return series.apply(_clean)


def clean_grade(series: pd.Series) -> pd.Series:
    """Normalize grade to lowercase single letter a-e, else 'unknown'."""
    valid = {"a", "b", "c", "d", "e"}
    def _clean(val):
        if pd.isna(val):
            return "unknown"
        v = str(val).strip().lower()
        return v if v in valid else "unknown"
    return series.apply(_clean)


def clean_nova(series: pd.Series) -> pd.Series:
    """Nova group must be integer 1-4, else NaN."""
    def _clean(val):
        try:
            v = int(float(val))
            return v if 1 <= v <= 4 else np.nan
        except (ValueError, TypeError):
            return np.nan
    return series.apply(_clean)


def clean_dates(series: pd.Series) -> pd.Series:
    """Parse date strings, return standardized YYYY-MM-DD."""
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


# ── Main Cleaning Pipeline ────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:

    # ── Step 1: Drop fully empty rows ─────────────────────────────────────
    log.info("Step 1: Drop fully empty rows")
    before = len(df)
    df.dropna(how="all", inplace=True)
    log.info(f"  Removed {before - len(df):,} fully empty rows")

    # ── Step 2: Drop duplicate barcodes ───────────────────────────────────
    log.info("Step 2: Drop duplicate barcodes")
    before = len(df)
    df.drop_duplicates(subset=["barcode"], keep="first", inplace=True)
    log.info(f"  Removed {before - len(df):,} duplicate barcodes")

    # ── Step 3: Fill missing product_name and barcode with N/A ────────────
    log.info("Step 3: Fill missing product_name and barcode with N/A")
    df["product_name"] = df["product_name"].replace("", np.nan).fillna("N/A")
    df["barcode"]      = df["barcode"].replace("", np.nan).fillna("N/A")

    # ── Step 4: Strip whitespace from all string columns ──────────────────
    log.info("Step 4: Strip whitespace")
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

    # ── Step 5: Replace empty strings with NaN ────────────────────────────
    log.info("Step 5: Replace empty strings with NaN")
    df.replace("", np.nan, inplace=True)

    # ── Step 6: Title-case text columns ───────────────────────────────────
    log.info("Step 6: Title-case text columns")
    for col in TITLE_CASE_COLS:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: x.title() if isinstance(x, str) and x != "N/A" else x
            )

    # ── Step 7: Clean numeric columns ─────────────────────────────────────
    log.info("Step 7: Clean numeric columns")
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].apply(strip_unit)

    # ── Step 8: Cap impossible nutrition values per 100g ──────────────────
    log.info("Step 8: Cap impossible nutrition values")
    macro_cols = [
        "fat_g", "saturated_fat_g", "monounsaturated_fat_g",
        "polyunsaturated_fat_g", "trans_fat_g",
        "carbohydrates_g", "sugars_g", "added_sugars_g",
        "fiber_g", "protein_g",
    ]
    for col in macro_cols:
        if col in df.columns:
            df.loc[df[col] > 100, col] = np.nan
            df.loc[df[col] < 0, col]   = np.nan

    if "energy_kcal" in df.columns:
        df.loc[df["energy_kcal"] > 900, "energy_kcal"] = np.nan
        df.loc[df["energy_kcal"] < 0,   "energy_kcal"] = np.nan

    if "alcohol_pct" in df.columns:
        df.loc[df["alcohol_pct"] > 100, "alcohol_pct"] = np.nan
        df.loc[df["alcohol_pct"] < 0,   "alcohol_pct"] = np.nan

    if "completeness_pct" in df.columns:
        df.loc[df["completeness_pct"] > 1, "completeness_pct"] = (
            df.loc[df["completeness_pct"] > 1, "completeness_pct"] / 100
        )

    # ── Step 9: Standardize grade columns ─────────────────────────────────
    log.info("Step 9: Standardize nutriscore and ecoscore grades")
    for col in GRADE_COLS:
        if col in df.columns:
            df[col] = clean_grade(df[col])

    # ── Step 10: Validate nova_group ──────────────────────────────────────
    log.info("Step 10: Validate nova_group")
    if "nova_group" in df.columns:
        df["nova_group"] = clean_nova(df["nova_group"])

    # ── Step 11: Clean tag columns ────────────────────────────────────────
    log.info("Step 11: Clean tag columns (remove en:/fr: prefixes)")
    for col in TAG_COLS:
        if col in df.columns:
            df[col] = clean_tags(df[col])

    # ── Step 12: Standardize date columns ────────────────────────────────
    log.info("Step 12: Standardize date columns")
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = clean_dates(df[col])

    # ── Step 13: Add cleaned_at timestamp ─────────────────────────────────
    log.info("Step 13: Add cleaned_at timestamp")
    df["cleaned_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df


# ── Save ──────────────────────────────────────────────────────────────────────

def save_clean(df: pd.DataFrame):
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"openfoodfacts_clean_{ts}.csv"
    path = os.path.join(CLEAN_DIR, name)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"Saved {len(df):,} clean records -> {path}")
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Open Food Facts Cleaner Starting ===")

    df = load_latest_raw()

    log.info(f"Starting shape: {df.shape}")
    df = clean(df)
    log.info(f"Final shape:    {df.shape}")

    path = save_clean(df)

    # ── Summary report ────────────────────────────────────────────────────
    log.info("\n=== Cleaning Summary ===")
    log.info(f"  Total rows:      {len(df):,}")
    log.info(f"  Total columns:   {len(df.columns)}")
    log.info(f"  N/A product names: {(df['product_name'] == 'N/A').sum():,}")
    log.info(f"  N/A barcodes:      {(df['barcode'] == 'N/A').sum():,}")
    log.info(f"  Missing energy_kcal: {df['energy_kcal'].isna().sum():,}")
    log.info(f"  Missing nutriscore:  {(df['nutriscore_grade'] == 'unknown').sum():,}")
    log.info(f"  Output: {path}")
    log.info("=== Done! ===")


if __name__ == "__main__":
    main()