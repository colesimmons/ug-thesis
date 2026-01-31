import pandas as pd


def read_cdli_csv():
    artifacts = pd.read_csv(
        "artifacts.csv", dtype={"artifact_id": "Int64"}, na_values=[""]
    )
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
    df.rename(columns={"asset_type": "image_type"}, inplace=True)
    df["path"] = df["path"].str.split("/").str[-1]
    # df["path"] = "https://sux-photos.s3.us-west-002.backblazeb2.com/" + df["path"]
    df.rename(columns={"path": "image"}, inplace=True)
    return df


cdli_df = read_cdli_csv()


def join_and_save(split):
    # dest_path = f"./outputs/{split}/{image_type}"
    # if not os.path.exists(dest_path):
    # os.makedirs(dest_path)

    glyphs_and_translits_df = pd.read_csv(
        f"../1_glyphs_and_transliterations/outputs/{split}.csv",
        low_memory=False,
    )

    # cdli_df_filtered = cdli_df[cdli_df["image_type"] == image_type]

    joined_df = pd.merge(glyphs_and_translits_df, cdli_df, on="id", how="inner")
    joined_df = joined_df[
        [
            "id",
            "glyphs",
            "image",
            "image_type",
            "period",
            "genre",
        ]
    ]
    joined_df.to_csv(f"{split}.csv", index=False, encoding="utf-8")

    for image_type in joined_df["image_type"].unique():
        image_type_df = joined_df[joined_df["image_type"] == image_type]
        image_type_df.drop(columns=["image_type"], inplace=True)
        image_type_df.to_csv(f"{split}_{image_type}.csv", index=False, encoding="utf-8")

    # for index, row in joined_df.iterrows():
    # filename = row["file_name"]
    # img_src_path = f"./photos/{filename}"
    # img_dst_path = f"{dest_path}/{filename}"
    # shutil.copy(img_src_path, img_dst_path)
    # print(f"Copied {img_src_path} to {img_dst_path}")

    # joined_df.to_csv(f"{dest_path}/metadata.csv", index=False)
    # all_df = pd.concat([all_df, joined_df]) if all_df else joined_df
    # all_df.to_csv("metadata.csv", index=False)


join_and_save("train")
join_and_save("test")
join_and_save("validation")
