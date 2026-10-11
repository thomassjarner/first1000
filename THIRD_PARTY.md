# Content and font attribution

This curriculum was assembled for a reconstruction of First 1000. Spellings were converted with OpenCC to simplified or Hong Kong traditional forms. The themed categories, selected senses, Mandarin/Cantonese word mappings, and new examples are editorial adaptations. No original interrupted-session dataset was available.

| Source | Use and credit | License |
|---|---|---|
| [HanziDB CSV](https://github.com/ruddfawcett/hanziDB.csv), commit `3e9f908d25f70674862343b201f6b641a36cd226` | Character order, glosses, and initial readings; ruddfawcett/HanziDB. Frequency ranking is derived from [Jun Da's Chinese character frequency work](https://lingua.mtsu.edu/chinese-computing/statistics/char/list.php?Which=MO). | MIT; included in `LICENSES/hanzi_db.LICENSE` |
| [clem109/hsk-vocabulary](https://github.com/clem109/hsk-vocabulary), commit `f3dc9d12ae00d04fa3676b0bd4c43cd58de2c264` | Intended HSK 2012 level 1–4 readings and English senses. 1,200 source records merge into 1,193 distinct spellings. | Repository MIT notice included; underlying CC-CEDICT definitions retain CC BY-SA 3.0 |
| [drkameleon/complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary), commit `7ac65bf1a6387d35f1ade478906172a19311c7f9` | Word frequency, POS hints, and cross-checking. Original syllabus readings take precedence over unrelated dictionary forms. | Repository MIT notice included; underlying dictionary licenses still apply |
| [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) | English dictionary senses included through the HSK sources. Credit the CC-CEDICT contributors. | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| [Pleco CC-Canto](https://www.cc-canto.org/) | Cantonese word and character readings, dictionary-supported HK vocabulary mappings. © 2015–2017 Pleco Inc. Distribution files `cccanto-170202.zip` and `cccedict-canto-readings-150923.zip`. | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| [Unicode Unihan 18.0.0](https://www.unicode.org/Public/18.0.0/ucd/Unihan.zip) | Character definitions and Mandarin/Cantonese reading cross-checks. © Unicode, Inc. | Unicode License v3, included in `LICENSES/unicode.LICENSE` |
| [Tatoeba](https://tatoeba.org/), via [ManyThings Mandarin/English](https://www.manythings.org/anki/cmn-eng.zip) and [Cantonese/English](https://www.manythings.org/anki/yue-eng.zip) | Paired examples. **Every selected row retains both sentence IDs, contributor names, and the source attribution** in the curriculum and the app's Example attribution dialog. | [CC BY 2.0 France](https://creativecommons.org/licenses/by/2.0/fr/). Script conversion is an adaptation. |
| First 1000 contributors | Selected learning senses, topic grouping, 38 HK phrase entries and original examples, transparent reference examples, and vocabulary-equivalence curation. | CC BY-SA 3.0 for new curriculum material |
| [Noto Sans CJK HK](https://github.com/notofonts/noto-cjk) | © 2014–2021 Adobe. The full Hong Kong regular font was subset to the actual curriculum and renamed **First 1000 Hanzi**. Hong Kong glyph forms are preserved. | SIL Open Font License 1.1, included beside the font |
| [Inter](https://github.com/rsms/inter), via Google Fonts | UI font; the bundled OFL notice credits the original authors. | SIL Open Font License 1.1, included beside the font |

The general dictionary includes the 1,000 separately labelled character records and 1,231 vocabulary/phrase records. This keeps core character-set membership stable even when Cantonese uses a different everyday word for the same meaning.

The compiled vocabulary portions of `curriculum.json` are distributed under CC BY-SA 3.0. Tatoeba example records retain CC BY 2.0 FR; Unicode fields retain the Unicode notice. Application source code is separately MIT-licensed. Redistribution must keep these attributions, notices, and applicable share-alike terms for adapted dictionary content.

Input SHA-256 checksums and source repository commits appear in `src/first1000/data/provenance.json`. The curated asset inputs are included in `tools/curated/`. The builder documents the required input filenames; it does not fetch data during app startup.

## Version 0.2.0 additions

The 48 paired situation sentences are original authored learning examples under CC BY-SA 3.0. Cantonese character selection reuses the existing attributed character readings and definitions. Its provisional order uses manually prioritized spoken essentials and occurrence counts in the bundled Cantonese examples and vocabulary; it is not an independent representative frequency corpus.

The expanded Hanzi subset was made from NotoSansCJKhk-Regular.otf from the official notofonts/noto-cjk repository (Sans/OTF/TraditionalChineseHK), under the existing SIL OFL license bundled with the app. It preserves existing glyph coverage and adds the new sentence and character glyphs.
