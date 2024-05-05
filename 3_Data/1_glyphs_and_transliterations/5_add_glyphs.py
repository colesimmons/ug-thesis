import json
import re
from collections import Counter, defaultdict

import pandas as pd
from tqdm import tqdm

tqdm.pandas()


# TODO: Create list of tuples of reading and glyph

INFILE = "3_cleaned_transliterations.csv"
OUTFILE = "5_with_glyphs.csv"


# =============================================================================
# ===================== (0) MAPPINGS / CONSTANTS ==============================
# =============================================================================
MAPPINGS_DIR = "."
with open(f"{MAPPINGS_DIR}/morpheme_to_glyph_names.json", encoding="utf-8") as infile:
    MORPHEME_TO_GLYPH_NAMES = json.load(infile)

with open(f"{MAPPINGS_DIR}/glyph_name_to_glyph.json", encoding="utf-8") as infile:
    GLYPH_NAME_TO_UNICODE = json.load(infile)

GLYPH_NAMES = set(GLYPH_NAME_TO_UNICODE.keys())

GLYPH_NAMES_TO_READINGS = defaultdict(set)
for reading, glyph_names in MORPHEME_TO_GLYPH_NAMES.items():
    for glyph_name in glyph_names:
        GLYPH_NAMES_TO_READINGS[glyph_name].add(reading)
for k, v in GLYPH_NAMES_TO_READINGS.items():
    GLYPH_NAMES_TO_READINGS[k] = list(v)


SPECIAL_TOKENS = {
    "==SURFACE==",
    "==COLUMN==",
    "==BLANK_SPACE==",
    "==RULING==",
    "...",
    "\n",
    "<unk>",
}

UNK = "<unk>"


# =============================================================================
# =================== (1) TRANSLIT -> GLYPH NAMES =============================
# =============================================================================
def add_glyph_names(row):
    text = row["transliteration"]

    # Get it ready for tokenization
    # --------------------------------
    # Replace lines like (lugal uri₅{ki}ma) because the parens
    # mean that it may not actually be present
    text = re.sub(r"(\n\(lugal[^\n]*\))(?=\n)", "\n...", text)
    # ...(anything)... or ...(anything)\n -> ...
    text = re.sub(r"(\.\.\.\([^\n]*\)\.\.\.)", "...", text)
    # ...(anything)\n -> ...\n
    text = re.sub(r"(\.\.\.\([^\n]*\)\n)", "...\n", text)
    # Multiple lines of ... -> single ...
    text = re.sub(r"(\n\.\.\.)+", "\n...", text)

    text = text.replace("\n", " \n ")
    text = text.replace("...", " ... ")
    text = re.sub(r"\ +", " ", text)

    wordforms = [wf for wf in text.split(" ") if wf]
    wfs_and_glyph_names = [get_wordform_glyph_names(wf) for wf in wordforms]
    row["transliteration"] = " ".join([wf for wf, _ in wfs_and_glyph_names])
    row["glyph_names"] = " ".join([" ".join(names) for _, names in wfs_and_glyph_names])
    return row


# -------------------------------------------------------------
# ------------------ (1.1) WORDFORMS --------------------------
# -------------------------------------------------------------

# Do this here because we want to keep the numbers in the translit
NUMBERS_TO_MORPHEMES = {
    "1/2": "1/2(diš)",
    "1/3": "1/3(diš)",
    "1/4": "1/3(iku)",
    "2/3": "2/3(diš)",
    "5/6": "5/6(diš)",
    "1": "1(diš)",
    "2": "2(diš)",
    "3": "3(diš)",
    "4": "4(diš)",
    "5": "5(diš)",
    "6": "6(diš)",
    "7": "7(diš)",
    "8": "8(diš)",
    "9": "9(diš)",
    "10": "1(u)",
    "11": "1(u) 1(diš)",
    "12": "1(u) 2(diš)",
    "14": "1(u) 4(diš)",
    "18": "1(u) 8(diš)",
    "20": "2(u)",
    "21": "2(u) 1(diš)",
    "23": "2(u) 3(diš)",
    "24": "2(u) 4(diš)",
    "25": "2(u) 5(diš)",
    "30": "3(u)",
    "36": "3(u) 6(diš)",
    "40": "4(u)",
    "50": "5(u)",
    "60": "6(u)",
    "600": "1(gešʾu)",
    "900": "1(gešʾu) 5(geš₂)",
    "3600": "1(šarʾu@c)",
    "36000": "1(šar₂)",
}

unk_morphemes_all = []
non_unk_morphemes_all = []


def get_wordform_glyph_names(wf: str) -> tuple[str, list[str]]:
    """
    Params: wf (str) a wordform
    Returns: tuple of updated wordform and list of glyph names
    """
    if wf in SPECIAL_TOKENS:
        return wf, [wf]

    if wf in NUMBERS_TO_MORPHEMES:
        wf_ = NUMBERS_TO_MORPHEMES[wf]
    elif wf.split("-", 1)[0] in NUMBERS_TO_MORPHEMES:
        # cases like "7-bi"
        split_ = wf.split("-", 1)
        wf_ = NUMBERS_TO_MORPHEMES[split_[0]] + "-" + split_[1]
    else:
        wf_ = wf

    morphemes = _split_wordform_into_morphemes(wf_)
    morphemes_and_possible_glyph_names = [
        _get_morpheme_glyph_names(m) for m in morphemes
    ]

    glyph_names = []
    for morpheme, possible_glyph_names in morphemes_and_possible_glyph_names:
        if len(possible_glyph_names) != 1:
            unk_morphemes_all.append(morpheme)
            glyph_names.append(UNK)
        else:
            non_unk_morphemes_all.append(morpheme)
            glyph_names.append(possible_glyph_names[0])

    return wf, glyph_names


def _split_wordform_into_morphemes(wf: str) -> list[str]:
    # uri₅{ki} -> [uri₅, {ki}]
    split_ = re.split(r"(\{.*?\})", wf)

    # Split on space, which should only happen if it
    # is one of the number replacements below
    split_ = [s.split(" ") for s in split_ if s]
    split_ = [s for sublist in split_ for s in sublist if s]  # Flatten

    # Split on hyphens, but not within parentheses
    split_ = [re.split(r"-(?![^(]*\))", s) for s in split_ if s]
    split_ = [s for sublist in split_ for s in sublist if s]  # Flatten

    # split and reverse any morphemes with colons
    # e.g. "mu-lu:gal-e" -> ["mu", "gal", "lu", "e"]
    split_ = [s.split(":")[::-1] if ":" in s else [s] for s in split_ if s]
    split_ = [s for sublist in split_ for s in sublist if s]  # Flatten

    return [s for s in split_ if s]


# -------------------------------------------------------------
# --------------- (1.2) MORPHEMES -----------------------------
# -------------------------------------------------------------

unk_morphemes_sign_name = []
unk_morphemes_num = []
unk_morpheme_other = []


NUMERIC_PATTERN = re.compile(r"^\d+(/\d+)?(\.\d+)?(\s*\([^)]+\))?$")


def _get_morpheme_glyph_names(morpheme: str) -> tuple[str, list[str]]:
    # only want to do this when it stands on its own
    morpheme = "ŋeš₂" if morpheme == "geš₂" else morpheme

    # Numbers
    if NUMERIC_PATTERN.match(morpheme):
        return _get_number_glyph_names(morpheme)

    # Already glyph name (reading uncertain)
    if morpheme in GLYPH_NAMES:
        return UNK, [morpheme]

    # {ki} -> ki
    morpheme = morpheme.replace("{", "").replace("}", "")

    # layup
    if morpheme in MORPHEME_TO_GLYPH_NAMES:
        return morpheme, MORPHEME_TO_GLYPH_NAMES[morpheme]

    # Sign name but that sign is not in the list.
    # But since sign names are based on a valid reading,
    # we can lowercase it and check again to get the more standard glyph name.
    # Note: the lowercase version may not be the right reading,
    # but we'll use it anyway...
    # It is the highest probability and introduces, I think,
    # a desirable amount of noise
    if morpheme.isupper():
        morpheme_ = morpheme.lower()
        if morpheme_.lower() in MORPHEME_TO_GLYPH_NAMES:
            return morpheme_, MORPHEME_TO_GLYPH_NAMES[morpheme_]
        # give up hope :/
        unk_morphemes_sign_name.append(morpheme)
        return UNK, []

    if "(" in morpheme and ")" in morpheme:
        split_ = morpheme.split("(")
        morpheme_, glyph_name_ = split_[0], split_[1].replace(")", "")

        if morpheme_ in MORPHEME_TO_GLYPH_NAMES:
            possible_glyph_names = MORPHEME_TO_GLYPH_NAMES[morpheme_]
            if len(possible_glyph_names) == 1:
                return morpheme_, possible_glyph_names
            if glyph_name_ in possible_glyph_names:
                return morpheme_, [glyph_name_]

        if glyph_name_ in GLYPH_NAMES_TO_READINGS:
            possible_readings = GLYPH_NAMES_TO_READINGS[glyph_name_]
            if len(possible_readings) == 1:
                return possible_readings[0], [glyph_name_]

    unk_morpheme_other.append(morpheme)
    return morpheme, []


def _get_number_glyph_names(morpheme: str) -> list[str]:

    if morpheme in MORPHEME_TO_GLYPH_NAMES:
        return morpheme, MORPHEME_TO_GLYPH_NAMES[morpheme]
    if morpheme.lower() in MORPHEME_TO_GLYPH_NAMES:
        return morpheme.lower(), MORPHEME_TO_GLYPH_NAMES[morpheme.lower()]
    if morpheme in GLYPH_NAMES:
        return morpheme, [morpheme]

    unk_morphemes_num.append(morpheme)
    return morpheme, []


# =============================================================================
# ==================== (2) GLYPH NAMES -> GLYPHS ==============================
# =============================================================================


glyph_names_not_in_map = []
glyph_names_no_unicode = []
glyph_names_found_unicode = []


def add_glyphs(row):
    glyph_names = row["glyph_names"]
    glyphs = ""
    for glyph_name in glyph_names.split(" "):
        if glyph_name == "":
            continue
        unicode = _glyph_name_to_unicode(glyph_name)
        glyphs += unicode
    row["glyphs"] = glyphs.strip()
    return row


def _glyph_name_to_unicode(glyph_name: str) -> str:
    if glyph_name in SPECIAL_TOKENS:
        return glyph_name

    if glyph_name not in GLYPH_NAME_TO_UNICODE:
        glyph_names_not_in_map.append(glyph_name)
        return UNK

    unicode = GLYPH_NAME_TO_UNICODE[glyph_name]
    if not unicode:
        glyph_names_no_unicode.append(glyph_name)
        return UNK

    glyph_names_found_unicode.append(glyph_name)
    return unicode


# =============================================================================
# =============================== MAIN ========================================
# =============================================================================
SIGN_LIST_REPLACEMENTS = {
    "BAU377": "GIŠ",  # technically GIŠ~v...
    "KWU147": "LIL",
    "KWU354": "LUM",
    "KWU636": "KU₄",
    "KWU777": "ŠITA",
    "KWU844": "|E₂×AŠ@t|",
    "LAK060": "|UŠ×TAK₄|",
    "LAK085": "|SI×TAK₄|",
    "LAK173": "KAD₅",
    "LAK175": "SANGA₂",
    "LAK218": "|ZU&ZU.SAR|",
    "LAK449": "|NUNUZ.AB₂|",
    "LAK524": "|ZUM×TUG₂|",
    "LAK589": "GISAL",
    "LAK672a": "UŠX",
    "LAK672b": "MUNSUB",
    "LAK720": "|LAK648×(PAP.PAP.LU₃)|",
    "LAK769": "|LAGAB×AN|",
    "LAK777": "|DAG.KISIM₅×UŠ|",
}

SIGN_NAME_REPLACEMENTS = {
    "(ŠE.1(AŠ))": "(ŠE.AŠ)",
    "(ŠE.2(AŠ))": "(ŠE.AŠ.AŠ)",
    "|E₂.BALAG|": "|KID.BALAG|",
    "BAD₃": "|EZEN×BAD|",
    "BIL₂": "NE@s",
    "DU₈": "DUH",
    "ERIM": "ERIN₂",
    "GAG": "KAK",
    "GIN₂": "DUN₃@g",
    "GU₄": "GUD",
    "ITI": "|UD×(U.U.U)|",
    "MUNUS": "SAL",
    "NIG₂": "GAR",
    "SILA₄": "|GA₂×PA|",
    "SIG₇": "IGI@g",
    "TUR₃": "|NUN.LAGAR|",
    "UH₃": "KUŠU₂",
    "U₈": "|LAGAB×(GUD&GUD)|",
}

# Remember that this comes after the above replacements,
# so some of the parenthetical values have already been replaced
READING_PLUS_SIGN_NAME_REPLACEMENTS = {
    "ad₆ ": "ad₆(|LU₂.LAGAB×U|) ",
    "dabₓ(|LAGAB×(GUD&GUD)|)": "dibₓ(|LAGAB×(GUD&GUD)|)",
    "erinₓ(KWU896)": "erenₓ(KWU896)",
    "gurₓ(|ŠE.KIN|)še₃": "gurₓ(|ŠE.KIN|)-še₃",
    "gurumₓ(|IGI.ERIM|)": "gurum₂",
    "ilduₓ(NAGAR)": "nagar",
    "itiₓ(|UD@s×BAD|)": "iti₂(|UD@s×BAD|)",
    "kuₓ(KU₄)": "ku₄",
    "lumₓ(LUM)": "lum",
    "mudₓ(|NUNUZ.AB₂|)": "mud₃(|NUNUZ.AB₂|)",
    "sangaₓ(|ŠID.GAR|)": "saŋŋaₓ(|ŠID.GAR|)",
    "šaganₓ(AMA)": "daŋal",
    "šitaₓ(ŠITA)": "šita",
    "tabₓ(MAN)": "tab₄",
    "umbinₓ(|UR₂×KID₂|)": "umbin(|UR₂×KID₂|)",
    "ušurₓ(|LAL₂×TUG₂|)": "ušurₓ(|LAL₂.TUG₂|)",
    "ugaₓ(NAGA)": "uga₃",
    "zeₓ(SIG₇)": "ziₓ(IGI@g)",
}

READING_REPLACEMENTS = {
    "babila": "babilim",
    "eri₁₃": "ere₁₃",
    "eriš₂": "ereš₂",
    "šu+nigin₂": "šuniŋin",
    "šu+nigin": "šuniŋin",
    "+...": "...",
    "...+": "...",
    "@c": "",
    "@t": "",
    "@v": "",
    "@90": "",
}

# As far as I can tell, there are at most 2 ways to do fractions
NUM_REPLACEMENTS = {
    "1/2(aš)": "1/2",
    "1/3(aš)": "1/3",
    "1/4(aš)": "1/4",
    "2/3(aš)": "2/3",
    "5/6(aš)": "5/6",
}

FINAL_REPLACEMENTS = {
    "||LAGAB×(GUD&GUD)|+HUL₂|": "|LAGAB×(GUD&GUD)+HUL₂|",
    "||EZEN×BAD|.AN|": "|EZEN×BAD.AN|",
    "|NINDA₂×(ŠE.2(AŠ@c))|": "|NINDA₂×(ŠE.AŠ.AŠ)|",
}

ALL_REPLACEMENTS = [
    SIGN_LIST_REPLACEMENTS,
    SIGN_NAME_REPLACEMENTS,
    READING_PLUS_SIGN_NAME_REPLACEMENTS,
    READING_REPLACEMENTS,
    NUM_REPLACEMENTS,
    FINAL_REPLACEMENTS,
]


def _print_report(x, title):
    print()
    print(f"----- {title} -----")
    counter = Counter(x)
    top_ = counter.most_common(20)
    for token, count in top_:
        print(f" > {token} – {count}")
    print("Total: ", len(x))


def main():
    df = pd.read_csv(INFILE).fillna("")

    # Drop "transliteration" column
    df = df.drop(columns=["transliteration"])

    # Rename transliteration_clean to transliteration
    df = df.rename(columns={"transliteration_clean": "transliteration"})

    # Replace some of the glyph names already present in the transliteration
    # (used when reading is uncertain) with more standard equivalents.
    for replacements in ALL_REPLACEMENTS:
        for k, v in replacements.items():
            df["transliteration"] = df["transliteration"].str.replace(k, v, regex=False)

    # ------------------------------------------
    # -------- TRANSLIT -> GLYPH NAMES ---------
    # ------------------------------------------
    print()
    print("Adding glyph names...")
    df = df.progress_apply(add_glyph_names, axis=1)
    print("Done!")

    num_unk_morphemes = len(unk_morphemes_all)
    num_non_unk_morphemes = len(non_unk_morphemes_all)
    num_all_morphemes = num_unk_morphemes + num_non_unk_morphemes
    pct_unk = round(num_unk_morphemes / num_all_morphemes * 100, 2)
    pct_non_unk = round(num_non_unk_morphemes / num_all_morphemes * 100, 2)
    print()
    print(f"# of morphemes unable to convert: {num_unk_morphemes} ({pct_unk}%)")
    print(
        f"# of morphemes successfully converted: {num_non_unk_morphemes} ({pct_non_unk}%)"
    )
    print()

    print("Reasons for inability to convert:")
    _print_report(unk_morphemes_sign_name, "UNK SIGN NAMES")
    _print_report(unk_morphemes_num, "UNK NUMBERS")
    _print_report(unk_morpheme_other, "UNK OTHER")

    replace = {
        "UN": "KALAM@g",
        "ŠITA₂": "|ŠITA.GIŠ|",
        "|ŠU₂.3xAN|": "|ŠU₂.3×AN|",
        "DE₂": "|UMUM×KASKAL|",
    }
    for k, v in replace.items():
        df["glyph_names"] = df["glyph_names"].str.replace(
            f" {k} ", f" {v} ", regex=False
        )

    # -----------------------------------------
    # ---------- GLYPH NAMES -> GLYPHS --------
    # -----------------------------------------
    print()
    print()
    print("Adding glyphs...")
    df = df.progress_apply(add_glyphs, axis=1)
    print("Done!")

    num_unable_to_convert = len(glyph_names_not_in_map) + len(glyph_names_no_unicode)
    num_converted = len(glyph_names_found_unicode)
    num_total = num_unable_to_convert + num_converted
    pct_unable_to_convert = round(num_unable_to_convert / num_total * 100, 2)
    pct_converted = round(num_converted / num_total * 100, 2)
    print()
    print(
        f"# of names unable to convert: {num_unable_to_convert} ({pct_unable_to_convert}%)"
    )
    print(f"# of names successfully converted: {num_converted} ({pct_converted}%)")
    print()

    print("Reasons for inability to convert:")
    _print_report(glyph_names_not_in_map, "NAME NOT IN glyph_name_to_glyph.json")
    _print_report(glyph_names_no_unicode, "NO UNICODE")

    # -----------------------------------------
    # -------------- POSTPROCESS --------------
    # -----------------------------------------
    df["transliteration"] = df["transliteration"].str.replace(" \n ", "\n")
    df["transliteration"] = df["transliteration"].str.replace(" ...", "...")
    df["transliteration"] = df["transliteration"].str.replace("... ", "...")

    print()
    print("Dropping rows with identical transliterations...")
    # uncomment below to see which rows
    # print(df[df["transliteration"].map(df["transliteration"].value_counts() > 1)])
    prev_num_rows = len(df)
    df = df.drop_duplicates(subset=["transliteration"])
    num_rows = len(df)
    print(f"Rows dropped: {prev_num_rows - num_rows}")
    print(f"New number of rows: {num_rows}")
    print()

    print()
    print("Dropping rows with identical glyphs...")
    # uncomment below to see which rows
    # print(df[df["glyphs"].map(df["glyphs"].value_counts() > 1)])
    prev_num_rows = len(df)
    df = df.drop_duplicates(subset=["glyphs"])
    num_rows = len(df)
    print(f"Rows dropped: {prev_num_rows - num_rows}")
    print(f"New number of rows: {num_rows}")
    print()

    new_row_order = [
        "id",
        "period",
        "genre",
        "transliteration",
        "glyph_names",
        "glyphs",
    ]
    # Reorganize rows
    df = df[new_row_order]

    # -----------------------------------------
    # ----------------- STATS -----------------
    # -----------------------------------------
    # Count glyphs
    def _count_glyph(glyphs):
        for special in SPECIAL_TOKENS:
            glyphs = glyphs.replace(special, "")
        glyphs = glyphs.replace(" ", "")
        return len(glyphs)

    # print total glyph count
    print("Total glyphs:", df["glyphs"].map(_count_glyph).sum())

    # -----------------------------------------
    # ----------------- WRITE -----------------
    # -----------------------------------------
    print(f"Writing to {OUTFILE}...")
    df.to_csv(OUTFILE, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
