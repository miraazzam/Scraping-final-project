import pandas as pd
import numpy as np
import os
import re



INPUT_FILE = "data/raw/raw4.csv"
OUTPUT_FILE = "data/cleaned/cleaned4.csv"

os.makedirs("data/cleaned", exist_ok=True)



df = pd.read_csv(INPUT_FILE)
df.columns = [c.lower().strip() for c in df.columns]

print("Loaded shape:", df.shape)



cols = ["title", "ingredients", "instructions", "cook_time", "servings", "source", "url"]

for c in cols:
    if c not in df.columns:
        df[c] = np.nan



def clean_text(x):
    if pd.isna(x):
        return "N/A"

    x = str(x)

    # remove control characters
    x = re.sub(r"[\x00-\x1F\x7F]", " ", x)

    # remove weird symbols (keep readable text only)
    x = re.sub(r"[^a-zA-Z0-9\s.,'\"()\-:/|]", "", x)

    # normalize spaces
    x = re.sub(r"\s+", " ", x).strip()

    return x if x else "N/A"



for c in cols:
    df[c] = df[c].apply(clean_text)



# must have valid title
df = df[df["title"] != "N/A"]


for c in ["title", "ingredients", "instructions"]:
    df[c] = df[c].astype(str).str.strip()



df = df.drop_duplicates(subset=["title"])



df = df.reset_index(drop=True)

print("Final shape:", df.shape)



df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("DONE ✔ Saved to:", OUTPUT_FILE)