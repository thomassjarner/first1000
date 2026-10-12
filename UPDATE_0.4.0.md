# Version 0.4.0

- Correct pronunciation and tone: green. Correct phonetic spelling but a different or missing tone: amber Almost correct. Incorrect pronunciation: red. Accepted alternative readings still count as fully correct. The rules apply to numbered/accented Pinyin and Jyutping.
- The drill browser filters All, Correct, Almost correct, Incorrect and Not attempted. It stores the latest outcome per displayed glyph and language. Simplified/traditional glyphs have their own pronunciation outcomes; explicit learned marks remain linked across script forms.
- A Whole 1,000-character track button selects the forty character sets for the current language. Displayed forms are deduplicated; filters apply to the selected track.
- Small neutral-grey Chinese example sentences appear under drill characters, in the drill browser, in single-character dictionary/flashcard cards, and in the post-quiz review. The shortest matching real bundled example is preferred. Where no paired corpus/authored example exists, a clearly labelled reference sentence is used.
- After every completed quiz, Which characters do you know? presents a paginated review with explicit learned checkboxes. Choices save immediately; Mark this page learned is an optional explicit bulk choice. A correct answer alone never marks a character learned. The completed quiz's language is retained for the review even if the header language changes.
- Progress now focuses on the learned-character bar. Remove practised-character and accuracy displays from Progress; remove accuracy from Home and saved new session history. Accuracy remains on the immediate completed-quiz result. New completion records save mode, size, category IDs and date, not scores. Historical scores/records are preserved but not displayed as accuracy. Legacy schema counters remain unchanged for compatibility.

## Storage and migration

Keep first1000.progress.v1 and schema 1. Add optional drill_outcomes per language. Existing binary character records seed Correct only when all prior attempts were correct, otherwise Incorrect; old records cannot identify tone-only errors. Reattempting a glyph replaces its inferred status with the new outcome. Old learned marks, settings, trophies, backups and historical session records remain intact. The validator accepts both historical scored sessions and new score-free completion records.

## Verification

Python compilation and 140 tests pass, covering Pinyin/Jyutping tone-only classification, latest-result filtering, legacy migration, score-free history, language-safe learned review, full 1,000-character completion and mounted Flet serialization/responsive constraints. Static build checks verify source/data/font files and Pyodide dependencies. Rendered browser UI was not tested for this release.
