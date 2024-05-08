Scripts to acquire and preprocess data which will be used in the following sections.

They should be run from within this folder. After following the instructions in the main README to install and set up Poetry,
you can run, for e.g.: `poetry run python 1_download_corpora.py`.

**Reproducibility**:
The first script (`1_download_corpora.py`) downloads the ePSD2 data.
However, as this data is liable to be modified or made unavailable in the future, you can download a copy of the data used in my experiments [here](https://drive.google.com/file/d/1gCubNGMb9_R0QcCyl4JwVAd5b-YKjL2Z/view?usp=drive_link).
Unpacking it in this directory should create a directory `./3_Data/.corpusdata`. The first script will detect the data's presence and use it rather than re-downloading.

Similarly, `4_create_lookups.py` relies on Oracc Sign List data `osl.json`, a copy of which can be downloaded [here](https://drive.google.com/file/d/1qArSHeGsCHc3Fq6gdZiBLIvvObB5cIrU/view?usp=drive_link)

---
`1_download_corpora.py`
* Downloads (or loads from `.corpusjson/`) the ePSD2 JSON files for each corpus
* For each corpus:
    * Loads the tablets' metadata from `catalogue.json`
    * Pulls the transliteration from each tablet's JSON file
    * Creates a DataFrame where each row is a tablet (variable set of columns depending on the data available for a corpus)
    * Saves the DataFrame to a CSV in `3_Data/1_corpora/{corpus}.csv`
 
This section makes use of my [Sumeripy](https://github.com/colesimmons/sumeripy) library, which uses Pydantic models to parse and validate the JSON.

---
`2_collate_tablets.py`
* Loads each corpus CSV file from `3_data/1_corpora/{corpus}.csv`
* Concats them into a single DataFrame (inner join, so only common columns)
  * 94,178 rows
* Drops tablets that are definitely not Sumerian
  * New # of rows: 93,615
* Drops rows without transliterations
  * New # of rows: 92,908
* Drops duplicate IDs (tablets that were included in multiple corpora)
  * New # of rows: 92,864
* Drops all columns except `id | transliteration | period | genre | subgenre`
* Saves result to `2_tablets.csv`

---
`3_clean_up_transliterations.py`
* Loads `2_tablets.csv`
* Cleans/standardizes transliterations
   * Removes, to the greatest extent possible, editorialization. For example, when a section is broken away, a transliteration may include a suggestion for what was probably in that space by placing it in brackets, e.g. "[lugal\] kur-kur-ra".
* Drops tablets with identical transliterations
   * New total: 92,831
* Saves to `3_cleaned_transliterations.csv` with new column `transliteration_clean`

---
`4_create_lookups.py`
* Uses the Oracc Sign List and the ePSD2 sign lists to create lookups that will help us turn transliterations into parallel glyph sets
* Creates file `morpheme_to_glyph_names.json` (str -> list[str])
  * Maps from an individual reading to all of the potential glyph names that could have represented it
* Creates file `glyph_name_to_glyph.json` (str -> str)
  * Maps from a glyph name to the corresponding Unicode

---
`5_add_glyphs.py`
* Loads `3_cleaned_transliterations.csv` and the lookup files from the previous step
* Creates parallel transliteration--glyph names--Unicode glyphs examples for each tablet
   * Number of morphemes unable to convert into glyph name: 4965 (0.07%)
   * Successfully converted: 6725306 (99.93%)
   * Number of glyph names unable to convert into Unicode: 5561 (0.08%)
   * Successfully converted: 6719745 (99.92%)
* Drops rows with identical transliterations:
   * New total: 91676
* Drops rows with identical glyphs:
   * New total: 91527
* Saves to `5_with_glyphs.csv` (columns=id|transliteration|glyph_names|glyphs|period|genre)

---
`6_split.py`
