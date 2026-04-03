import pandas as pd
import numpy as np
import os



INPUT_FILE = "data/raw/raw7.csv"
OUTPUT_FILE = "data/cleaned/cleaned7.csv"

os.makedirs("data/cleaned", exist_ok=True)



df = pd.read_csv(INPUT_FILE)

print("Loaded shape:", df.shape)



df.columns = [c.lower().strip() for c in df.columns]



required_cols = ["title", "ingredients", "instructions", "cook_time", "servings", "source", "url"]

for col in required_cols:
    if col not in df.columns:
        df[col] = np.nan



def clean_text(x):
    if pd.isna(x):
        return "N/A"
    x = str(x).strip()
    return x if x else "N/A"

for col in required_cols:
    df[col] = df[col].apply(clean_text)



# remove rows with no title
df = df[df["title"] != "N/A"]

# normalize whitespace
for col in ["title", "ingredients", "instructions"]:
    df[col] = df[col].str.replace(r"\s+", " ", regex=True).str.strip()



df.drop_duplicates(subset=["title"], inplace=True)



df = df[df[["title", "ingredients"]].ne("N/A").any(axis=1)]



df.reset_index(drop=True, inplace=True)

print("Final shape:", df.shape)



df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("DONE ✔ Saved to:", OUTPUT_FILE)