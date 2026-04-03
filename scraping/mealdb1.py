import requests
import csv
import os



RAW_FILE = "data/raw/mealdb1.csv"
os.makedirs("data/raw", exist_ok=True)



CATEGORIES_URL = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"



cats = requests.get(CATEGORIES_URL, timeout=10).json()["meals"]

recipes = []

print("Collecting recipes from API...")



for c in cats:
    category = c["strCategory"]

    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"

    try:
        res = requests.get(url, timeout=10).json()
    except Exception as e:
        print("Category failed:", category, e)
        continue

    if not res.get("meals"):
        continue

    for meal in res["meals"]:
        meal_id = meal["idMeal"]

        # get full recipe details
        detail_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"

        try:
            detail = requests.get(detail_url, timeout=10).json()["meals"][0]
        except Exception as e:
            print("Meal failed:", meal_id, e)
            continue

        title = detail.get("strMeal", "N/A")
        instructions = detail.get("strInstructions", "N/A")

        # ingredients extraction
        ingredients = []
        for i in range(1, 21):
            ing = detail.get(f"strIngredient{i}")
            measure = detail.get(f"strMeasure{i}")

            if ing and ing.strip():
                if measure and measure.strip():
                    ingredients.append(f"{ing.strip()} - {measure.strip()}")
                else:
                    ingredients.append(ing.strip())

        url_source = detail.get("strSource", "N/A")

        recipes.append([title, "; ".join(ingredients), instructions, url_source])

        print(f"Added: {title}")


with open(RAW_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["title", "ingredients", "instructions", "url"])
    writer.writerows(recipes)

print("\nDONE ✔ Total recipes:", len(recipes))
print("Saved to:", RAW_FILE)