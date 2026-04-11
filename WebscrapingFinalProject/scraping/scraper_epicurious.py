"""
Epicurious.com Recipe Scraper — Simple Edition (No Selenium!)
Uses requests + BeautifulSoup + JSON-LD extraction.

Every Epicurious recipe page contains a <script type="application/ld+json">
block with ALL the recipe data pre-loaded. We just read that JSON directly.

Saves raw CSV → ../data/raw/epicurious_raw.csv
"""

import time
import random
import csv
import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass, fields, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── config ────────────────────────────────────────────────────────────────────
BASE_URL   = "https://www.epicurious.com"
SEARCH_URL = "https://www.epicurious.com/search?content=recipe&page={page}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RAW_DIR          = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
RAW_FILE         = os.path.join(RAW_DIR, "epicurious_raw.csv")
MAX_RECIPES      = 500
DELAY_MIN        = 1.5
DELAY_MAX        = 3.0
CHECKPOINT_EVERY = 50


# ── data model ────────────────────────────────────────────────────────────────
@dataclass
class Recipe:
    url:          str = ""
    title:        str = ""
    author:       str = ""
    rating:       str = ""
    review_count: str = ""
    description:  str = ""
    prep_time:    str = ""
    cook_time:    str = ""
    total_time:   str = ""
    servings:     str = ""
    categories:   str = ""
    ingredients:  str = ""
    steps:        str = ""
    scraped_at:   str = ""


# ── HTTP helper ───────────────────────────────────────────────────────────────
def get_soup(url: str) -> Optional[BeautifulSoup]:
    for attempt in range(3):
        try:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            log.warning("HTTP %s for %s", resp.status_code, url)
        except requests.RequestException as e:
            log.warning("Attempt %d failed: %s", attempt + 1, e)
            time.sleep(5)
    return None


# ── collect recipe links ──────────────────────────────────────────────────────
def get_recipe_links(max_recipes: int) -> list:
    links = []
    page  = 1

    while len(links) < max_recipes:
        url = SEARCH_URL.format(page=page)
        log.info("Fetching link page %d — %d collected so far", page, len(links))

        soup = get_soup(url)
        if soup is None:
            break

        anchors = soup.select('a[href^="/recipes/food/"]')
        if not anchors:
            log.info("No more links on page %d — stopping.", page)
            break

        for a in anchors:
            href = a["href"].split("?")[0]
            full = BASE_URL + href
            if full not in links:
                links.append(full)
            if len(links) >= max_recipes:
                break

        page += 1

    log.info("Total links collected: %d", len(links))
    return links


# ── extract JSON-LD from a recipe page ───────────────────────────────────────
def extract_jsonld(soup: BeautifulSoup) -> Optional[dict]:
    """
    Epicurious embeds a JSON-LD block like:
    <script type="application/ld+json">{ "@type": "Recipe", ... }</script>
    We extract that and parse it directly — no CSS selectors needed!
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # could be a list or a single object
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Recipe":
                        return item
            elif isinstance(data, dict):
                if data.get("@type") == "Recipe":
                    return data
                # sometimes nested under @graph
                for item in data.get("@graph", []):
                    if isinstance(item, dict) and item.get("@type") == "Recipe":
                        return item
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


# ── parse a single recipe page ────────────────────────────────────────────────
def parse_recipe(url: str) -> Optional[Recipe]:
    soup = get_soup(url)
    if soup is None:
        return None

    r = Recipe(url=url, scraped_at=datetime.utcnow().isoformat())

    # ── try JSON-LD first (most reliable) ────────────────────────────────
    data = extract_jsonld(soup)

    if data:
        r.title       = data.get("name", "")
        r.description = data.get("description", "")
        r.prep_time   = data.get("prepTime", "")
        r.cook_time   = data.get("cookTime", "")
        r.total_time  = data.get("totalTime", "")
        r.servings    = str(data.get("recipeYield", ""))

        # author
        author = data.get("author", {})
        if isinstance(author, list):
            r.author = ", ".join(a.get("name", "") for a in author if a.get("name"))
        elif isinstance(author, dict):
            r.author = author.get("name", "")
        else:
            r.author = str(author)

        # rating
        agg = data.get("aggregateRating", {})
        if agg:
            r.rating       = str(agg.get("ratingValue", ""))
            r.review_count = str(agg.get("reviewCount", ""))

        # categories
        cats = data.get("recipeCategory", [])
        if isinstance(cats, str):
            cats = [cats]
        keywords = data.get("keywords", "")
        if isinstance(keywords, str) and keywords:
            cats += [k.strip() for k in keywords.split(",")]
        r.categories = " | ".join(dict.fromkeys(c for c in cats if c))

        # ingredients
        ings = data.get("recipeIngredient", [])
        r.ingredients = " | ".join(i.strip() for i in ings if i.strip())

        # steps
        instructions = data.get("recipeInstructions", [])
        steps = []
        for step in instructions:
            if isinstance(step, dict):
                text = step.get("text", "")
                if text:
                    steps.append(text.strip())
            elif isinstance(step, str) and step.strip():
                steps.append(step.strip())
        r.steps = " | ".join(steps)

    else:
        # ── fallback: plain HTML parsing ─────────────────────────────────
        log.warning("No JSON-LD found at %s — falling back to HTML.", url)

        h1 = soup.find("h1")
        r.title = h1.get_text(strip=True) if h1 else ""

        for sel in ['a[href*="/contributor/"]', '[class*="byline"] a', 'a[rel="author"]']:
            tag = soup.select_one(sel)
            if tag and tag.get_text(strip=True):
                r.author = tag.get_text(strip=True)
                break

        for sel in ['[data-testid="recipe-dek"]', '[class*="dek"]', 'meta[name="description"]']:
            tag = soup.select_one(sel)
            if tag:
                val = tag.get("content", "") if tag.name == "meta" else tag.get_text(strip=True)
                if val:
                    r.description = val
                    break

        ing_tags = soup.select('[class*="ingredient" i] li') or soup.select('li[class*="ingredient" i]')
        r.ingredients = " | ".join(t.get_text(strip=True) for t in ing_tags if t.get_text(strip=True))

        step_tags = soup.select('[class*="step" i] p') or soup.select('[class*="instruction" i] li')
        r.steps = " | ".join(t.get_text(strip=True) for t in step_tags if t.get_text(strip=True))

    if not r.title and not r.ingredients:
        log.warning("Empty recipe at %s — skipping.", url)
        return None

    return r


# ── CSV save ──────────────────────────────────────────────────────────────────
def save_csv(recipes: list, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    col_names = [f.name for f in fields(Recipe)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=col_names)
        writer.writeheader()
        for rec in recipes:
            writer.writerow(asdict(rec))
    log.info("Saved %d recipes → %s", len(recipes), path)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    log.info("=== Epicurious Simple Scraper starting (no Selenium!) ===")
    recipes = []
    links   = get_recipe_links(MAX_RECIPES)

    for i, url in enumerate(links, 1):
        log.info("[%d/%d] %s", i, len(links), url)
        recipe = parse_recipe(url)
        if recipe:
            recipes.append(recipe)

        if i % CHECKPOINT_EVERY == 0:
            save_csv(recipes, RAW_FILE)
            log.info("Checkpoint — %d recipes saved.", len(recipes))

    save_csv(recipes, RAW_FILE)
    log.info("=== Done. %d recipes saved. ===", len(recipes))


if __name__ == "__main__":
    main()