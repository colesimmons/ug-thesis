"""
This script uses the Oracc Sign List (OSL) data to create three JSON files:

1) `wordforms_to_glyph_names.json` str -> list[str]
- This maps from wordforms to a set of the glyph names.
- To see why this is useful, consider "lil₂",
- which can be represented as either "KID" or "E₂".
- If we are dealing with "{d}en-lil₂", wordforms_to_glyph_names tells us that
  this wordform is composed of the glyphs ["AN", "EN", "KID"]
  (correct order is coincidence),
  which tells us that "lil₂" is written as "KID" in this context.

2) `morpheme_to_glyph_names.json` str -> list[str]
- maps from an individual morpheme to a set of glyph names that could represent it.
- e.g. "lil₂" -> ["AN", "E₂"]

3) `glyph_name_to_glyph.json` str -> str
- This maps from glyph names to their Unicode representations or an empty string.

This script does not rely on the previous scripts.
It will be essential for turning the readings into glyph names / Unicode.
"""

import json
import os
from collections import defaultdict

import requests


# --------------------------------------------------------------------------------------
# ---------------------------- Download OSL JSON ---------------------------------------
# --------------------------------------------------------------------------------------
def download_osl_json():
    # Saved a copy at
    # https://drive.google.com/file/d/1qArSHeGsCHc3Fq6gdZiBLIvvObB5cIrU/view?usp=drive_link
    url = "https://oracc.museum.upenn.edu/osl/downloads/sl.json"
    filename = "osl.json"

    if os.path.isfile(filename):
        print(f"File '{filename}' already exists in the current directory.")
    else:
        try:
            # Send a GET request to the URL
            response = requests.get(url)

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                # Save the JSON content to a file
                with open(filename, "w") as file:
                    file.write(response.text)
                print(f"File '{filename}' downloaded successfully.")
            else:
                print(
                    f"Failed to download the file. Status code: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while downloading the file: {str(e)}")


# --------------------------------------------------------------------------------------
# ----------------------------- Process OSL JSON ---------------------------------------
# --------------------------------------------------------------------------------------
def process_json():
    # ----------------------------------------
    # ----- Wordform -> set(Glyph Names) -----
    # ----------------------------------------
    # e.g. e₂-a-ni-ša -> {E₂, AN, NI, ŠA}
    wordform_to_glyph_names = defaultdict(set)

    def _add_wordforms(*, glyph_name: str, wordforms: list[str]) -> None:
        for form in wordforms:
            form_base = form["sl:lemma"]["base"]
            glyph_name = glyph_name.replace("&amp;", "&")
            wordform_to_glyph_names[form_base].add(glyph_name)

    # ----------------------------------
    # -- Morpheme -> set(Glyph Names) --
    # ----------------------------------
    # e.g.  šab₄ -> {MI}
    morpheme_to_glyph_names = defaultdict(set)

    def _add_reading(*, glyph_name: str, reading: str) -> None:
        glyph_name = glyph_name.replace("&amp;", "&")
        morpheme_to_glyph_names[reading].add(glyph_name)

    # ----------------------------------
    # ------ Glyph Name -> Unicode -----
    # ----------------------------------
    # e.g. MI -> {𒈪}
    glyph_name_to_glyphs = defaultdict(set)

    def _add_glyph(*, glyph_name: str, unicode: str) -> None:
        glyph_name = glyph_name.replace("&amp;", "&")
        glyph_name_to_glyphs[glyph_name].add(unicode)

    # ----------------------------------------
    # ---------- Process json ----------------
    # ----------------------------------------
    with open("osl.json") as f:
        data = json.load(f)

    for letter in data["sl:signlist"]["j:letters"]:
        for glyph in letter["sl:letter"]["j:signs"]:
            glyph_data = glyph["sl:sign"]
            glyph_name = glyph_data["n"]
            # Glyph Name -> Unicode
            glyph_unicode = glyph_data.get("sl:ucun", "")
            _add_glyph(glyph_name=glyph_name, unicode=glyph_unicode)
            # Glyph Wordforms -> Glyph Name
            glyph_wordforms = glyph_data.get("sl:lemmas", [])
            _add_wordforms(glyph_name=glyph_name, wordforms=glyph_wordforms)

            for aka in glyph_data.get("j:aka", []):
                aka_name = aka["sl:aka"]["n"]
                _add_glyph(glyph_name=aka_name, unicode=glyph_unicode)

            # Glyph Readings
            for glyph_reading_data in glyph_data.get("j:values", []):
                if "sl:v" not in glyph_reading_data:
                    continue
                # Morpheme -> Glyph Name
                glyph_reading_data = glyph_reading_data["sl:v"]
                _add_reading(glyph_name=glyph_name, reading=glyph_reading_data["n"])
                # Wordform -> Glyph Name
                reading_wordforms = glyph_reading_data.get("sl:lemmas", [])
                _add_wordforms(glyph_name=glyph_name, wordforms=reading_wordforms)

            # Glyph Forms (variants, not to be confused with wordforms)
            for form in glyph_data.get("j:forms", []):
                form_data = form["sl:form"]
                form_name = form_data["n"]
                # Form Name -> Unicode
                form_unicode = form_data.get("sl:ucun", "")
                _add_glyph(glyph_name=form_name, unicode=form_unicode)

                for aka in form_data.get("j:aka", []):
                    aka_name = aka["sl:aka"]["n"]
                    _add_glyph(glyph_name=aka_name, unicode=form_unicode)

                # Form Readings
                for form_reading_data in form_data.get("j:values", []):
                    if "sl:v" not in form_reading_data:
                        continue
                    # Morpheme -> Form Name
                    form_reading_data = form_reading_data["sl:v"]
                    _add_reading(glyph_name=form_name, reading=form_reading_data["n"])
                    # Wordform -> Form Name
                    reading_lemmas = form_reading_data.get("sl:lemmas", [])
                    _add_wordforms(glyph_name=form_name, wordforms=reading_lemmas)

    # ----------------------------------------
    # ---------- Postprocess -----------------
    # ----------------------------------------
    #
    # 1) Convert sets to lists and remove empty strings
    def _remove_empty_strings(d: dict) -> dict:
        return {key: [v for v in vals if v != ""] for key, vals in d.items()}

    wordform_to_glyph_names = _remove_empty_strings(wordform_to_glyph_names)
    morpheme_to_glyph_names = _remove_empty_strings(morpheme_to_glyph_names)
    glyph_name_to_glyphs = _remove_empty_strings(glyph_name_to_glyphs)

    # 2) For every morpheme that has multiple glyph names,
    #    add a new entry for each of the glyph names.
    #    e.g. if "lil₂": ["AN", "E₂"], we add "lil₂(AN)" and "lil₂(E₂)"
    with open("epsd2-sl.json", encoding="utf-8") as infile:
        to_add = json.load(infile)["index"]
        for k, v in to_add.items():
            morpheme_to_glyph_names[k] = [v]

    # 3) Each glyph name should map to at most one unicode representation.
    #    Double check, then convert the lists to strings.
    for glyph_name, unicodes in glyph_name_to_glyphs.items():
        if len(unicodes) > 1:
            print(glyph_name, unicodes)
    glyph_name_to_glyph = {
        key: vals[0] if vals else "" for key, vals in glyph_name_to_glyphs.items()
    }

    # ----------------------------------------
    # --------------- Save -------------------
    # ----------------------------------------
    with open("wordform_to_glyph_names.json", "w", encoding="utf-8") as f:
        json.dump(wordform_to_glyph_names, f, ensure_ascii=False)

    with open("morpheme_to_glyph_names.json", "w", encoding="utf-8") as f:
        json.dump(morpheme_to_glyph_names, f, ensure_ascii=False)

    with open("glyph_name_to_glyph.json", "w", encoding="utf-8") as f:
        json.dump(glyph_name_to_glyph, f, ensure_ascii=False)


if __name__ == "__main__":
    download_osl_json()
    process_json()
