> Historical verification notes for the original edition. See UPDATE_0.2.0.md for the current features and migration notes. Version 0.2.0 passes 94 tests; rendered browser UI has not been tested here.

# Recovery and completed work

The original requirements and visible progress messages were supplied in the current conversation. They established Python/Flet, Mandarin/Cantonese and HK traditional modes, the first-1,000-character goal, 40 core character sets, 93 themed sets, 1,231 words/phrases, fixed core quizzes with perfect-run trophies, mixed categories, a dictionary, flashcards, character drills, and progress tracking. They also mentioned a matching game and progress backup work.

The existing **First 1000** Sites project was located and reused. At recovery time it had no saved versions and its source repository had no default-branch commit. The old generated source code, exact curriculum/category membership, and any unfinished ZIP could not be recovered. Moving the old conversation into a Project did not make those unsaved files available here.

The user subsequently authorized generating a usable version. This project therefore **reconstructs the recovered design and requirements**. It does not claim to be recovered original code. It keeps the same application concept, Python/Flet architecture, counts, and quiz behavior, using newly assembled attributed data. There was no existing learning progress to import.

## Completed in this edition

- Python/Flet 1.0.3 application with home navigation and responsive layouts.
- Three header switches, dark palette, Pinyin/Jyutping separation, and HK traditional conversion.
- 1,000 ranked character cards in 40 fixed sets; 1,231 word/phrase entries in 93 fixed themed sets.
- General/category dictionaries, sorting/filtering, example-source dialogs, flashcards, and mixed selection.
- Repeat-until-correct core quizzes, error-free trophies, typed and eight-choice pronunciation drills, matching game.
- Validated local progress persistence, separate language scores, session history, backup/restore.
- Included fonts, licensing/provenance, source package, static web build, and GitHub Pages workflow.

## Verification

The practice rules, actual Flet control/handler flows, and web-build regressions now pass **78 tests**, including eight combinations of phone/desktop widths, language, and script. Tests exercise full core/drill/matching/flashcard completion, trophy persistence, answer hiding, reading normalization, polyphonic answers, duplicate-character handling, eight distinct answer options, rejection of malformed backups, curriculum counts, font coverage, runtime URL resolution, and repairing existing workflows across filenames and run styles. Added checks inject browser save failures and corrupt data, preserve legacy progress, and exercise the real mounted Flet session/MessagePack protocol rather than only a fake page.

The first reported web startup error was Flet 1.0.3's generated bare module path, `pyodide/pyodide.mjs`. Static builds now resolve this URL against `document.baseURI`, so module workers receive a valid absolute URL at both the website root and a GitHub Pages project path. The GitHub workflow uses this corrected build script, and distribution verification rejects an uncorrected module path. The generated JavaScript was evaluated for both paths in Node, and the packaged Pyodide runtime successfully started Python 3.12.7 and loaded micropip. Application code, vocabulary, categories, and progress identifiers were unchanged by this fix.

The static package is checked against current source hashes, curriculum counts, pinned runtime dependency, custom fonts, and Pyodide/CanvasKit files. These checks do not establish rendered browser behavior. A managed browser preview was unavailable in this environment, so rendered visual QA, clipboard permissions, actual browser storage, and Chinese IME behavior need confirmation on the user's browser. The hosted deployment status is checked separately.

A later GitHub Actions screenshot showed the standalone packaged-app check rejecting an unresolved URL. The exact live workflow could not be retrieved, so `tools/repair_pages_workflow.py` repairs the existing workflow files in the user's checkout without assuming their filenames. It ensures the URL repair runs immediately before that check, including when a legacy workflow still uses raw `flet publish`. The repository's workflow also performs this explicit repair. This changes deployment tooling only.

The subsequent 20-item browser audit found a persistence bug: a failed load could leave defaults that later autosaving would write over unreadable stored progress. The new async storage layer keeps the original key/schema, verifies main/shadow/rollback copies, and pauses saving when stored copies cannot be safely read. Explicit restore preserves the existing raw data before replacement. Clipboard errors and empty imports are handled inside their dialogs. Deprecated input-border properties were migrated to Flet 1.0.3's current border API. Curriculum, category IDs, trophy fingerprints, language separation and UI design were preserved. See [BROWSER_AUDIT.md](BROWSER_AUDIT.md) for each supplied pitfall and the remaining browser verification limits.

## Remaining editorial refinements

The complete usable first edition is included. Cantonese has both spoken HK equivalents and shared written vocabulary. Some items use visibly labelled reference examples because an appropriate paired sentence was unavailable. Later revisions can add more natural Cantonese sentences, contextual reading quizzes, additional games, and extra core quiz types without replacing this code or discarding progress.

Data/category changes invalidate only a trophy whose category fingerprint changes. Keep category IDs and question membership stable for routine UI revisions. Save code through Git and copy a progress JSON backup before changing browser origin or clearing browser data.
