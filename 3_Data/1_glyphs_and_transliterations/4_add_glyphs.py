import json
import re
from collections import Counter
from enum import Enum
from typing import Optional, Tuple

import pandas as pd
from sumeripy import corpora as corpora_
from tqdm import tqdm

tqdm.pandas()


INFILE = "3_cleaned_transliterations.csv"
OUTFILE = "4_with_glyphs.csv"

# TODO: Create list of tuples of reading and glyph

with open("./data/reading_to_glyph.json", encoding="utf-8") as infile:
    READING_TO_GLYPH = json.load(infile)

with open("./data/reading_to_glyph_name.json", encoding="utf-8") as infile:
    data = json.load(infile)
    READING_TO_GLYPH_NAME = data["index"]

with open("./data/glyph_name_to_glyph.json", encoding="utf-8") as infile:
    GLYPH_NAME_TO_GLYPH = json.load(infile)

with open("./data/glyph_to_glyph_name.json", encoding="utf-8") as infile:
    GLYPH_TO_GLYPH_NAME = json.load(infile)


class SpecialToken(Enum):
    SURFACE = "<SURFACE>"
    MISSING_LINES = "<MISSING_LINES>"
    MISSING = "<MISSING>"
    NUM = "<NUM>"
    NEWLINE = "\n"
    UNK = "<unk>"


SPECIAL_TOKENS = {member.value for member in SpecialToken}

# =============================================================================
# ========================= TRANSLIT -> GLYPHS ================================
# =============================================================================


corpus_unk = []
corpus_nums = []


def _reading_to_glyph(reading: str) -> Optional[str]:
    to_convert = {
        "₀": "0",
        "₁": "1",
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
        "ₓ": "x",
        "h": "ḫ",
    }
    for replace, with_ in to_convert.items():
        reading = reading.replace(replace, with_)
    if reading in READING_TO_GLYPH:
        return READING_TO_GLYPH[reading]
    return None


def _get_glyph_for_reading(reading: str) -> Optional[Tuple[str, str, str]]:
    """Returns (updated_reading, glyph_unicode, glyph_name)"""

    MISC = {"šu+nigin₂": "šuniŋin"}
    if reading in MISC:
        reading = MISC[reading]

    if reading in SPECIAL_TOKENS:
        return reading, reading, reading

    reading = reading.replace("@c", "")
    reading = reading.replace("@t", "")

    # Reading is already glyph name
    if reading in GLYPH_NAME_TO_GLYPH:
        glyph = GLYPH_NAME_TO_GLYPH.get(reading)
        if glyph:
            return reading, glyph, reading

    # Reading to glyph to glyph name
    for reading_ in [reading, reading.lower(), reading.upper()]:
        glyph = _reading_to_glyph(reading_)
        if glyph:
            glyph_name = GLYPH_TO_GLYPH_NAME.get(glyph)
            if glyph == "𒌤":
                return reading, glyph, "UMUM×KASKAL"
            if glyph_name:
                return reading, glyph, glyph_name

    # Reading to glyph name to glyph
    if reading in READING_TO_GLYPH_NAME:
        glyph_name = READING_TO_GLYPH_NAME[reading]
        glyph = GLYPH_NAME_TO_GLYPH.get(glyph_name)
        if glyph:
            return reading, glyph, glyph_name

    # n
    if reading == "n":
        return (
            SpecialToken.MISSING.value,
            SpecialToken.MISSING.value,
            SpecialToken.MISSING.value,
        )

    # Numbers
    match = re.search(r"^([0-9]*/?[0-9]+)\((.*?)\)$", reading)
    if match:
        quantity = match.group(1)
        reading_ = match.group(2)

        glyph = _reading_to_glyph(reading_)
        if glyph:
            glyph_name = GLYPH_TO_GLYPH_NAME.get(glyph)
            if glyph_name:
                return reading, f"{quantity}({glyph})", f"{quantity}({glyph_name})"

        glyph_name = READING_TO_GLYPH_NAME.get(reading_)
        if glyph_name:
            glyph = GLYPH_NAME_TO_GLYPH.get(glyph_name)
            if glyph:
                return reading, f"{quantity}({glyph})", f"{quantity}({glyph_name})"

        return None

    # Parens, e.g. zu(SU)
    match = re.search(r"^(\S*?)\((.*?)\)$", reading)
    if match:
        before_parens = match.group(1)
        inside_parens = match.group(2)

        if inside_parens == "$erasure$":
            return (
                SpecialToken.MISSING.value,
                SpecialToken.MISSING.value,
                SpecialToken.MISSING.value,
            )

        inside_parens_glyph = GLYPH_NAME_TO_GLYPH.get(inside_parens)
        if inside_parens_glyph:
            return before_parens, inside_parens_glyph, inside_parens

        before_parens_glyph = _reading_to_glyph(before_parens)
        if before_parens_glyph:
            glyph_name = GLYPH_TO_GLYPH_NAME.get(before_parens_glyph)
            if glyph_name:
                return before_parens, before_parens_glyph, glyph_name

    return None


def _add_glyphs(row):
    text = row["transliteration_clean"]

    all_readings = []
    all_glyphs = []
    all_glyph_names = []

    num_unk = 0
    num_special = 0
    num_glyphs = 0

    for seq in text.split(" "):
        seq_readings = []
        seq_glyphs = []
        seq_glyph_names = []

        for reading in seq.split("-"):
            reading = reading.replace("{", "").replace("}", "")

            # Has one paren but not the other
            if (")" in reading and "(" not in reading) or (
                ")" not in reading and "(" in reading
            ):
                reading = reading.replace("(", "").replace(")", "")

            if reading == "" or reading == "|":
                continue

            reading_data = _get_glyph_for_reading(reading)
            if reading_data is None:
                corpus_unk.append(reading)
                seq_readings.append(SpecialToken.UNK.value)
                seq_glyphs.append(SpecialToken.UNK.value)
                seq_glyph_names.append(SpecialToken.UNK.value)
                num_unk += 1
            else:
                reading_, glyph_unicode, glyph_name = reading_data
                seq_readings.append(reading_)
                seq_glyphs.append(glyph_unicode)
                seq_glyph_names.append(glyph_name)
                if glyph_unicode in SPECIAL_TOKENS:
                    num_special += 1
                else:
                    num_glyphs += 1

        all_readings.append("-".join(seq_readings))
        all_glyphs.append(" ".join(seq_glyphs))
        all_glyph_names.append(" ".join(seq_glyph_names))

    updated_translit = " ".join(all_readings)
    glyphs = " ".join(all_glyphs)
    glyph_names = " ".join(all_glyph_names)

    row["glyphs"] = glyphs
    row["glyph_names"] = glyph_names
    row["transliteration_final"] = updated_translit

    row["num_unk"] = num_unk
    row["num_special_toks"] = num_special
    row["num_glyphs"] = num_glyphs
    return row


# =============================================================================
# =============================================================================


def _remove_space_around_missing(text):
    text = re.sub(
        rf"( )+{SpecialToken.MISSING.value}( )+", SpecialToken.MISSING.value, text
    )
    return text


def _remove_space_around_newline(text: str):
    text = re.sub(r"( )+(\n)( )+", "\n", text)
    return text


def _remove_all_spaces(text: str):
    text = text.replace(" ", "")
    return text


def _add_newline_tok(text: str):
    text = text.replace("<SURFACE>\n", "<SURFACE>")
    text = text.replace("\n", "<NEWLINE>")
    return text


def _process_corpus(corpus_name: str):
    # Load corpus
    df = pd.read_csv(INFILE).fillna("")

    # Add glyphs
    df = df.progress_apply(_add_glyphs, axis=1)

    # Remove spaces around <MISSING> and \n
    df["transliteration_final"] = df["transliteration_final"].apply(
        _remove_space_around_missing
    )
    df["glyphs"] = df["glyphs"].apply(_remove_all_spaces)
    for key in ("transliteration_final", "glyph_names"):
        df[key] = df[key].apply(_remove_space_around_newline)
    for key in ("transliteration_final", "glyphs", "glyph_names"):
        df[key] = df[key].apply(_add_newline_tok)

    num_rows = len(df)
    num_glyphs = df["num_glyphs"].sum()
    num_special_toks = df["num_special_toks"].sum()
    num_unk = df["num_unk"].sum()

    # drop # glyphs
    # df = df.drop(columns=["num_glyphs"])
    print(f"Writing to {OUTFILE}...")
    df.to_csv(OUTFILE, index=False, encoding="utf-8")

    return df, num_rows, num_glyphs, num_special_toks, num_unk


# =============================================================================
# =============================================================================


if __name__ == "__main__":
    all_unk = []
    all_num_texts = 0
    all_num_glyphs = 0
    all_num_special_toks = 0

    corpora = corpora_.list()
    for corpus_name in corpora:
        corpus_unk = []
        corpus_num = []
        print()
        print(f"---------- {corpus_name} ----------")
        print(f"Adding glyphs for {corpus_name}...")
        df, num_rows, num_glyphs, num_special_toks, num_unk = _process_corpus(
            corpus_name
        )
        print()

        all_unk += corpus_unk
        all_num_texts += num_rows
        all_num_glyphs += num_glyphs
        all_num_special_toks += num_special_toks

        print("Num texts: ", num_rows)
        print("Found: ", num_glyphs)
        print("Special tokens: ", num_special_toks)
        print("Could not find: ", len(corpus_unk))
        print("Top 20 missing:")
        counter = Counter(corpus_unk)
        top_20 = counter.most_common(20)
        for token, count in top_20:
            print(f" > {token} – {count}")

        # print(f"Num rows: {num_rows}")
        # print(f"Num glyphs: {num_glyphs}")
        print()

    print("Num texts: ", all_num_texts)
    print("Found: ", all_num_glyphs)
    print("Special tokens: ", all_num_special_toks)
    print("Could not find: ", len(all_unk))
    print()
    print("> =========")
    print(">   UNK    ")
    print("> =========")
    counter = Counter(all_unk).most_common(50)
    # counter = sorted(counter, key=lambda x: x[1], reverse=True)
    for token, count in counter:
        print(f"> {token} – {count}")
