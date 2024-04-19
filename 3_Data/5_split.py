import os

import pandas as pd
from constants import DATA_DIR, WITH_GLYPHS_DATA_DIR
from sklearn.model_selection import train_test_split


def _load_dataset_from_files():
    """
    So there is a reason this is not all done in, for e.g., huggingface datasets:

    I want to perform the train-test split before creating examples in the reverse direction.
    """

    # Get all the csv files in the 3_with_glyphs dir
    csv_files = [
        file for file in os.listdir(WITH_GLYPHS_DATA_DIR) if file.endswith(".csv")
    ]
    csv_files = [os.path.join(WITH_GLYPHS_DATA_DIR, file) for file in csv_files]

    # When we stratify by period, we will lump these together.
    # (first three are the same, last two have too few examples to stratify)
    group_together = {
        "",
        "Unknown",
        "Uncertain",
        "Early Dynastic I-II",
        "Pre-Uruk V",
        "fake",
    }

    # Load the csv files into a datafrane
    # Columns in resulting df: id, source, target, period
    dfs = []
    for file in csv_files:
        df = pd.read_csv(file, encoding="utf-8").fillna("")
        df = df.drop(columns=["transliteration", "transliteration_clean"])
        df = df[df["genre"] != "fake (modern)"]
        df.loc[df["period"].isin(group_together), "period"] = "Unknown"
        df.loc[df["genre"].isin({"", "uncertain"}), "genre"] = "Unknown"
        dfs.append(df)

    df = pd.concat(dfs)
    df = df.rename(columns={"transliteration_final": "transliteration"})

    # Remove duplicate IDs
    print("Removing duplicates...")
    print(f"Before removing duplicates: {len(df)}")
    df = df.drop_duplicates(subset=["id"], keep="first")
    print(f"After removing duplicates: {len(df)}")

    # Exclude administrative texts
    # df = df[df["genre"] != "Administrative"]

    df.to_csv(os.path.join(DATA_DIR, "all.csv"), index=False)

    # Split the dataframe into a train, test, and val sets
    # 95% train, 5% val, 5% test
    train_val_df, test_df = train_test_split(
        df, stratify=df["period"], test_size=0.05, random_state=42
    )
    train_df, val_df = train_test_split(
        train_val_df,
        stratify=train_val_df["period"],
        test_size=(5 / 95),
        random_state=42,
    )

    print(f"Train: {len(train_df)}")
    print(f"Test: {len(test_df)}")
    print(f"Val: {len(val_df)}")

    for name, df in (("Train", train_df), ("Test", test_df), ("Val", val_df)):
        # Print how many examples we have for each period and genre
        print()
        print(f"-- {name} --")
        print(df["period"].value_counts())
        print()
        print(df["genre"].value_counts())
        print()

    # Shuffle em up
    train_df = train_df.sample(frac=1).reset_index(drop=True)
    test_df = test_df.sample(frac=1).reset_index(drop=True)
    val_df = val_df.sample(frac=1).reset_index(drop=True)

    # Drop admin
    no_admin_train_df = train_df[train_df["genre"] != "Administrative"]
    no_admin_test_df = test_df[test_df["genre"] != "Administrative"]
    no_admin_val_df = val_df[val_df["genre"] != "Administrative"]

    for name, df in (
        ("Train", no_admin_train_df),
        ("Test", no_admin_test_df),
        ("Val", no_admin_val_df),
    ):
        # Print how many examples we have for each period and genre
        print()
        print(f"-- {name} (no admin) --")
        print(df["period"].value_counts())
        print()
        print(df["genre"].value_counts())
        print()

    # Drop extra columns
    cols_to_drop = [
        "subgenre",
        "num_unk",
        "num_special_toks",
        "num_glyphs",
    ]
    train_df = train_df.drop(columns=cols_to_drop)
    test_df = test_df.drop(columns=cols_to_drop)
    val_df = val_df.drop(columns=cols_to_drop)
    no_admin_train_df = no_admin_train_df.drop(columns=cols_to_drop)
    no_admin_test_df = no_admin_test_df.drop(columns=cols_to_drop)
    no_admin_val_df = no_admin_val_df.drop(columns=cols_to_drop)

    # Now for all sets, we want to duplicate the examples,
    # switch the source and target, and append them back to the original set
    # train_df_reverse = train_df.rename(columns={"source": "target", "target": "source"})
    # test_df_reverse = test_df.rename(columns={"source": "target", "target": "source"})
    # val_df_reverse = train_df.rename(columns={"source": "target", "target": "source"})
    # train_df = pd.concat([train_df, train_df_reverse]).reset_index(drop=True)
    # test_df = pd.concat([test_df, test_df_reverse]).reset_index(drop=True)

    # Write to csv
    train_df.to_csv(
        os.path.join(DATA_DIR, "train_all.csv"), index=False, encoding="utf-8"
    )
    test_df.to_csv(
        os.path.join(DATA_DIR, "test_all.csv"), index=False, encoding="utf-8"
    )
    val_df.to_csv(
        os.path.join(DATA_DIR, "validation_all.csv"), index=False, encoding="utf-8"
    )

    no_admin_train_df.to_csv(
        os.path.join(DATA_DIR, "train_no_admin.csv"), index=False, encoding="utf-8"
    )
    no_admin_test_df.to_csv(
        os.path.join(DATA_DIR, "test_no_admin.csv"), index=False, encoding="utf-8"
    )
    no_admin_val_df.to_csv(
        os.path.join(DATA_DIR, "validation_no_admin.csv"),
        index=False,
        encoding="utf-8",
    )

    # Small versions for model debugging
    small_train_df = train_df.head(5)
    small_test_df = test_df.head(5)
    small_val_df = val_df.head(5)

    small_train_df.to_csv(
        os.path.join(DATA_DIR, "train_small.csv"), index=False, encoding="utf-8"
    )
    small_test_df.to_csv(
        os.path.join(DATA_DIR, "test_small.csv"), index=False, encoding="utf-8"
    )
    small_val_df.to_csv(
        os.path.join(DATA_DIR, "validation_small.csv"), index=False, encoding="utf-8"
    )

    return


_load_dataset_from_files()
