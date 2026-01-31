import json
import os

from datasets import Dataset


def load_json_files():
    data = []
    for filename in os.listdir("./generated"):
        if filename.endswith(".json"):
            filepath = os.path.join("./generated", filename)
            with open(filepath, "r") as file:
                json_data = json.load(file)
                if json_data.get("translation", "") != "":
                    data.append(json_data)
    return data


json_data = load_json_files()
dataset = Dataset.from_list(json_data)
print(dataset)
# dataset.to_csv("generated.csv")
# print(dataset)
dataset.push_to_hub("colesimmons/SumTablets_English-augmented")
