import pandas as pd

# Load dataset
df = pd.read_csv("recipes_dataset.csv")

# ---------------------------
# 1. Clean column names
# ---------------------------
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# ---------------------------
# 2. Remove duplicates
# ---------------------------
df = df.drop_duplicates(subset=["title", "ingredients"])

# ---------------------------
# 3. Clean text columns
# ---------------------------
text_cols = ["title", "author", "ingredients", "steps", "source"]

for col in text_cols:
    df[col] = df[col].str.strip()

# Optional: lowercase titles for consistency
df["title"] = df["title"].str.lower()

# ---------------------------
# 4. Fix ratings
# ---------------------------
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

# Keep only valid ratings (0–5)
df = df[(df["rating"] >= 0) & (df["rating"] <= 5)]

# ---------------------------
# 5. Fix time columns
# ---------------------------
time_cols = ["prep_time", "cook_time", "total_time"]

for col in time_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove negative or unrealistic times
df = df[(df["prep_time"] >= 0) & (df["cook_time"] >= 0)]

# Optional: fix total_time if wrong
df["total_time"] = df["prep_time"] + df["cook_time"]

# ---------------------------
# 6. Remove empty or weird rows
# ---------------------------
df = df[df["title"].str.len() > 3]
df = df[df["ingredients"].str.len() > 10]

# ---------------------------
# 7. Reset index
# ---------------------------
df = df.reset_index(drop=True)

# ---------------------------
# 8. Save cleaned dataset
# ---------------------------
df.to_csv("cleaned_recipes.csv", index=False)

print("✅ Cleaning complete! File saved as cleaned_recipes.csv")