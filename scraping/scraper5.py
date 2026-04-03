import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
from urllib.parse import urljoin, urlparse
import os
import lxml

print("🚀 Starting NO-API 2000+ Recipe Scraper...")
print("No keys needed - works immediately!")

def scrape_recipes():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    OUTPUT_FILE = "data/raw/raw5.csv"
    os.makedirs("data/raw", exist_ok=True)

    all_recipes = []
    
    # 🌟 SITE 1: TheMealDB
    print("\n1️ TheMealDB...")
    try:
        resp = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?f=a")
        if resp.status_code == 200:
            data = resp.json()
            for meal in data.get('meals', []):
                ingredients = [
                    meal.get(f'strIngredient{i}', '')
                    for i in range(1, 21)
                    if meal.get(f'strIngredient{i}')
                ]

                all_recipes.append({
                    'title': meal.get('strMeal', ''),
                    'ingredients': " | ".join(ingredients),
                    'instructions': meal.get('strInstructions', ''),
                    'cook_time': '',
                    'servings': '',
                    'source': 'TheMealDB',
                    'url': meal.get('strMealThumb', '')
                })
    except:
        pass

    print(f"   Total so far: {len(all_recipes)}")
    
    # 🌟 SITE 2: BBC GoodFood
    print("\n2️⃣ BBC GoodFood...")
    try:
        resp = requests.get("https://www.bbcgoodfood.com/recipes/collection/easy-recipes", headers=headers)
        soup = BeautifulSoup(resp.content, 'html.parser')

        for card in soup.select('a[href*="/recipes/"]')[:100]:
            title = card.get_text(strip=True)

            if title:
                all_recipes.append({
                    'title': title,
                    'ingredients': '',
                    'instructions': '',
                    'cook_time': '',
                    'servings': '',
                    'source': 'BBCGoodFood',
                    'url': card.get('href', '')
                })
    except:
        pass

    print(f"   Total so far: {len(all_recipes)}")
    
    # 🌟 SITE 3: AllRecipes
    print("\n3️⃣ AllRecipes...")
    try:
        resp = requests.get("https://www.allrecipes.com/recipes/17544/desserts/", headers=headers)
        soup = BeautifulSoup(resp.content, 'html.parser')

        for link in soup.select('a[href*="/recipe/"]')[:100]:
            title = link.get_text(strip=True)

            if title:
                all_recipes.append({
                    'title': title,
                    'ingredients': '',
                    'instructions': '',
                    'cook_time': '',
                    'servings': '',
                    'source': 'AllRecipes',
                    'url': link.get('href', '')
                })
    except:
        pass

    print(f"   Total so far: {len(all_recipes)}")
    
    # 🌟 SITE 4: Food.com
    print("\n4️⃣ Food.com...")
    try:
        for page in range(1, 6):
            url = "https://www.food.com/recipefinder"
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.content, 'html.parser')

            titles = soup.select('a[href*="/recipe/"]')[:100]

            for title in titles:
                text = title.get_text(strip=True)

                if text:
                    all_recipes.append({
                        'title': text,
                        'ingredients': '',
                        'instructions': '',
                        'cook_time': '',
                        'servings': '',
                        'source': 'Food.com',
                        'url': title.get('href', '')
                    })

            time.sleep(1)
    except:
        pass

   
    df = pd.DataFrame(all_recipes)
    df = df.drop_duplicates(subset=['title']).head(2000)


    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')

    print(f"\n🎉 SAVED {len(df)} recipes to {OUTPUT_FILE}")
    print("\nPreview:")
    print(df[['title', 'source', 'url']].head(10))

    print(f"\nSources: {df['source'].value_counts().to_dict()}")

    return df

if __name__ == "__main__":
    recipes_df = scrape_recipes()