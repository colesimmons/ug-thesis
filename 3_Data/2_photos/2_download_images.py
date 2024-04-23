import os

import pandas as pd
import requests

csv_file = "translits_and_photos.csv"
prefix = "https://cdli.mpiwg-berlin.mpg.de/"
output_dir = "photos/"
os.makedirs(output_dir, exist_ok=True)

df = pd.read_csv(csv_file)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

for _, row in df.iterrows():
    image_path = row["path"]
    image_url = prefix + image_path
    image_filename = os.path.basename(image_path)
    output_file = os.path.join(output_dir, image_filename)
    if os.path.exists(output_file):
        print(f"Skipping {image_filename} (already downloaded)")
        continue
    try:
        response = requests.get(image_url)
        with open(output_file, "wb") as file:
            file.write(response.content)

        print(f"Downloaded {image_filename}")
    except Exception as e:
        print(f"Error downloading {image_filename}: {str(e)}")
