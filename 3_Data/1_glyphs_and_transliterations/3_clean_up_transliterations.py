"""
This script cleans the transliterations in a new "transliteration_clean" column
(for easy comparison) and saves the result to a new csv file
"""

import re
from enum import Enum

import pandas as pd
from tqdm import tqdm

tqdm.pandas()

INFILE = "2_tablets.csv"
OUTFILE = "3_cleaned_transliterations.csv"


class SpecialToken(Enum):
    SURFACE = "<SURFACE>"
    MISSING_LINES = "<MISSING_LINES>"
    MISSING = "<MISSING>"
    NUM = "<NUM>"
    NEWLINE = "\n"


# =============================================================================
# ========================= CLEANING FUNCTIONS ================================
# =============================================================================
def _handle_angle_brackets(text):
    """
    Double angle brackets:
        - "The graphemes are present but must be excised for the sense."
        - We want to get rid of the brackets but keep the text (i.e. treat it like normal text)

    Single angle brackets:
        - "The graphemes must be supplied for the sense but are not present"
        - We want to get rid of these altogether
    """
    # --- DOUBLE ---
    text = text.replace("<<", "")
    text = text.replace(">>", "")

    # --- SINGLE ---
    text = re.sub(r"<[\s\S]*?>", "", text)
    return text


def _drop_linguistic_glosses(text):
    """
    Double curly braces.
        - "Linguistic glosses are defined for the purposes of this specification
          as glosses which give an alternative to the word(s) in question.
          Such alternatives are typically either variants or translations."
        - Get rid of em
    """
    text = re.sub(r"\{\{[\s\S]*?\}\}", "", text)
    return text


def _handle_partial_breakage(text):
    """
    ⸢abc⸣ = partially broken. We'll treat it as normal text.
    """
    text = text.replace("⸢", "")
    text = text.replace("⸣", "")
    return text


def _handle_complete_breakage(text):
    # Replace instances like {[d}sud₃] where the { and [ are in the wrong order
    text = re.sub(r"(\{\[).*?(\]\})", SpecialToken.MISSING.value, text)
    text = re.sub(r"(\{\[).*?(\}).*?(\])", SpecialToken.MISSING.value, text)
    text = re.sub(r"(\[).*?(\{).*?(\]\})", SpecialToken.MISSING.value, text)

    # Variations of X -> "X"
    text = text.replace("([x)]", SpecialToken.MISSING.value)
    text = text.replace("x", SpecialToken.MISSING.value)
    text = re.sub("( )*(-)*o( )*(-)*", f" {SpecialToken.MISSING.value} ", text)
    text = text.replace("(X)", SpecialToken.MISSING.value)

    # "X" -> <MISSING>
    text = re.sub("(X?( |-)+X)+", f" {SpecialToken.MISSING.value} ", text)

    # [abc def] -> <MISSING>
    text = re.sub(r"\[[\s\S]*?\]", SpecialToken.MISSING.value, text)

    # ... or (...) -> <MISSING>
    text = re.sub(r"\(?\.\.\.\)?", SpecialToken.MISSING.value, text)

    # Sequence of several <MISSING> -> a single <MISSING>
    text = re.sub(
        r"(( )*(-)*( )*(" + SpecialToken.MISSING.value + ")( )*(-)*( )*)+",
        f" {SpecialToken.MISSING.value} ",
        text,
    )

    # { <MISSING } -> <MISSING>
    text = re.sub(
        r"{( )*(" + SpecialToken.MISSING.value + ")( )*}",
        f" {SpecialToken.MISSING.value} ",
        text,
    )

    # |SIGN. <MISSING> | -> |SIGN.<MISSING>|
    match = re.search(
        r"|[A-Z]+( )+(" + SpecialToken.MISSING.value + ")( )+|",
        text,
    )
    if match:
        text = text.replace(match.group(), match.group().replace(" ", ""))

    # Sometimes brackets are not opened or closed (shortcoming of the EPSD data) # TODO
    text = text.replace("[", "")
    text = text.replace("]", "")

    return text


def _handle_semicolons(text):
    """Semicolons are used to separate lines in the transliteration."""
    text = text.replace(";", f" {SpecialToken.NEWLINE.value} ")
    return text


def _update_special_tokens(text):
    """
    $MISSING_LINES$ -> <MISSING_LINES>
    ==SURFACE== -> <SURFACE>
    """
    text = text.replace("$MISSING_LINES$", SpecialToken.MISSING_LINES.value)
    text = text.replace("==SURFACE==", SpecialToken.SURFACE.value)
    return text


def _add_hyphens_around_determinatives(text):
    text = text.replace("{", "-{")
    text = text.replace("}", "}-")
    return text


def _handle_vertical_bars(text):
    # Add hyphen after vertical bars
    text = re.sub(r"\|(.*?)\|", r"|\1|-", text)

    # If the last character before the closing bar is a hyphen, remove it
    text = re.sub(r"\|(.+)-\|", r"|\1|", text)
    return text


def _handle_parentheses(text):
    # Insert a hyphen after each closing parenthesis if the next character is not whitespace
    # (abc)def -> (abc)-def
    text = re.sub(r"\)([a-zA-Z])", r")-\1", text)
    # remove double hyphens
    text = re.sub(r"-+", "-", text)
    # Remove hypens inside closing bracket
    text = text.replace("-)", ")")
    # Remove hyphens in double compounds
    # e.g. (|(SU.LU.EŠ₂)&(SU.LU.EŠ₂)|) now looks like (|(SU.LU.EŠ₂)-&(SU.LU.EŠ₂)-|)
    text = text.replace("-&", "&")
    text = text.replace("-|)", "|)")
    return text


def _final_cleanup(text):
    # handle numbers where the number is "n"
    text = re.sub(r"(-)*( )*n(-)?( )?\(.*\)", f" {SpecialToken.NUM.value} ", text)

    # Remove empty brackets
    text = text.replace("{}", "")
    # Replace multiple hyphens with a single hypen
    text = re.sub(r"-+", "-", text)
    # Replace multiple spaces with a single space
    text = re.sub(r" +", " ", text)
    # Remove leading/trailing hyphens
    text = text.replace("- ", " ")
    text = text.replace(" -", " ")
    return text


# =============================================================================
# =============================================================================

if __name__ == "__main__":
    print("Loading data...")
    df = pd.read_csv(INFILE).fillna("")

    print("Cleaning transliterations...")
    functions_to_apply = [
        _handle_angle_brackets,
        _drop_linguistic_glosses,
        _add_hyphens_around_determinatives,
        _handle_partial_breakage,
        _handle_complete_breakage,
        _handle_semicolons,
        _update_special_tokens,
        _handle_vertical_bars,
        _handle_parentheses,
        _final_cleanup,
    ]
    df["transliteration_clean"] = df["transliteration"]
    for func in functions_to_apply:
        df["transliteration_clean"] = df["transliteration_clean"].apply(func)

    print(f"Writing to {OUTFILE}...")
    df.to_csv(OUTFILE, index=False)
    print("Done!")
