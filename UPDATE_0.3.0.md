# Version 0.3.0

- Learned checkboxes in dictionary rows, entry details and revealed flashcards. Saved per language, linked across script forms; can be unmarked. Learned/Still learning dictionary filters and a separate learned-character Progress count.
- Flashcard I knew it / Still learning buttons set or clear the learned mark. Practice alone does not automatically imply mastery.
- Every flashcard/practice set has at least 15 cards. Related vocabulary supplements the original four situation sentences and other small groups; supplementary membership is separate from original question IDs and fingerprints.
- Replace English-to-character typing with Chinese-to-meaning recognition and context where available. One scored answer, correction/reading, then Next or Enter. No same-card retry. Existing recognition/core trophies remain preserved; new trophies require a perfect first-answer run.
- Matching consumes a card on either a correct or wrong answer, reveals the correct pair after mistakes, and counts only correct first answers in accuracy.
- Pick all categories ignores active filters and selects all applicable categories for the current language. Existing drill deduplication prevents repeated characters.
- Dictionary sort buttons toggle direction on repeated clicks. Frequency supports most/least common first, with unranked entries last.

## Storage compatibility

Keep `first1000.progress.v1` and schema 1. The optional per-language learned dictionary is added in memory when an older valid backup is loaded. Existing scores, settings, sessions and trophy records are preserved. Exported backups include learned marks. Original category memberships/fingerprints remain unchanged; expanded practice membership is stored separately.

## Content scope

Situation flashcard sets now mix four original sentences with eleven related words. Sentence-only practice still uses those four original sentences per situation; this update does not claim to add new sentence translations. Expanded vocabulary sets may include words from additional levels, as labelled in their category descriptions.

## Verification

Python compilation, 119 tests (including mounted Flet lifecycle, backup migration, learned status, expanded sets, sorting, one-pass scoring and responsive constraints), and the static build/runtime/source checks pass. Rendered browser UI was not tested for this release.
