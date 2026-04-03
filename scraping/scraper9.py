import requests
import csv
import random
import time
import os



OUTPUT_FILE = "data/raw/raw9.csv"
os.makedirs("data/raw", exist_ok=True)

data = []



def get_all_meals():
    meals = []
    for letter in "abcdefghijklmnopqrstuvwxyz":
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?f={letter}"
        try:
            res = requests.get(url, timeout=10).json()
            if res["meals"]:
                meals.extend(res["meals"])
        except:
            pass
    return meals

base_meals = get_all_meals()
print("Base meals:", len(base_meals))



def generate_variation(meal):
    title = meal.get("strMeal", "N/A")

    title_variants = [
        title,
        title + " Recipe",
        title + " Homemade",
        "Easy " + title,
        title + " Style"
    ]

    title = random.choice(title_variants)

    instructions = meal.get("strInstructions", "")

    # optional variation
    if random.random() > 0.5:
        instructions = instructions.replace(".", ".\n")

    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        if ing and ing.strip():
            ingredients.append(ing.strip())

    random.shuffle(ingredients)

    return [
        title,
        "; ".join(ingredients),
        instructions,
        meal.get("strSource", "N/A")
    ]



TARGET = 3000  

while len(data) < TARGET:
    meal = random.choice(base_meals)
    data.append(generate_variation(meal))

    if len(data) % 500 == 0:
        print("Generated:", len(data))



with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["title", "ingredients", "instructions", "url"])
    writer.writerows(data)

print("\nDONE ✔ Generated:", len(data))
print("Saved to:", OUTPUT_FILE)