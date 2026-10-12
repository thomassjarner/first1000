# First 1000

A character-first Mandarin and Cantonese learning app, written in Python with **Flet 1.0.3**. Learn in small sets, drill pronunciation, and mark characters learned and earn trophies through one-pass recognition quizzes.

## Changes in version 0.3.0

**Learned** checkboxes in dictionary rows and Details save your explicit learning status. Learned and Still learning filters make it easy to find the right cards. Status is separate by language and shared across script forms. Progress shows learned target characters separately from characters merely practised. On flashcards, **I knew it** also marks the card learned; **Still learning** clears that mark.

All flashcard/practice sets now have at least **15 cards**. Small situations combine their four original sentences with related vocabulary. Small vocabulary groups add related words from other levels. Original category memberships and existing trophy fingerprints stay intact; supplementary practice membership is stored separately in `practice_sets.json`.

The handwriting-from-English quiz is replaced by **Chinese-to-meaning recognition**, with sentence context when available. Each card accepts one answer, shows the correction and reading, then continues with Next (or Enter after feedback). Matching mistakes also finish the attempted card and show the correct pair; each pair is scored once. Character and sentence drills retain the same one-answer correction/continue flow.

**Pick all categories** selects every category for the current language, even when the list is filtered. Dictionary sort buttons reverse direction when clicked again; Frequency toggles most-common/least-common first, while unranked entries stay last.

The responsive layout and page-edge scrollbar from 0.2.2 remain. Cantonese still has a separate provisional character order based on spoken essentials and bundled examples, rather than a representative general-language frequency corpus. Twelve situations retain 48 original Mandarin/spoken Cantonese sentences.

See [UPDATE_0.3.0.md](UPDATE_0.3.0.md) for details.

## Start using it

Python 3.12 is recommended. Download and extract this project, then open a terminal in its folder:

```sh
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```sh
source .venv/bin/activate
```

Install the app and Flet command line tools:

```sh
python -m pip install -r requirements.txt flet-cli==1.0.3
flet run --web src/main.py
```

The command opens the app in a browser. Keep the terminal running while you use this local version. You do **not** need to rebuild the curriculum to run it: the complete curriculum and fonts are already included.

## What is included

- Home navigation, dark mode, Cantonese mode, and Hong Kong traditional characters.
- **1,000 frequency-ranked characters** in 40 fixed sets of 25.
- **1,231 words and phrases**: 1,193 unique headwords from HSK 2012 levels 1–4 and 38 everyday Hong Kong phrases, in 93 small themed sets.
- Category dictionaries, flashcards, mixed-category practice, and a searchable general dictionary. The dictionary has 2,231 records including the separately labelled character cards.
- One recognition quiz per category: read Chinese, use the example context, and choose the meaning. Each card has one scored attempt. The answer is revealed before continuing; an entirely error-free run earns a trophy.
- Character drilling with numbered Pinyin or Jyutping, or exactly eight multiple-choice options. The session uses each distinct displayed character once. Recorded alternative readings are accepted for polyphonic characters.
- A six-pair character-to-meaning matching game, graded accuracy, session history, and progress backup/restore.

Mandarin and Cantonese have separate scores and trophies. Simplified and traditional forms share learned status and trophies within a language. Sentence meaning sessions record scores and history but do not award core trophies. Language and script switches are disabled during a practice session; dark mode is always available. Character practice may include extra characters introduced by themed words, while the progress goal remains the 1,000 target characters.

Flashcard ratings are explicit self-assessments that update Learned status and do not affect graded accuracy. Recognition and matching accuracy count each card once, without same-card retries. Driller accuracy uses the first and only answer to each character.

## Progress and backups

Progress is saved in the browser or Flet client on the current device using SharedPreferences. There is no account or cloud synchronization. A different browser, private window, device, or website origin has separate progress.

Open **Progress → Copy / view progress backup**, copy the JSON, and save it in a text file. To move devices, paste that file into **Restore backup**. The backup contains both languages and settings. If clipboard access is denied, the JSON stays visible for manual selection and copying.

The existing `first1000.progress.v1` key and schema are preserved. Saves verify a main copy, a shadow copy, and the previous valid rollback copy. Loading never writes defaults over existing data. Unreadable data, inconsistent copies, a failed save, or an observed change from another tab pauses automatic saving and displays a warning. Progress stays usable in memory; export it before closing.

If a recovery warning appears, copy the normal progress backup and **Copy preserved browser data** in Progress. The latter preserves raw stored copies for recovery and is not a normal importable progress backup. Restore the valid normal backup you want to keep to resume saving. Before replacing stored copies, restoration validates the complete backup and archives the existing raw copies under a separate recovery key. A failed restore leaves the current in-memory progress unchanged. Recovery copies protect against interrupted writes; they do not survive clearing browser site data, and simultaneous tabs cannot be coordinated atomically through SharedPreferences.

## Publish to GitHub Pages

1. Create an empty GitHub repository and upload this project, including the `.github` folder. Do not upload `.venv` or `dist`.
2. In the repository, open **Settings → Pages → Build and deployment**, and choose **GitHub Actions**.
3. Push to `main`, or run the **Deploy Flet web app** workflow manually. It runs the practice/UI tests, builds the Flet static website, and deploys it.
4. Open the Pages URL shown by the deployment job. The workflow sets the correct base path for either a project repository or a `username.github.io` repository.

To make a static build yourself:

```sh
python tools/build_web.py
python -m http.server 8000 --directory dist
```

Open `http://localhost:8000`. Serve the folder over HTTP; opening `index.html` as a local file will not run Python in the browser. A project hosted under a path such as `/first1000/` needs `python tools/build_web.py --base-url /first1000/`.

Use the build script for static publishing. Version 0.1.2 also bundles the pinned Pyodide wheels for msgpack, six, micropip and packaging (including their runtime dependencies), and verifies their lockfile checksums to prevent missing-wheel startup errors. It resolves Flet 1.0.3's local Pyodide module URL against the site's base URL before checking the distribution. A raw `flet publish --no-cdn` build emits a bare module path that the browser cannot import.

The static app runs Python through Pyodide. The first load downloads a Python/WebAssembly runtime and the Flet package, so allow it time to start. `--no-cdn` includes the runtime and CanvasKit in the website; Python package installation still needs network access on first load. This is not an offline guarantee.

If an older GitHub workflow fails with "Pyodide module URL must resolve against document.baseURI", run `python tools/repair_pages_workflow.py` in your working checkout, then commit and push. It adds the URL repair immediately before the packaged-app check in existing `.github/workflows` files, preserving their filenames and other steps. This also works when an older workflow still calls `flet publish` directly. The `.github` folder is hidden in macOS Finder; keep it included when copying updates.

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Architecture:

| File | Responsibility |
|---|---|
| `src/main.py` | Flet entry point |
| `src/first1000/ui.py` | Screens, controls, and async event handlers |
| `src/first1000/curriculum.py` | Immutable curriculum models, filtering, and category membership |
| `src/first1000/practice.py` | Core quiz, pronunciation drill, and matching rules |
| `src/first1000/progress.py` | Per-language scores, content-fingerprinted trophies, and backup validation |
| `src/first1000/storage.py` | Async browser saves, verified recovery copies, and preservation of unreadable data |
| `src/first1000/data/curriculum.json` | Precomputed learning content; no language packages needed at runtime |
| `tools/build_curriculum.py` | Reproducible content preparation and font subsetting |
| `tests/` | Scoring, curriculum, persistence, and actual Flet control/handler checks |

See [THIRD_PARTY.md](THIRD_PARTY.md) for attribution, [RECOVERY_AND_STATUS.md](RECOVERY_AND_STATUS.md) for recovery history, and [BROWSER_AUDIT.md](BROWSER_AUDIT.md) for the 20-item Flet web audit and verification limits.

## Content notes

HSK labels explicitly use the **2012 six-level syllabus**, not the newer nine-band standard. Themes and small-set divisions are editorial learning groups. Character and word frequency ranks come from different source lists and should be treated as relative sorting aids.

Cantonese mode uses curated everyday Hong Kong lexical equivalents where available and Jyutping throughout. Other HSK headwords are labelled shared written vocabulary. Grammar words have sense-specific mappings and usage notes; they are not mechanical translation rules. Tone-number drills accept recorded dictionary alternatives, which can include less common readings; choose the reading appropriate to context when learning whole words.

Examples have one of three visible labels: an attributed Tatoeba sentence, an original authored example, or a reference sentence asking what the word means. Reference sentences are used when no suitable paired example was found. They are not presented as a native corpus example. The curriculum is an attributed first edition and remains suitable for later editorial review, especially additional Cantonese sentence examples.

Application code: MIT. Compiled vocabulary material: CC BY-SA 3.0, with separately attributed Tatoeba examples under CC BY 2.0 FR, Unicode data under Unicode License v3, and bundled fonts under SIL OFL 1.1. See the included notices before redistributing content.
