"""
Epicurious Recipe Data Cleaner
Reads:  ../data/raw/epicurious_raw.csv
Saves:  ../data/clean/epicurious_clean.csv

Cleaning steps
──────────────
1.  Drop exact duplicates
2.  Normalize whitespace in all text columns
3.  Strip HTML entities / leftover tags
4.  Standardise time columns  → integer minutes
5.  Clean rating              → float 0-4 (Epicurious scale)
6.  Clean review_count        → integer
7.  Clean servings            → integer
8.  Split pipe-separated lists → keep as-is but strip each item
9.  Drop rows missing both title AND ingredients
10. Add a word-count column for ingredients & steps
11. Save with a clean timestamp
"""

import os
import re
import logging
from datetime import datetime

import pandas as pd

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── paths ─────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(__file__)
RAW_FILE  = os.path.join(BASE, "..", "data", "raw",   "epicurious_raw.csv")
CLEAN_DIR = os.path.join(BASE, "..", "data", "clean")
CLEAN_FILE = os.path.join(CLEAN_DIR, "epicurious_clean.csv")


# ── helpers ───────────────────────────────────────────────────────────────────
def strip_html(text: str) -> str:
    """Remove any leftover HTML tags and decode common entities."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text
            .replace("&amp;",  "&")
            .replace("&lt;",   "<")
            .replace("&gt;",   ">")
            .replace("&nbsp;", " ")
            .replace("&#39;",  "'")
            .replace("&quot;", '"'))
    return re.sub(r"\s+", " ", text).strip()


def normalize_whitespace(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def clean_pipe_list(series: pd.Series) -> pd.Series:
    """Strip whitespace around each pipe-separated item."""
    def _clean(val):
        if not isinstance(val, str) or val in ("", "nan"):
            return ""
        items = [i.strip() for i in val.split("|") if i.strip()]
        return " | ".join(items)
    return series.apply(_clean)


def parse_minutes(val: str) -> float:
    """
    Convert time strings like '1 hour 30 minutes', '45 mins', '2 hrs' → float minutes.
    Returns NaN if unparseable.
    """
    if not isinstance(val, str) or val.strip() in ("", "nan"):
        return float("nan")
    val = val.lower()
    hours   = re.search(r"(\d+)\s*h(ou)?r",   val)
    minutes = re.search(r"(\d+)\s*m(in)?",    val)
    total   = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    # bare number with no unit → assume minutes
    if total == 0:
        bare = re.search(r"^\s*(\d+)\s*$", val)
        if bare:
            total = int(bare.group(1))
    return float(total) if total > 0 else float("nan")


def parse_rating(val: str) -> float:
    """Extract first float found in the rating string."""
    if not isinstance(val, str):
        return float("nan")
    m = re.search(r"(\d+\.?\d*)", val)
    return float(m.group(1)) if m else float("nan")


def parse_int(val: str) -> float:
    """Extract first integer from a string."""
    if not isinstance(val, str):
        return float("nan")
    m = re.search(r"(\d+)", val.replace(",", ""))
    return float(m.group(1)) if m else float("nan")


def count_pipe_items(series: pd.Series) -> pd.Series:
    """Count the number of items in a pipe-separated column."""
    return series.apply(
        lambda v: len([i for i in str(v).split("|") if i.strip()])
        if isinstance(v, str) else 0
    )


# ── main cleaning pipeline ────────────────────────────────────────────────────
def clean(df: pd.DataFrame) -> pd.DataFrame:
    original_rows = len(df)
    log.info("Loaded %d rows.", original_rows)

    # 1. drop exact duplicates
    df.drop_duplicates(inplace=True)
    log.info("After dedup: %d rows.", len(df))

    # 2. normalize whitespace in all columns
    for col in df.columns:
        df[col] = normalize_whitespace(df[col])

    # 3. strip HTML entities / tags from text fields
    text_cols = ["title", "author", "description", "categories", "ingredients", "steps"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(strip_html)

    # 4. standardise time columns → integer minutes
    for time_col in ["prep_time", "cook_time", "total_time"]:
        if time_col in df.columns:
            df[f"{time_col}_mins"] = df[time_col].apply(parse_minutes)
            df.drop(columns=[time_col], inplace=True)

    # 5. clean rating → float
    if "rating" in df.columns:
        df["rating"] = df["rating"].apply(parse_rating)

    # 6. clean review_count → integer
    if "review_count" in df.columns:
        df["review_count"] = df["review_count"].apply(parse_int).astype("Int64")

    # 7. clean servings → integer
    if "servings" in df.columns:
        df["servings"] = df["servings"].apply(parse_int).astype("Int64")

    # 8. clean pipe-separated lists
    for col in ["ingredients", "steps", "categories"]:
        if col in df.columns:
            df[col] = clean_pipe_list(df[col])

    # 9. drop rows missing both title AND ingredients
    before = len(df)
    df = df[~((df["title"].str.strip() == "") & (df["ingredients"].str.strip() == ""))]
    log.info("Dropped %d rows with no title AND no ingredients.", before - len(df))

    # 10. add count columns
    if "ingredients" in df.columns:
        df["ingredient_count"] = count_pipe_items(df["ingredients"])
    if "steps" in df.columns:
        df["step_count"] = count_pipe_items(df["steps"])

    # 11. add cleaned_at timestamp
    df["cleaned_at"] = datetime.utcnow().isoformat()

    # reorder columns nicely
    preferred_order = [
        "url", "title", "author", "description",
        "rating", "review_count",
        "prep_time_mins", "cook_time_mins", "total_time_mins",
        "servings", "categories",
        "ingredient_count", "ingredients",
        "step_count", "steps",
        "scraped_at", "cleaned_at",
    ]
    existing = [c for c in preferred_order if c in df.columns]
    rest     = [c for c in df.columns if c not in existing]
    df = df[existing + rest]

    log.info("Final clean dataset: %d rows, %d columns.", len(df), len(df.columns))
    return df


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    log.info("=== Epicurious Cleaner starting ===")

    if not os.path.exists(RAW_FILE):
        log.error("Raw file not found: %s", RAW_FILE)
        log.error("Run scraper.py first.")
        return

    df = pd.read_csv(RAW_FILE, dtype=str)
    df_clean = clean(df)

    os.makedirs(CLEAN_DIR, exist_ok=True)
    df_clean.to_csv(CLEAN_FILE, index=False, encoding="utf-8")
    log.info("Clean CSV saved → %s", CLEAN_FILE)
    log.info("=== Done ===")


if __name__ == "__main__":
    main()