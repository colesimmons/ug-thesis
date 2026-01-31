import json
import re

from datasets import load_dataset
from openai import OpenAI
from tqdm import tqdm
from transformers import AutoTokenizer

client = OpenAI(api_key="")

SYSTEM = """
You are a highly skilled translator specializing in Sumerian.

Your task is to accurately translate Sumerian transliterations into English while maintaining the original meaning and context.

Please follow these steps:
1) Analyze the Sumerian text provided by the user, considering the context and any specific terminology. Break down the text into smaller segments, such as sentences or phrases, to ensure accurate translation.
2) For each segment, provide a definitive English translation that captures the intended meaning. Do not include any Sumerian transliteration in the final translation.
3) Once you have translated all the segments, combine them into a coherent English translation that maintains the structure and flow of the original Sumerian text.
Do not include any additional information or commentary in your translation.

When translating Sumerian to English, keep in mind the following grammatical information:
1) Sumerian is an agglutinative language, meaning that words are formed by combining smaller morphemes or grammatical elements.
2) The word order in Sumerian is Subject-Object-Verb (SOV).
3) Sumerian uses a system of grammatical cases to indicate the function of a noun in a sentence. The main cases include the ergative (subject of a transitive verb), absolutive (object of a transitive verb or subject of an intransitive verb), genitive (indicating possession), and dative (indicating the recipient or beneficiary of an action).
4) Verbs in Sumerian have a complex system of affixes that indicate tense, aspect, mood, and agreement with the subject and object.
5) Pronouns in Sumerian are generally not used, as the verb affixes can indicate the person and number of the subject and object.
6) Sumerian does not have articles (e.g., "a," "an," "the") or conjunctions (e.g., "and," "but," "or").
"""

PROMPT = """
INPUT:
ud re-a-ta ud an ki-bi-ta...
ŋi₆ re-a-ta ŋi₆ an ki-bi-ta...
...mu nam...
...ba-tu-ud-da-a-ba
{d}ama{d}inana nam <unk> še₃ ba-tuku-a-ba
{d}ama{d}inana an ki-a ba-hal-hal-la-a-ba
{d}ama{d}inana...ba-a-peš u₃-tud-da-a-ba
diŋir kurum₆-ma-bi <unk>...unu₂-bi-še₃ ba-ab-keše₂-a-ba
diŋir šar₂-šar₂ kiŋ₂-ŋa₂ al-sug₂-ge-eš diŋir tur-tur du₂-lum im-il₂-il₂-e-ne
diŋir id₂ im dun-dun-u₃-ne sahar-bi ha-ra-li im-dub-dub-be₂-ne
diŋir im ar₃-ar₃-re-ne zi-bi inim am₃-ma-ŋar-re-ne
ud-ba ŋeštug₂ daŋal mud diŋir šar₂-šar₂ ŋal₂-ŋal₂
{d}en-ki-ke₄ engur burudₓ(U) a-sur-ra ki diŋir na-me šag₄-bi u₆ nu-um-me
ki-nu₂-ni i₃-nu₂ u₃ ku nu-um-zi-zi
diŋir er₂-ra im-pad-pad-ne a-nir ŋal₂ i₃-ak im-me-ne
lu₂ ku-ra i₃-nu₂-a-ra ki-nu₂-bi nu-um-zi-zi-ra
{d}namma-ke₄ ama palil u₃-tud diŋir šar₂-šar₂-ra-ke₄-ne
er₂-ra diŋir-re-e-ne dumu-ni-ir ba-ši-in-de₆
...mu-un-ši-nu₂-u₃-nam u₃ mu-un-ši-ku-ku-na-nam
...<unk> <unk>...
dim₃-me₂-er šu dim₂-dim₂-ma-zu...gu₂-bi im-tu₁₀-tu₁₀-ne
du₅-mu-ŋu₁₀ ki-nu₂-zu zig₃-ga...ma-al-la-zu-ta na-aŋ₂-kug-zu u₃-mu-e-kiŋ₂-ŋa₂
kiŋ₂-sig₁₀ dim₃-me₂-er-e-ne-ke₄...du₂-lum-bi ha-ba-tu-lu-ne
{d}en-ki-ke₄ inim ama-na {d}namma-ke₄ ki-nu₂-na ba-ta-zig₃
hal-an-kug niŋin₂ šag₄ kuš₂-u₃-da-na haš...

OUTPUT:
In those days, in the days when heaven and earth were created; in those nights, in the nights when heaven and earth were created; in those years, in the years when the fates were determined; when the Anuna gods were born; when the goddesses were taken in marriage; when the goddesses were distributed in heaven and earth; when the goddesses...became pregnant and gave birth; when the gods were obliged...their food...for their meals; the senior gods oversaw the work, while the minor gods were bearing the toil. The gods were digging the canals and piling up the silt in Harali. The gods, dredging the clay, began complaining about this life.

At that time, the one of great wisdom, the creator of all the senior gods, Enki lay on his bed, not waking up from his sleep, in the deep engur, in the flowing water, the place the inside of which no other god knows. The gods said, weeping: "He is the cause of the lamenting!" Namma, the primeval mother who gave birth to the senior gods, took the tears of the gods to the one who lay sleeping, to the one who did not wake up from his bed, to her son: "Are you really lying there asleep, and...not awake? The gods, your creatures, are smashing their...My son, wake up from your bed! Please apply the skill deriving from your wisdom and create a substitute for the gods so that they can be freed from their toil!"

At the word of his mother Namma, Enki rose up from his bed.

INPUT:
2(diš) udu
1(diš) sila₄
ba-uš₂
u₄ 1(u)-kam
ki be-li₂-i₃-li₂-ta
{d}šul-gi-iri-mu
šu ba-ti
iti <unk> bi₂-gu₇
mu us₂-sa si-ma-num₂{ki} ba-hul
3(diš)

OUTPUT:
2 sheep, 1 lamb. Slaughtered on the 10th day.
Šulgi-irimu received from Bēlī-ilī.
Month: “Ubi feast"
Year: “Simanum was destroyed.”
Total: 3.

---

INPUT:
1(u) 5(diš) guruš
a₂ u₄ 1(diš)-bi gu-nigin₂ 4(u) 5(diš)-am₃
šuniŋin 1(gešʾu) 2(geš₂) 4(u) 5(diš) gu-nigin₂-am₃
a₂ u₄ 1(u) 7(diš)-bi-im

OUTPUT:
15 male laborers,
Labor of 1 day: 45 bales.
Total: 765 bales, 17 days of labor.

---

INPUT:
2(u) 3(diš) ab₂
4(diš) gu₄
2(gešʾu) 3(u) 2(diš) u₈
1(geš₂) 4(u) 5(diš) udu
4(diš) sila₄ ga
...e₂-udu-niga
...
sa₂-du₁₁...
iti ki-siki{d}nin-a-zu
mu ki-maš{ki} u₃ hu-ur₅-ti{ki} ba-hul
2(u) 7(diš) gu₄ 2(gešʾu)...

OUTPUT:
23 cows
4 oxen
1232 ewes 105 rams, 4 suckling lambs...house of grain-fed sheep; regular rations
Month: “kisiki of Ninazu”
Year: “Kimaš and Hurti were destroyed.”
Total: 27 oxen, 1341 sheep.

---

INPUT:
{d}šu{d}suen
nita kal-ga
lugal uri₅{ki}ma
lugal an ub-da limmu₂-ba
lu₂{d}na-ru₂...
dub-sar
dumu he-sa₆
arad₂-zu

OUTPUT:
Šū-Suen, strong man, king of Ur, king of heaven, king of the Four Corners.
Lu-Nurua, scribe, son of Ḫesa, is your servant.

---

INPUT:
8(diš) udu niga
u₄ 2(u) la₂ 1(diš)-kam
ki ab-ba-sa₆-ga-ta
na-lu₅
i₃-dab₅
iti maš-da₃-gu₇
mu ur-bi₂-lum{ki} ba-hul
8(diš)

OUTPUT:
8 fattened sheep.
On the 19th day.
From Abbasaga.
Accepted by Nalu.
Month: “Gazelle feast,”
Year: “Urbilum was destroyed;”
Total: 8.

---

"""

SPECIAL_TOKS_TO_REMOVE = {
    "<SURFACE>",
    "<COLUMN>",
    "<RULING>",
    "<BLANK_SPACE>",
}


dataset = load_dataset("colesimmons/SumTablets")
tokenizer = AutoTokenizer.from_pretrained(
    "ColeSimmons/SumerianTransliterationTokenizer_Roberta"
)
MAX_LEN = 256


def translate_text(example) -> int:
    text = example["transliteration"]
    id = example["id"]

    # See if file already exists
    try:
        with open(f"./generated/{id}.json", "r") as f:
            print(f"Skipping {id} (already translated)")
            return 0
    except FileNotFoundError:
        pass

    for token in SPECIAL_TOKS_TO_REMOVE:
        text = text.replace(token, "")
    text = text.replace("<unk>", "...")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\ *\.\.\.\ *", "...", text)
    text = text.strip()

    tokenized = tokenizer(text, padding=False, truncation=False)
    if len(tokenized["input_ids"]) > MAX_LEN:
        print(f"Skipping {id} (too long)")
        translation = ""
        usage = 0
    else:
        prompt = PROMPT + f"INPUT:\n{text}\n\nOUTPUT:\n"
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.5,
            frequency_penalty=0.2,
        )
        translation = response.choices[0].message.content
        usage = response.usage.total_tokens

    # Write to JSON file in ./generated/{id}.json
    with open(f"./generated/{id}.json", "w", encoding="utf-8") as f:
        out = {
            "id": id,
            "transliteration": text,
            "translation": translation,
            "genre": example["genre"],
            "period": example["period"],
        }
        json.dump(out, f, ensure_ascii=False, indent=4)

    return usage


# Augment the dataset with translated text
def augment_dataset():
    num_tokens = 0
    dataset["train"] = dataset["train"].shuffle(seed=2)
    for example in tqdm(dataset["train"]):
        num_tokens += translate_text(example)
        print("Usage: ", num_tokens)


augment_dataset()
