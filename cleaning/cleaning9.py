import pandas as pd
import numpy as np
import os


INPUT_FILE = "data/raw/raw9.csv"
OUTPUT_FILE = "data/cleaned/cleaned9.csv"

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
    return str(x).strip()

for col in required_cols:
    df[col] = df[col].apply(clean_text)



df = df[df[required_cols].ne("N/A").any(axis=1)]


df.drop_duplicates(subset=["title", "ingredients"], inplace=True)


df.reset_index(drop=True, inplace=True)

print("Final shape:", df.shape)



df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("DONE ✔ Saved to:", OUTPUT_FILE)