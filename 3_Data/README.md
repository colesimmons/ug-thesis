Scripts to acquire and preprocess the data that will be used in the following sections.

They should be run from within this folder. After following the instructions in the main README to install and set up Poetry,
you can run, for e.g.: `poetry run python 1_download_corpora.py`.

**Reproducibility**: The first script (`1_download_corpora.py`) downloads the ePSD2 data.
However, as this data is liable to be modified or made unavailable in the future, you can download a copy of the data used in my experiments [here](https://drive.google.com/file/d/1gCubNGMb9_R0QcCyl4JwVAd5b-YKjL2Z/view?usp=drive_link).
Unpacking it in this directory should create a directory `./3_Data/.corpusdata`. The first script will detect the data's presence and use it rather than re-downloading.

`1_download_corpora.py`
---
* Downloads (or loads from `.corpusjson/`) the ePSD2 JSON files for each corpus
* For each corpus:
    * Loads the tablets' metadata from `catalogue.json`
    * Pulls the transliteration from each tablet's JSON file
    * Creates a DataFrame where each row is a tablet (variable set of columns depending on the data available for a corpus)
    * Saves the DataFrame to a CSV in `3_Data/1_corpora/{corpus}.csv`
 
This section makes use of my [Sumeripy](https://github.com/colesimmons/sumeripy) library, which uses Pydantic models to parse and validate the JSON.

`2_collate_tablets.py`
---
* Loads each corpus CSV file from `3_data/1_corpora/{corpus}.csv`
* Concats them into a single DataFrame (inner join, so only common columns)
  * 94,178 rows
* Drops tablets that are definitely not Sumerian
* Drops duplicates
* Drops all columns except `id | transliteration | period | genre | subgenre`
* Saves result to `2_tablets.csv`

`3_clean_up_transliterations.py`
---
* Loads `2_tablets.csv`
* Cleans/standardizes tablets
* Saves to `3_cleaned_transliterations.csv`

`4_add_glyphs.py`
---
* Loads `3_cleaned_transliterations.csv`
* Saves to `4_with_glyphs.csv`

`5_split.py`
---
