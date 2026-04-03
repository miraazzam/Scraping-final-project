import pandas as pd
import os
import glob

INPUT_FOLDER = "data/cleaned"
OUTPUT_FOLDER = "data/combined"
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "allone.csv")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

csv_files = glob.glob(os.path.join(INPUT_FOLDER, "*.csv"))

print(f"📂 Found {len(csv_files)} files")

all_data = []

for file in csv_files:
    try:
        df = pd.read_csv(file, dtype=str, keep_default_na=False)

        
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        
        df.drop(columns=[c for c in df.columns if "cook" in c], errors="ignore", inplace=True)

       
        if "url" in df.columns:
            df["url"] = (
                df["url"]
                .astype(str)
                .str.replace("\n", "", regex=True)
                .str.replace("\r", "", regex=True)
                .str.strip()
            )

       
        df.replace(r"^\s*$", "N/A", regex=True, inplace=True)
        df.fillna("N/A", inplace=True)

        print(f"✔ Loaded: {file} | rows: {len(df)} | cols: {len(df.columns)}")

        all_data.append(df)

    except Exception as e:
        print(f"❌ Error reading {file}: {e}")


final_df = pd.concat(all_data, ignore_index=True)

final_df.drop_duplicates(inplace=True)

final_df.replace(r"^\s*$", "N/A", regex=True, inplace=True)
final_df.fillna("N/A", inplace=True)


final_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
    quoting=1
)

print("\n🎉 DONE CLEAN MERGE")
print("Total rows:", len(final_df))
print("Saved:", OUTPUT_FILE)