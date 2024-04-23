import pandas as pd

# Read the two CSV files
artifacts = pd.read_csv("artifacts.csv", dtype={"artifact_id": "Int64"}, na_values=[""])
assets = pd.read_csv("assets.csv", dtype={"artifact_id": "Int64"}, na_values=[""])

# Drop rows with NA values in the 'artifact_id' column
artifacts.dropna(subset=["artifact_id"], inplace=True)
assets.dropna(subset=["artifact_id"], inplace=True)

df = pd.merge(artifacts, assets, on="artifact_id", how="inner")

df = df[df["file_format"] == "jpg"]
df = df[
    [
        "artifact_id",
        "asset_type",
        "path",
        "artifact_type",
    ]
]

df["id"] = df["path"].str.extract(r"/([A-Z]\d+)[_\.]", expand=False)

translits = pd.read_csv("../3_cleaned_transliterations.csv")

df = pd.merge(translits, df, on="id", how="inner")

df.to_csv("translits_and_photos.csv", index=False)
