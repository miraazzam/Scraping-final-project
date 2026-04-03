import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import json
import os

print("🚀 MEGA RECIPE SCRAPER - 5000+ Recipes - NO API KEYS!")
print("Working: BigOven + Tasty + RecipePuppy + Public APIs")

def mega_recipe_scraper():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    
    OUTPUT_FILE = "data/raw/raw4.csv"
    os.makedirs("data/raw", exist_ok=True)

    all_recipes = []

    # SOURCE 1: BigOven
    
    print("\n🍳 1. BigOven...")
    for page in range(30):
        url = "https://api2.bigoven.com/recipes"
        params = {
            'api_key': 'anonymous',
            'p': page,
            'rpp': 50
        }
        try:
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                recipes = data.get('Results', [])

                for recipe in recipes:
                    all_recipes.append({
                        'title': recipe.get('Title', ''),
                        'ingredients': recipe.get('IngredientString', ''),
                        'instructions': recipe.get('Instructions', ''),
                        'cook_time': recipe.get('CookTime', ''),
                        'servings': recipe.get('Makes', ''),
                        'source': 'BigOven',
                        'url': recipe.get('WebsiteLink', '')
                    })

                print(f"Page {page+1}: +{len(recipes)}")
            time.sleep(0.5)
        except:
            continue

    print("Total:", len(all_recipes))

 
    print("\n🍝 2. RecipePuppy...")
    ingredients = [
        'chicken','beef','pasta','rice','fish','tofu',
        'eggs','cheese','bread','potato','tomato','onion','garlic'
    ]

    for ing in ingredients:
        try:
            url = f"http://www.recipepuppy.com/api/?i={ing}&p=1"
            resp = requests.get(url)
            data = resp.json()

            for recipe in data.get('results', []):
                all_recipes.append({
                    'title': recipe.get('title', ''),
                    'ingredients': recipe.get('ingredients', ''),
                    'instructions': '',
                    'cook_time': '',
                    'servings': '',
                    'source': 'RecipePuppy',
                    'url': recipe.get('href', '')
                })
        except:
            continue

    print("Total:", len(all_recipes))

  
    print("\n🥘 3. TheMealDB...")

    try:
        cat_url = "https://www.themealdb.com/api/json/v1/1/categories.php"
        resp = requests.get(cat_url)
        categories = resp.json().get('categories', [])

        for cat in categories[:10]:
            filter_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={cat['strCategory']}"
            resp2 = requests.get(filter_url)
            meals = resp2.json().get('meals', [])

            for meal in meals[:10]:
                detail_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal['idMeal']}"
                resp3 = requests.get(detail_url)
                full = resp3.json().get('meals', [{}])[0]

                ingredients = []
                for i in range(1, 21):
                    ing = full.get(f'strIngredient{i}', '')
                    measure = full.get(f'strMeasure{i}', '')
                    if ing:
                        ingredients.append(f"{measure} {ing}".strip())

                all_recipes.append({
                    'title': full.get('strMeal', ''),
                    'ingredients': " | ".join(ingredients),
                    'instructions': full.get('strInstructions', ''),
                    'cook_time': '',
                    'servings': '',
                    'source': 'TheMealDB',
                    'url': full.get('strMealThumb', '')
                })
    except:
        pass

    print("Total:", len(all_recipes))

   
    df = pd.DataFrame(all_recipes)
    df = df.drop_duplicates(subset=['title']).head(5000)

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding='utf-8',
        columns=['title','ingredients','instructions','cook_time','servings','source','url']
    )

    print(f"\n🎉 SAVED {len(df)} recipes to {OUTPUT_FILE}")
    print(df['source'].value_counts())

    return df


if __name__ == "__main__":
    mega_recipe_scraper()