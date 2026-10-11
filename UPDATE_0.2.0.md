# First 1000 0.2.0

- Categories are compact rows with situation/character/vocabulary shortcuts, topic filters, search by meaning, recommended/name/size/unfinished sorting, and previous/next set navigation.
- Twelve everyday situations contain 48 original paired Mandarin and spoken Cantonese sentences. Sentence meaning practice offers four choices and reveals pronunciation after answering; records scores and session history separately from trophy quizzes.
- Cantonese now has forty separate sets of 25 characters. Spoken essentials are placed first, followed by occurrence counts in the bundled Cantonese examples and vocabulary. This is a provisional learning order, not a representative general Cantonese frequency ranking. Mandarin's original sets are unchanged.
- Hong Kong labels in navigation are replaced by traditional characters and spoken expressions. Existing regional content remains available alongside the general situations.
- Dictionary entries are compact list rows with Details dialogs for examples and attribution.
- Enter checks or reveals a character reading; another Enter advances. Empty reveals count as incorrect attempts. Choice mode also supports Enter.
- Added font glyph coverage for all new content. Retained the 0.1.2 Pyodide packaging fix.

## Existing progress

Storage key `first1000.progress.v1` and schema 1 remain intact. Original category IDs, memberships, and fingerprints are unchanged. New content has new IDs. Existing trophies remain in Progress, even when the Cantonese character browser now shows its separate sets. Character goal counts follow the current language's track; all earlier character attempt records remain stored. The backup validator additionally accepts sentence session history.

## Content limits

Sentences are authored learning examples, not corpus quotations. Cantonese character ordering is specific to this curriculum and still needs future refinement using a representative spoken corpus. Shared HSK vocabulary remains available and is not presented as a Cantonese frequency ranking.
