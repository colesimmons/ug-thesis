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
# ====================== MAPPINGS / CONSTANTS =================================
# =============================================================================
MAPPINGS_DIR = "."
with open(f"{MAPPINGS_DIR}/wordform_to_glyph_names.json", encoding="utf-8") as infile:
    WORDFORM_TO_GLYPH_NAMES = json.load(infile)

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

NUMBERS_TO_TRANSLIT = {
    "1/2": "1/2(diš)",
    "1/3": "1/3(diš)",
    "2/3": "2/3(diš)",
    "5/6": "2/3(diš)",
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
    "𒎙𒐊": "25",
    "600": "1(gešʾu)",
    "900": "1(gešʾu) 5(geš₂)",
    "3600": "1(šarʾu@c)",
    "36000": "1(šar₂)",
}

# As far as I can tell, there are at most 2 ways to do fractions
UNIT_CONVERSIONS = {
    "1/2(aš)": "1/2(diš)",
    "1/3(aš)": "1/3(diš)",
    "2/3(aš)": "2/3(diš)",
    "1/4(aš)": "1/4(iku)",
    "5/6(aš)": "2/3(diš)",
}


NUMERIC_PATTERN = re.compile(r"^\d+(/\d+)?(\.\d+)?(\s*\([^)]+\))?$")

# Places where convention has changed since the transliterations were made
MORPHEME_REPLACEMENTS = {
    # reading -> reading
    "babila": "babilim",
    "eri₁₃": "ere₁₃",
    "eriš₂": "ereš₂",
    "ilduₓ(NAGAR)": "nagar",
    "šaganₓ(AMA)": "daŋal",
    "šu+nigin₂": "šuniŋin",
    "šu+nigin": "šuniŋin",
    # reading(SIGN) -> reading | reading(SIGN)
    "ad₆": "ad₆(|LU₂.LAGAB×U|)",
    "dabₓ(|LAGAB×(GUD&GUD)|)": "dibₓ(|LAGAB×(GUD&GUD)|)",
    "erinₓ(KWU896)": "erenₓ(KWU896)",
    "gurumₓ(|IGI.ERIM|)": "gurum₂",
    "itiₓ(|UD@s×BAD|)": "iti₂(|UD@s×BAD|)",
    "kuₓ(KU₄)": "ku₄",
    "lumₓ(KWU354)": "lum",
    "mudₓ(LAK449)": "mud₃(LAK449)",
    "sangaₓ(|ŠID.GAR|)": "saŋŋaₓ(|ŠID.GAR|)",
    "šitaₓ(KWU777)": "šita",
    "tabₓ(MAN)": "tab₄",
    "umbinₓ(|UR₂×KID₂|)": "umbin(|UR₂×KID₂|)",
    "ušurₓ(|LAL₂×TUG₂|)": "ušurₓ(|LAL₂.TUG₂|)",
    "ugaₓ(NAGA)": "uga₃",
    "zeₓ(SIG₇)": "ziₓ(IGI@g)",
    # SIGN -> SIGN
    "(ŠE.1(AŠ))": "(ŠE.AŠ)",
    "(ŠE.2(AŠ))": "(ŠE.AŠ.AŠ)",
    "||EZEN×BAD|.AN|": "|EZEN×BAD.AN|",
    "|E₂.BALAG|": "|KID.BALAG|",
    "|NINDA₂×(ŠE.2(AŠ@c))|": "|NINDA₂×(ŠE.AŠ.AŠ)|",
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
    # same as above but must come after
    "||LAGAB×(GUD&GUD)|+HUL₂|": "|LAGAB×(GUD&GUD)+HUL₂|",
    # SIGN LIST -> SIGN
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


# =============================================================================
# ======================= TRANSLIT -> GLYPH NAMES =============================
# =============================================================================
def _split_wordform_into_morphemes(wf: str) -> list[str]:
    pattern = r"(\{.*?\})"
    split_ = re.split(pattern, wf)
    split_ = [s for s in split_ if s]
    # Split on hyphens, but not within parentheses
    split_ = [re.split(r"-(?![^(]*\))", s) for s in split_]
    # flatten
    split_ = [s for sublist in split_ for s in sublist]
    split_ = [s for s in split_ if s]
    return split_


# Any of the values is None
unk_sign_names = []
unk_nums_ = []
unk_w_colon_ = []
unk_other_ = []


def _morpheme_to_glyph_names(morpheme: str) -> tuple[str, list[str]]:
    # 7 -> 7(diš)
    if morpheme in NUMBERS_TO_TRANSLIT:
        morpheme = NUMBERS_TO_TRANSLIT[morpheme]

    if morpheme == "geš₂":
        morpheme = "ŋeš₂"

    # Numbers
    if morpheme[0].isdigit() and NUMERIC_PATTERN.match(morpheme):
        for mod in ("", "@90", "@c", "@t", "@v"):
            morpheme = morpheme.replace(mod, "")
        if morpheme in UNIT_CONVERSIONS:
            morpheme = UNIT_CONVERSIONS[morpheme]

        if morpheme in MORPHEME_TO_GLYPH_NAMES:
            return morpheme, MORPHEME_TO_GLYPH_NAMES[morpheme]
        if morpheme in GLYPH_NAMES:
            if "(DIŠ)" in morpheme or "(AŠ)" in morpheme:
                return morpheme.lower(), [morpheme]
            return morpheme, [morpheme]
        unk_nums_.append(morpheme)

    # already glyph name, reading uncertain
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
    # but we'll use it anyway..a
    # It is the highest probability and introduces, I think,
    # a desirable amount of noise
    if morpheme.isupper():
        morpheme_ = morpheme.lower()
        if morpheme_.lower() in MORPHEME_TO_GLYPH_NAMES:
            return morpheme_, MORPHEME_TO_GLYPH_NAMES[morpheme_]
        # give up hope :/
        unk_sign_names.append(morpheme)
        return UNK, []

    elif ":" in morpheme:
        unk_w_colon_.append(morpheme)

    elif "(" in morpheme and ")" in morpheme:
        split_ = morpheme.split("(")
        morpheme_ = split_[0]
        glyph_name_ = split_[1].replace(")", "")

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
    unk_other_.append(morpheme)
    return morpheme, []


all_unk = []
could_add = []


def wordform_to_morphemes_and_glyph_names(wf: str) -> tuple[str, list[str]]:
    """
    Params: wf (str) a wordform
    Returns: tuple of updated wordform and list of glyph names
    """

    if wf.startswith("+"):
        wf = wf[1:]
    if wf.endswith("+"):
        wf = wf[:-1]

    # 1) It's a special token
    # --------------------------------
    if wf in SPECIAL_TOKENS:
        return wf, [wf]

    # 2) Standardize and split the wordform into morphemes
    # --------------------------------
    for k, v in MORPHEME_REPLACEMENTS.items():
        wf = wf.replace(k, v)
    morphemes = _split_wordform_into_morphemes(wf)

    # 3) Get possible glyph names for each morpheme
    # --------------------------------
    morphemes_and_possible_glyph_names = [
        _morpheme_to_glyph_names(morpheme) for morpheme in morphemes
    ]

    # 4) If all morphemes have only one possible glyph name, we're done
    # --------------------------------
    glyph_names = []
    for morpheme, possible_glyph_names in morphemes_and_possible_glyph_names:
        if len(possible_glyph_names) != 1:
            all_unk.append(morpheme)
            glyph_names.append(UNK)
        else:
            could_add.append(morpheme)
            glyph_names.append(possible_glyph_names[0])
    return wf, glyph_names


def add_glyph_names(row):
    text = row["transliteration_clean"]

    # Gets it ready for tokenization
    text = text.replace("\n", " \n ")
    text = text.replace("...", " ... ")
    text = re.sub(r"(\n\(lugal[^\n]*\))+", "\n...", text)
    text = text.replace("gurₓ(|ŠE.KIN|)še₃", "gurₓ(|ŠE.KIN|)-še₃")
    text = re.sub(r"\ +", " ", text)

    translit = ""
    glyph_names = ""

    for wf in text.split(" "):
        if wf == "":
            continue
        new_wf, wf_glyph_names_ = wordform_to_morphemes_and_glyph_names(wf)
        translit += new_wf + " "
        glyph_names += " ".join(wf_glyph_names_) + " "

    row["glyph_names"] = glyph_names.strip()
    row["transliteration"] = translit.strip()
    return row


# =============================================================================
# ======================= GLYPH NAMES -> GLYPHS ===============================
# =============================================================================


unk_names = []
no_unicode = []
found_unicode = []


def _glyph_name_to_unicode(glyph_name: str) -> str:
    if glyph_name in SPECIAL_TOKENS:
        return glyph_name

    if glyph_name not in GLYPH_NAME_TO_UNICODE:
        unk_names.append(glyph_name)
        return UNK

    unicode = GLYPH_NAME_TO_UNICODE[glyph_name]
    if not unicode:
        no_unicode.append(glyph_name)
        return UNK

    found_unicode.append(glyph_name)
    return unicode


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


# =============================================================================
# =============================== MAIN ========================================
# =============================================================================
# TODO: get rid of wordform lookup
if __name__ == "__main__":
    # Load corpus
    df = pd.read_csv(INFILE).fillna("")

    # Add glyphs
    print("Adding glyph names...")
    df = df.progress_apply(add_glyph_names, axis=1)

    def _print_report(x, title):
        print()
        print(f"----- {title} -----")
        print(len(x))
        counter = Counter(x)
        top_20 = counter.most_common(50)
        for token, count in top_20:
            print(f" > {token} – {count}")

    _print_report(unk_sign_names, "UNK SIGN NAMES")
    _print_report(unk_w_colon_, "UNK W/ COLON")
    _print_report(unk_nums_, "UNK NUMBERS")
    _print_report(unk_other_, "UNK OTHER")

    print()
    print("Could not convert:", len(all_unk))
    print("Could convert:", len(could_add))
    print()

    df["glyph_names"] = df["glyph_names"].str.replace(" UN ", " KALAM@g ")
    df["glyph_names"] = df["glyph_names"].str.replace(" ŠITA₂ ", " |ŠITA.GIŠ| ")
    df["glyph_names"] = df["glyph_names"].str.replace(" LAK524 ", " |ZUM×TUG₂| ")
    df["glyph_names"] = df["glyph_names"].str.replace(" |ŠU₂.3xAN| ", " |ŠU₂.3×AN| ")
    df["glyph_names"] = df["glyph_names"].str.replace(" DE₂ ", " |UMUM×KASKAL| ")

    print("Adding glyphs...")
    df = df.progress_apply(add_glyphs, axis=1)

    _print_report(unk_names, "UNK NAMES")
    _print_report(no_unicode, "NO UNICODE")

    print()
    print("Could not convert:", len(unk_names))
    print("Had no unicode:", len(no_unicode))
    print("Could convert:", len(found_unicode))
    print()

    df["transliteration"] = df["transliteration"].str.replace(" \n ", "\n")
    df["transliteration"] = df["transliteration"].str.replace(" ...", "...")
    df["transliteration"] = df["transliteration"].str.replace("... ", "...")

    # see how many rows have the same transliteration
    print(
        "Rows with the same transliteration:",
        len(df) - len(df["transliteration"].unique()),
    )
    # print some examples
    print(df[df["transliteration"].map(df["transliteration"].value_counts() > 1)])
    # Drop duplicates
    df = df.drop_duplicates(subset=["transliteration"])
    print(
        "Rows with the same glyphs:",
        len(df) - len(df["glyphs"].unique()),
    )
    print(df[df["glyphs"].map(df["glyphs"].value_counts() > 1)])

    df = df[
        [
            "id",
            "period",
            "genre",
            "transliteration",
            "glyph_names",
            "glyphs",
        ]
    ]

    # Count glyphs
    def _count_glyph(glyphs):
        for special in SPECIAL_TOKENS:
            glyphs = glyphs.replace(special, "")
        glyphs = glyphs.replace(" ", "")
        return len(glyphs)

    # print total glyph count
    print("Total glyphs:", df["glyphs"].map(_count_glyph).sum())

    print(f"Writing to {OUTFILE}...")
    df.to_csv(OUTFILE, index=False, encoding="utf-8")
