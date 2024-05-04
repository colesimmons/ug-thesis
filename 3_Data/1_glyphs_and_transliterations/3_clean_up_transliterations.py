"""
This script cleans the transliterations in a new "transliteration_clean" column
(for easy comparison) and saves the result to a new csv file
"""

import re

import pandas as pd

INFILE = "2_tablets.csv"
OUTFILE = "3_cleaned_transliterations.csv"


MISSING = (
    "==MISSING=="  # becomes "..." in the final output but that's annoying in regexes
)


SPECIAL_TOKENS_AFTER = {
    "==SURFACE==",
    "==COLUMN==",
    "==BLANK_SPACE==",
    "==RULING==",
    "...",
}


# =============================================================================
# ========================= initial cleanup ===================================
# =============================================================================
def _double_angle_brackets(text: str) -> str:
    """
    'The graphemes are present but must be excised for the sense.'
    From: https://oracc.museum.upenn.edu/doc/help/editinginatf/primer/inlinetutorial/index.html

    Get rid of the brackets but keep the text (i.e. treat it like normal text)
    """
    text = text.replace("<<", "")
    text = text.replace(">>", "")
    return text


def _upper_brackets(text: str) -> str:
    """
    ⸢abc⸣ is partially broken. Treat it as normal text.
    """
    text = text.replace("⸢", "")
    text = text.replace("⸣", "")
    return text


def _double_curly_braces(text: str) -> str:
    """
    'Linguistic glosses are defined for the purposes of this specification
     as glosses which give an alternative to the word(s) in question.
     Such alternatives are typically either variants or translations.'
    From: https://oracc.museum.upenn.edu/doc/help/editinginatf/primer/inlinetutorial/index.html

    Get rid of 'em.
    """
    text = re.sub(r"\{\{[^\n]*?\}\}", "", text)
    text = text.replace("{{", "")
    text = text.replace("}}", "")
    return text


# ============================================================================
# ========================= check ============================================
# ============================================================================
def _check_for_unmatched_brackets(row):
    """A shortcoming of the EPSD data is that when I pull the transliterations,
    brackets that occur in tandem with an "n", a parenthesis, or a vertical bar
    are ommited.
    """
    text = row["transliteration_clean"]
    lines = text.split("\n")

    fixed = []
    problematic_lines = []
    for line in lines:
        bracket_seq = "".join([c for c in line if c in "[]"])
        while True:
            bracket_seq = bracket_seq.replace("[]", "")
            if "[]" not in bracket_seq:
                break
        if bracket_seq:
            fixed.append(MISSING)  # just drop the whole line
            problematic_lines.append(line)
        else:
            fixed.append(line)

    if problematic_lines:
        print("Unmatched brackets in: ", row["id"])
        for line in problematic_lines:
            print(">> ", line)
        print()
        row["transliteration_clean"] = "\n".join(fixed)

    return row


# ============================================================================
# =========================== <> and [] ======================================
# ============================================================================
def _fix_enclosure_order(text):
    # Case 1: ([...)...] -> [(...)...]
    matches = re.findall(
        r"(\(\["  # ([
        + r"[^\n)\]]*?"  # any character except: \n ) ]
        + r"\)"  # )
        + r"[^\n\]]*?"  # any character except: \n ]
        + r"\])",  # ]
        text,
    )
    for match in matches:
        after = match.replace("([", "[(")
        print(f">> {match} -> {after}")
        text = text.replace(match, after)

    # Case 2: [...(...]) -> [...(...)]
    matches = re.findall(
        r"(\["  # [
        + r"[^\n(\]]*?"  # any character except: \n ( ]
        + r"\("  # (
        + r"[^\n)\]]*?"  # any character except: \n ) ]
        + r"\]\))",  # ]
        text,
    )
    for match in matches:
        after = match.replace("])", ")]")
        print(f">> {match} -> {after}")
        text = text.replace(match, after)

    # Case 3: {[...}...] -> [{...}...]
    matches = re.findall(
        r"(\{\["  # {[
        + r"[^\n}\]]*?"  # any character except: \n } ]
        + r"\}"  # }
        + r"[^\n\]]*?"  # any character except: \n ]
        + r"\])",  # closing bracket
        text,
    )
    for match in matches:
        after = match.replace("{[", "[{")
        print(f">> {match} -> {after}")
        text = text.replace(match, after)

    # Case 4: [...{...]} -> [...{...}]
    matches = re.findall(
        r"(\["  # [
        + r"[^\n{\]]*?"  # any character except: \n { ]
        + r"\{"  # {
        + r"[^\n\]]*?"  # any character except: \n ]
        + r"\]\})",  # }]
        text,
    )
    for match in matches:
        after = match.replace("]}", "}]")
        print(f">> {match} -> {after}")
        text = text.replace(match, after)

    # Case 5: <...{...>} -> <...{...}>
    matches = re.findall(
        r"(\<"  # <
        + r"[^\n{\>]*?"  # any character except: \n { >
        + r"\{"  # {
        + r"[^\n}\>]*?"  # any character except: \n } >
        + r"\>\})",  # >}
        text,
    )
    for match in matches:
        after = match.replace(">}", "}>")
        print(f">> {match} -> {after}")
        text = text.replace(match, after)

    # Case 6: {<...}...> -> <{...}...>
    matches = re.findall(
        r"(\{\<" + r"[^\n\}\>]*?" + r"\})",
        text,
    )
    for match in matches:
        after = match.replace("{<", "<{")
        print(f">> {match} -> {after}")
        text = text.replace(match, after)

    return text


def _single_angle_brackets(text):
    """
    'The graphemes must be supplied for the sense but are not present.'
    From: https://oracc.museum.upenn.edu/doc/help/editinginatf/primer/inlinetutorial/index.html

    Get rid of 'em.
    """
    text = re.sub(r"<[^\n]*?>", "", text)
    # rest are unmatched, so we'll just get rid of the start/end of these lines
    text = re.sub(r"(<[^\n>]*?(\n|$))", f"{MISSING}\n", text)
    text = re.sub(r"(\n[^\n<]*?>)", f"\n{MISSING}", text)
    return text


def _single_square_brackets(text):
    """
    [abc def] is conjecture on what has been broken away.
    Convert to SpecialToken.MISSING
    """
    # [abc def] -> <MISSING> or [abc ... \n -> <MISSING>
    return re.sub(r"\[(?:[^\[\]\n]|\[[^\[\]\n]*\])*\]", MISSING, text)


def _x_and_o(text):
    """
    Both "x" and "o" are used to indicate missing text.
    Convert sequences to SpecialToken.MISSING.
    """
    return re.sub(r"([\ -]*[oxX]+[\ -]*)+", MISSING, text)


def _dollar_signs(text):
    """
    $erasure$ or $ traces $ -> SpecialToken.MISSING

    The other instances precede a sign name to indicate that the reading is uncertain.
    Since we will take the presence of a sign name to mean that the reading is uncertain,
    we can remove the $ signs and treat the text as normal.
    e.g. $AN -> AN
    """

    text = text.replace("($erasure$)", MISSING)
    text = text.replace("$erasure$", MISSING)
    text = text.replace("$ traces $", MISSING)
    text = text.replace("$", "")
    return text


def _ellipsis(text):
    """... -> SpecialToken.MISSING"""
    return text.replace("...", MISSING)


def _missing_alone_in_enclosure(text):
    # Alone in parens
    text = re.sub(
        r"(\(" + r"[\ \-]*" + MISSING + r"[\ \-]*" + r"\))",
        MISSING,
        text,
    )

    # Alone in brackets
    text = re.sub(
        r"(\{" + r"[\ \-]*" + MISSING + r"[\ \-]*" + r"\})",
        MISSING,
        text,
    )

    # Alone in vertical bars
    text = re.sub(
        r"(\|" + r"[\ \-]*" + MISSING + r"[\ \-]*" + r"\|)",
        MISSING,
        text,
    )
    return text


def _missing_inside_curly_braces(text):
    return text.replace(f"{MISSING}}}", f"}}{MISSING}")


def _standalone_parens(text):
    matches = re.finditer(r"((^|\n|\ )\([^\n\)]+\)($|\n|\ ))", text)
    for match in matches:
        text = text.replace(match.group(1), MISSING)
    return text


# =============================================================================
# ============================= check =========================================
# =============================================================================
def _check_for_disallowed_characters(row):
    """
    Check for characters that should not be present at this point.
    """
    text = row["transliteration_clean"]
    lines = text.split("\n")
    fixed = []

    chars = ["<", ">", "[", "]", "$", "..."]

    problematic_lines = []
    for line in lines:
        if any(char in line for char in chars):
            problematic_lines.append(line)
            fixed.append(MISSING)
        else:
            fixed.append(line)

    if problematic_lines:
        print("Disallowed character(s) in: ", row["id"])
        for line in problematic_lines:
            print(">> ", line)
        print()
        row["transliteration_clean"] = "\n".join(fixed)

    return row


# =============================================================================
# ========================= back to cleanup ===================================
# =============================================================================
def _remove_multiple_spaces(text):
    return re.sub(r"\ +", " ", text)


def _semicolons(text):
    """Semicolons are used to separate lines in the transliteration."""
    return text.replace(";", " \n ")


def _remove_space_around_newline(text):
    return re.sub(r"\ *\n\ *", "\n", text)


def _sequence_of_several_missing(text):
    text = text.replace(f"{MISSING}-", MISSING)
    text = text.replace(f"-{MISSING}", MISSING)
    text = re.sub(r"(" + MISSING + r"(\ \-)*)+", MISSING, text)
    text = re.sub(r"((\ \-)*" + MISSING + r")+", MISSING, text)
    text = re.sub(r"(" + MISSING + r")+", MISSING, text)
    text = re.sub(r"(\n" + MISSING + r")+", f"\n{MISSING}", text)
    return text


def _remove_parentheses_with_missing_inside(text):
    matches = re.findall(r"(\([^\n)]*" + MISSING + r"[^\n)]*\))", text)
    for match in matches:
        print(">> ", match)
        text = text.replace(match, "")
    return text


def _remove_bars_with_missing_inside(text):
    # Remove missing inside parentheses
    matches = re.findall(r"(\|[^\n|\ ]*" + MISSING + r"[^\n|\ ]*\|)", text)
    for match in matches:
        print(">> ", match)
        text = text.replace(match, "")
    return text


def _single_curly_braces(text):
    """
    'Determinatives include semantic and phonetic modifiers,
     which may be single graphemes or several hyphenated graphemes,
     which are part of the current word.

     Determinatives are enclosed in single brackets {...};
     semantic determinatives require no special marking,
     but phonetic glosses and determinatives should be indicated by adding
     a plus sign (+) immediately after the opening brace, e.g., AN{+e}.

     Multiple separate determinatives must be enclosed in their own brackets,
     but a single determinative may consist of more than one sign
     (as is the case with Early Dynastic pronunciation glosses).'
    From: https://oracc.museum.upenn.edu/doc/help/editinginatf/primer/inlinetutorial/index.html
    """
    text = text.replace("{-", "{")
    text = text.replace("-}", "}")
    return text


def _vertical_bars(text):
    # Add hyphen after vertical bars
    text = re.sub(r"\|(.*?)\|", r"|\1|-", text)

    # If the last character before the closing bar is a hyphen, remove it
    text = re.sub(r"\|(.+)-\|", r"|\1|", text)
    return text


def _parentheses(text):
    # Insert a hyphen after each closing parenthesis if the next character is not whitespace
    # (abc)def -> (abc)-def
    text = re.sub(r"\)([a-zA-Z])", r")-\1", text)
    # Remove hyphens inside opening bracket
    text = text.replace("(-", "(")
    # Remove hypens inside closing bracket
    text = text.replace("-)", ")")
    # Remove hyphens in double compounds
    # e.g. (|(SU.LU.EŠ₂)&(SU.LU.EŠ₂)|) now looks like (|(SU.LU.EŠ₂)-&(SU.LU.EŠ₂)-|)
    text = text.replace("-&", "&")
    text = text.replace("-|)", "|)")
    return text


def _missing_to_ellipses(text):
    text = re.sub(r"\ +", " ", text)
    text = text.replace(f"{MISSING} ", MISSING)
    text = text.replace(f" {MISSING}", MISSING)
    return text.replace(MISSING, "...")


def _final_cleanup(text):
    # Remove leading/trailing hyphens
    text = text.replace("- ", " ")
    text = text.replace(" -", " ")
    text = text.replace("-\n", "\n")
    text = text.replace("\n-", "\n")
    # Remove empty brackets
    text = text.replace("{}", "")
    # Replace multiple hyphens with a single hypen
    text = re.sub(r"-+", "-", text)
    # Replace multiple spaces with a single space
    text = re.sub(r"\ +", " ", text)
    return text


# =============================================================================
# =============================================================================
if __name__ == "__main__":
    print("Loading data...")
    df = pd.read_csv(INFILE).fillna("")

    df["transliteration_clean"] = df["transliteration"]

    print("Performing initial cleanup...")
    fns = [
        (_double_angle_brackets, "Treating <<...>> as normal text"),
        (_upper_brackets, "Treating ⸢...⸣ as normal text"),
        (_double_curly_braces, "Getting rid of {{...}} (linguistic glosses)"),
    ]
    for func, desc in fns:
        print("\n➡️ " + desc)
        df["transliteration_clean"] = df["transliteration_clean"].apply(func)

    print()
    print("\nChecking for unmatched brackets...")
    df.apply(_check_for_unmatched_brackets, axis=1)

    fns = [
        (_fix_enclosure_order, "Fixing enclosure order..."),
        (_single_angle_brackets, "Getting rid of <...>"),
        (_single_square_brackets, "Getting rid of [...]"),
        (_x_and_o, "Getting rid of x and o"),
        (_dollar_signs, "Getting rid of $...$"),
        (_ellipsis, "Getting rid of '...'"),
        (_missing_alone_in_enclosure, "Getting rid of, e.g. (==MISSING==)"),
        (_missing_inside_curly_braces, "==MISSING==} -> }==MISSING=="),
        (_standalone_parens, "Getting rid of (...)"),
    ]
    for func, desc in fns:
        print("\n➡️ " + desc)
        df["transliteration_clean"] = df["transliteration_clean"].apply(func)

    print()
    print("\nChecking for disallowed character(s)...")
    df.apply(_check_for_disallowed_characters, axis=1)

    fns = [
        (_remove_multiple_spaces, "Reducing multiple spaces to one..."),
        (_semicolons, "Converting semicolons to newlines..."),
        (
            _remove_parentheses_with_missing_inside,
            "Removing parentheses w/ ==MISSING== inside...",
        ),
        (
            _remove_bars_with_missing_inside,
            "Removing vertical bars w/ ==MISSING== inside...",
        ),
        (_remove_space_around_newline, "Removing spaces around newlines..."),
        (_sequence_of_several_missing, "==MISSING====MISSING== -> ==MISSING=="),
        (_single_curly_braces, "Handling single curly braces..."),
        (_vertical_bars, "Handling vertical bars..."),
        (_parentheses, "Handling parentheses..."),
        (_missing_to_ellipses, "Converting ==MISSING== to '...'"),
        (_final_cleanup, "Final cleanup..."),
    ]
    for func, desc in fns:
        print("\n➡️ " + desc)
        df["transliteration_clean"] = df["transliteration_clean"].apply(func)

    # Filter out tablets where transliteration without special tokens is empty
    print(
        "Filtering out tablets with empty transliterations (beside special tokens)..."
    )
    print(f"Initial number of tablets: {len(df)}")
    df = df[
        df["transliteration_clean"].apply(
            lambda x: re.sub(r"(==.*?==|\.\.\.|\n)", "", x)
        )
        != ""
    ]
    print(f"Updated number of tablets: {len(df)}")

    print(f"Writing to {OUTFILE}...")
    df.to_csv(OUTFILE, index=False)
    print("Done!")
