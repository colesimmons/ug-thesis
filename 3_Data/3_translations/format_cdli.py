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


def count_in_common_with_epsd2():
    # 2191 of 3656

    # Read the IDs from cdli.csv
    with open("cdli.csv", "r") as cdli_file:
        cdli_reader = csv.DictReader(cdli_file)
        cdli_ids = [row["id"] for row in cdli_reader]

    # Read the IDs from tablets.csv
    with open("2_tablets.csv", "r") as tablets_file:
        tablets_reader = csv.DictReader(tablets_file)
        tablets_ids = [row["id"] for row in tablets_reader]

    # Count the number of IDs from cdli.csv that are present in tablets.csv
    count = sum(1 for id in cdli_ids if id in tablets_ids)

    # Print the count
    print(f"Number of IDs from cdli.csv present in tablets.csv: {count}")
    print(len(cdli_ids))
