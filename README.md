# First 1000

A character-first Mandarin and Cantonese learning app, written in Python with **Flet 1.0.3**. Learn in small sets, drill pronunciation, and earn a trophy by completing a fixed character-writing quiz without mistakes.

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
- One core quiz per category: read the English meaning and type Chinese characters. An incorrect answer stays until corrected. A trophy requires an entirely error-free completed run.
- Character drilling with numbered Pinyin or Jyutping, or exactly eight multiple-choice options. The session uses each distinct displayed character once. Recorded alternative readings are accepted for polyphonic characters.
- A six-pair character-to-meaning matching game, graded accuracy, session history, and progress backup/restore.

Mandarin and Cantonese have separate scores and trophies. Simplified and traditional forms share a trophy within a language. Language and script switches are disabled during a practice session; dark mode is always available. Character practice may include extra characters introduced by themed words, while the progress goal remains the 1,000 target characters.

Flashcard ratings are self-assessments and do not affect graded accuracy. Core/matching accuracy counts every attempt, including retries. Driller accuracy uses the first and only answer to each character.

## Progress and backups

Progress is saved in the browser or Flet client on the current device using SharedPreferences. There is no account or cloud synchronization. A different browser, private window, device, or website origin has separate progress.

Open **Progress → Copy / view progress backup**, copy the JSON, and save it in a text file. To move devices, paste that file into **Restore backup**. Restoration validates the complete backup before replacing saved progress. It contains both languages and settings. If storage is unavailable, the app displays a message and retains the current progress in memory.

## Publish to GitHub Pages

1. Create an empty GitHub repository and upload this project, including the `.github` folder. Do not upload `.venv` or `dist`.
2. In the repository, open **Settings → Pages → Build and deployment**, and choose **GitHub Actions**.
3. Push to `main`, or run the **Deploy Flet web app** workflow manually. It runs the practice/UI tests, builds the Flet static website, and deploys it.
4. Open the Pages URL shown by the deployment job. The workflow sets the correct base path for either a project repository or a `username.github.io` repository.

To make a static build yourself:

```sh
flet publish . --python-version 3.12 --distpath dist --no-cdn --route-url-strategy hash
python -m http.server 8000 --directory dist
```

Open `http://localhost:8000`. Serve the folder over HTTP; opening `index.html` as a local file will not run Python in the browser. A project hosted under a path such as `/first1000/` also needs `--base-url /first1000/` when publishing.

The static app runs Python through Pyodide. The first load downloads a Python/WebAssembly runtime and the Flet package, so allow it time to start. `--no-cdn` includes the runtime and CanvasKit in the website; Python package installation still needs network access on first load. This is not an offline guarantee.

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Architecture:

| File | Responsibility |
|---|---|
| `src/main.py` | Flet entry point |
| `src/first1000/ui.py` | Screens, controls, async storage, and event handlers |
| `src/first1000/curriculum.py` | Immutable curriculum models, filtering, and category membership |
| `src/first1000/practice.py` | Core quiz, pronunciation drill, and matching rules |
| `src/first1000/progress.py` | Per-language scores, content-fingerprinted trophies, and backup validation |
| `src/first1000/data/curriculum.json` | Precomputed learning content; no language packages needed at runtime |
| `tools/build_curriculum.py` | Reproducible content preparation and font subsetting |
| `tests/` | Scoring, curriculum, persistence, and actual Flet control/handler checks |

See [THIRD_PARTY.md](THIRD_PARTY.md) for attribution and [RECOVERY_AND_STATUS.md](RECOVERY_AND_STATUS.md) for what could be recovered and the verification limits.

## Content notes

HSK labels explicitly use the **2012 six-level syllabus**, not the newer nine-band standard. Themes and small-set divisions are editorial learning groups. Character and word frequency ranks come from different source lists and should be treated as relative sorting aids.

Cantonese mode uses curated everyday Hong Kong lexical equivalents where available and Jyutping throughout. Other HSK headwords are labelled shared written vocabulary. Grammar words have sense-specific mappings and usage notes; they are not mechanical translation rules. Tone-number drills accept recorded dictionary alternatives, which can include less common readings; choose the reading appropriate to context when learning whole words.

Examples have one of three visible labels: an attributed Tatoeba sentence, an original authored example, or a reference sentence asking what the word means. Reference sentences are used when no suitable paired example was found. They are not presented as a native corpus example. The curriculum is an attributed first edition and remains suitable for later editorial review, especially additional Cantonese sentence examples.

Application code: MIT. Compiled vocabulary material: CC BY-SA 3.0, with separately attributed Tatoeba examples under CC BY 2.0 FR, Unicode data under Unicode License v3, and bundled fonts under SIL OFL 1.1. See the included notices before redistributing content.
