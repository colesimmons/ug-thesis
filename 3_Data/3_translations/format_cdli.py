import csv
import json

import pandas as pd

# Open and read the contents of the JSON file
data = []
for filename in ["cdli.json", "cdli2.json", "cdli3.json", "cdli4.json"]:
    with open(filename, "r") as file:
        data.extend(json.load(file))

# Create an empty list to store the tablet transcriptions
tablets = []

# Iterate through each tablet object
for tablet in data:
    genres = tablet.get("genres", [])
    genres = [g.get("genre") for g in genres]
    genres = [g.get("genre") for g in genres]
    genre = ", ".join(genres) if genres else "Unknown"

    period = tablet.get("period", {})
    period = period.get("period", "Unknown")

    if "inscription" not in tablet:
        continue
    inscription = tablet["inscription"].get("atf", "")
    if "#atf: lang sux" not in inscription:
        continue

    name = inscription.split(" ", 1)
    name = name[0].split("&", 1)[1]

    inscription_body = inscription.split("#atf: lang sux", 1)[1]

    lines = inscription_body.split("\n")

    translation = [line[8:].strip() for line in lines if line.startswith("#tr.en: ")]
    translation = "\n".join(translation)

    transliteration = [
        line.strip() for line in lines if not line.startswith("#tr.en: ")
    ]
    transliteration = "\n".join(transliteration)

    tablets.append(
        {
            "id": tablet.get("id", ""),
            "name": name,
            "transliteration": transliteration,
            "translation": translation,
            "period": period,
            "genre": genre,
        }
    )

df = pd.DataFrame(tablets)

# Save the DataFrame to a CSV file
df.to_csv("cdli.csv", index=False)


SPECIAL_TOKS_TO_REMOVE = {
    "<SURFACE>",
    "<COLUMN>",
    "<RULING>",
    "<BLANK_SPACE>",
}


def _rm_special_tokens(text):
    text_ = text
    for tok in SPECIAL_TOKS_TO_REMOVE:
        text_ = text_.replace(tok, "")
    return text_


def count_in_common_with_epsd2():
    # 2191 of 3656
    cdli_df = pd.read_csv("cdli.csv", encoding="utf-8")
    # Rename the "id" column to "name" to match the column name in cdli.csv
    cdli_df = cdli_df[["name", "translation"]]
    cdli_df = cdli_df.rename(columns={"name": "id"})
    print("Before dropping duplicates:", cdli_df.shape)
    cdli_df = cdli_df.drop_duplicates(subset=["id"])
    print("After dropping duplicates:", cdli_df.shape)

    train_df = pd.read_csv(
        "../1_glyphs_and_transliterations/outputs/train.csv", encoding="utf-8"
    )
    test_df = pd.read_csv(
        "../1_glyphs_and_transliterations/outputs/test.csv", encoding="utf-8"
    )
    val_df = pd.read_csv(
        "../1_glyphs_and_transliterations/outputs/validation.csv", encoding="utf-8"
    )

    for split, df_ in [
        ("train", train_df),
        ("test", test_df),
        ("validation", val_df),
    ]:
        joined = pd.merge(cdli_df, df_, on="id", how="inner")
        joined = joined[
            [
                "id",
                "period",
                "genre",
                "transliteration",
                "translation",
            ]
        ]
        joined["transliteration"] = joined["transliteration"].apply(_rm_special_tokens)
        joined.to_csv(f"{split}.csv", index=False, encoding="utf-8")
    return

    # Read the IDs from cdli.csv
    with open("cdli.csv", "r") as cdli_file:
        cdli_reader = csv.DictReader(cdli_file)
        cdli_ids = [row["id"] for row in cdli_reader]

    # Read the IDs from tablets.csv
    with open(
        "../1_glyphs_and_transliterations/outputs/5_with_glyphs.csv", "r"
    ) as tablets_file:
        tablets_reader = csv.DictReader(tablets_file)
        tablets_ids = [row["id"] for row in tablets_reader]

    # Count the number of IDs from cdli.csv that are present in tablets.csv
    count = sum(1 for id in cdli_ids if id in tablets_ids)

    # Print the count
    print(f"Number of IDs from cdli.csv present in tablets.csv: {count}")
    print(len(cdli_ids))


count_in_common_with_epsd2()
