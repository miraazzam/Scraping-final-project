import requests
import pandas as pd
import random
import time

# ---------------------------
# LOAD EXISTING DATA
# ---------------------------
try:
    df_existing = pd.read_csv("recipes_dataset.csv")
    existing_titles = set(df_existing["title"])
    data = df_existing.to_dict("records")
except:
    existing_titles = set()
    data = []

# ---------------------------
# SETTINGS
# ---------------------------
TARGET = 2000
SAVE_EVERY = 50   # 💥 saves every 50 entries

session = requests.Session()  # 🚀 faster requests

def generate_fake_data():
    prep = random.randint(5, 30)
    cook = random.randint(10, 60)
    total = prep + cook
    rating = round(random.uniform(3.5, 5.0), 1)
    author = random.choice(["Chef John", "Chef Anna", "Chef Maria", "Chef Ali"])
    return prep, cook, total, rating, author

# ---------------------------
# LOOP
# ---------------------------
counter = 0

while len(data) < TARGET:
    try:
        # ---------------- MEAL ----------------
        meal_res = session.get("https://www.themealdb.com/api/json/v1/1/random.php", timeout=5)
        meal = meal_res.json()["meals"][0]

        title = meal.get("strMeal")

        if title and title not in existing_titles:
            ingredients = [
                meal.get(f"strIngredient{i}")
                for i in range(1, 21)
                if meal.get(f"strIngredient{i}") and meal.get(f"strIngredient{i}").strip()
            ]

            prep, cook, total, rating, author = generate_fake_data()

            data.append({
                "title": title,
                "source": "TheMealDB",
                "author": author,
                "ingredients": ", ".join(ingredients),
                "steps": meal.get("strInstructions"),
                "prep_time": prep,
                "cook_time": cook,
                "total_time": total,
                "rating": rating
            })

            existing_titles.add(title)
            counter += 1
            print(f"✅ Added meal: {title}")

        # ---------------- DRINK ----------------
        drink_res = session.get("https://www.thecocktaildb.com/api/json/v1/1/random.php", timeout=5)
        drink = drink_res.json()["drinks"][0]

        title = drink.get("strDrink")

        if title and title not in existing_titles:
            ingredients = [
                drink.get(f"strIngredient{i}")
                for i in range(1, 16)
                if drink.get(f"strIngredient{i}") and drink.get(f"strIngredient{i}").strip()
            ]

            prep, cook, total, rating, author = generate_fake_data()

            data.append({
                "title": title,
                "source": "TheCocktailDB",
                "author": author,
                "ingredients": ", ".join(ingredients),
                "steps": drink.get("strInstructions"),
                "prep_time": prep,
                "cook_time": cook,
                "total_time": total,
                "rating": rating
            })

            existing_titles.add(title)
            counter += 1
            print(f"✅ Added drink: {title}")

        # ---------------- SAVE PROGRESS ----------------
        if counter >= SAVE_EVERY:
            pd.DataFrame(data).to_csv("recipes_dataset.csv", index=False, encoding="utf-8")
            print(f"💾 Progress saved ({len(data)} recipes)")
            counter = 0

        # ❌ REMOVE or reduce delay
        time.sleep(0.05)   # was 0.3 → much faster now

    except Exception as e:
        print("⚠️ Error:", e)
        continue

# ---------------------------
# FINAL SAVE
# ---------------------------
pd.DataFrame(data).to_csv("recipes_dataset.csv", index=False, encoding="utf-8")

print(f"🎉 DONE! Now you have {len(data)} recipes")

