import requests
import pandas as pd
import os



OUTPUT_FILE = "data/raw/raw6.csv"
os.makedirs("data/raw", exist_ok=True)

MAX_RECIPES = 2000
recipes = []

letters = "abcdefghijklmnopqrstuvwxyz"



for letter in letters:
    print(f"[LETTER] {letter}")

    url = f"https://www.themealdb.com/api/json/v1/1/search.php?f={letter}"
    response = requests.get(url)
    data = response.json()

    meals = data.get("meals")

    if not meals:
        continue

    for meal in meals:
        title = meal.get("strMeal", "N/A")
        instructions = meal.get("strInstructions", "N/A")
        country = meal.get("strArea", "Unknown")

        # INGREDIENTS (20 max)
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")

            if ing and ing.strip():
                ingredients.append(f"{measure} {ing}".strip())

        recipes.append({
            "title": title,
            "ingredients": " | ".join(ingredients),  # better for CSV
            "instructions": instructions,
            "time_to_cook": "N/A",
            "country_origin": country
        })

        print("Collected:", len(recipes))

        if len(recipes) >= MAX_RECIPES:
            break

    if len(recipes) >= MAX_RECIPES:
        break


df = pd.DataFrame(recipes)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("\nDONE ✔")
print("TOTAL RECIPES:", len(recipes))
print("Saved to:", OUTPUT_FILE)