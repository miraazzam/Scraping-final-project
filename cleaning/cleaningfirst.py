import pandas as pd
import numpy as np
import os
import re

print("🧹 Starting cleaning...")

INPUT_FILE = "data/raw/raw9.csv"
OUTPUT_FILE = "data/cleaned/first_cleaned.csv"

os.makedirs("data/cleaned", exist_ok=True)



df = pd.read_csv(INPUT_FILE)

print("Loaded shape:", df.shape)



df.columns = [c.lower().strip() for c in df.columns]


rename_map = {
    "recipe title": "title",
    "name": "title",
    "recipe": "title",
    "ingredient": "ingredients",
    "ingredients list": "ingredients",
    "steps": "instructions",
    "directions": "instructions",
    "link": "url"
}

df.rename(columns=rename_map, inplace=True)



required_cols = ["title", "ingredients", "instructions", "url"]

for col in required_cols:
    if col not in df.columns:
        df[col] = np.nan



def clean_text(x):
    if pd.isna(x):
        return "N/A"
    x = str(x)
    x = re.sub(r"[\x00-\x1F\x7F]", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x if x else "N/A"


def clean_instructions(x):
    if pd.isna(x):
        return "N/A"

    x = str(x)

    # remove control characters
    x = re.sub(r"[\x00-\x1F\x7F]", " ", x)

    # keep readable characters only
    x = re.sub(r"[^a-zA-Z0-9\s.,;:()\-']", " ", x)

    # normalize spaces
    x = re.sub(r"\s+", " ", x).strip()

    # reject garbage
    if len(x) < 20:
        return "N/A"

    if x.isdigit():
        return "N/A"

    if len(set(x.replace(" ", ""))) <= 2:
        return "N/A"

    return x


df["title"] = df["title"].apply(clean_text)
df["ingredients"] = df["ingredients"].apply(clean_text)
df["url"] = df["url"].apply(clean_text)
df["instructions"] = df["instructions"].apply(clean_instructions)


df = df[df["title"] != "N/A"]
df = df[df["instructions"] != "N/A"]



df.drop_duplicates(subset=["title", "ingredients"], inplace=True)

df.reset_index(drop=True, inplace=True)

print("Final shape:", df.shape)


df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("DONE ✔ Saved to:", OUTPUT_FILE)