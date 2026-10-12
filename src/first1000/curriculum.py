"""Read the precomputed curriculum. No dictionaries or network calls at runtime."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

LANGUAGES = ("mandarin", "cantonese")


@dataclass(frozen=True)
class Entry:
    data: dict

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def meaning(self) -> str:
        return self.data["english"]

    @property
    def hsk(self) -> int | None:
        return self.data.get("hsk")

    @property
    def frequency(self) -> int:
        return self.data.get("frequency") or 999999

    @property
    def kind(self) -> str:
        return self.data.get("kind", "vocabulary")

    def text(self, language: str, traditional: bool) -> str:
        script = "traditional" if traditional else "simplified"
        return self.data[f"{language}_{script}"]

    def reading(self, language: str) -> str:
        return self.data["pinyin" if language == "mandarin" else "jyutping"]

    def example(self, language: str, traditional: bool) -> dict:
        example = dict(self.data.get("examples", {}).get(language, {}))
        example["text"] = example.get("traditional" if traditional else "simplified", "")
        return example

    def accepted_spellings(self, language: str, traditional: bool) -> tuple[str, ...]:
        key = f"{language}_{'traditional' if traditional else 'simplified'}"
        return tuple(dict.fromkeys([self.text(language, traditional), *self.data.get("accepted", {}).get(key, [])]))


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    theme: str
    kind: str
    hsk: int | None
    entry_ids: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class Character:
    glyph: str
    pinyin: tuple[str, ...]
    jyutping: tuple[str, ...]
    meaning: str
    rank: int | None = None
    target_ids: tuple[str, ...] = ()

    def readings(self, language: str) -> tuple[str, ...]:
        return self.pinyin if language == "mandarin" else self.jyutping


class Curriculum:
    def __init__(self, payload: dict):
        if payload.get("schema") != 1:
            raise ValueError("Unsupported curriculum format")
        self.meta = payload["meta"]
        self.entries = {x["id"]: Entry(x) for x in payload["entries"]}
        self.categories = [Category(**{**x, "entry_ids": tuple(x["entry_ids"])}) for x in payload["categories"]]
        self.category_map = {x.id: x for x in self.categories}
        self.characters = {glyph: Character(glyph=glyph, **{**x, "pinyin": tuple(x["pinyin"]), "jyutping": tuple(x["jyutping"]), "target_ids": tuple(x.get("target_ids", []))}) for glyph, x in payload["characters"].items()}
        self.target_characters = tuple(payload["target_characters"])
        self.vocabulary_ids = tuple(payload["vocabulary_entry_ids"])
        self.entry_categories: dict[str, list[Category]] = {key: [] for key in self.entries}
        for category in self.categories:
            for entry_id in category.entry_ids:
                if entry_id not in self.entries:
                    raise ValueError(f"Unknown entry {entry_id} in {category.id}")
                self.entry_categories[entry_id].append(category)

    @classmethod
    def load(cls, path: Path | None = None) -> "Curriculum":
        path = path or Path(__file__).with_name("data") / "curriculum.json"
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def add_everyday_content(self):
        """Add new IDs without changing original categories or fingerprints."""
        if hasattr(self, "cantonese_targets"):
            return
        payload = json.loads(Path(__file__).with_name("data").joinpath("everyday.json").read_text(encoding="utf-8"))
        self.cantonese_targets = tuple(payload["cantonese_targets"])
        for glyph, data in payload.get("characters", {}).items():
            self.characters[glyph] = Character(glyph=glyph, **{**data, "pinyin": tuple(data["pinyin"]), "jyutping": tuple(data["jyutping"]), "target_ids": tuple(data.get("target_ids", []))})
        for data in payload["entries"]:
            entry = Entry(data)
            self.entries[entry.id] = entry
            self.entry_categories[entry.id] = []
        for data in payload["categories"]:
            cat = Category(**{**data, "entry_ids": tuple(data["entry_ids"])})
            self.categories.append(cat)
            self.category_map[cat.id] = cat
            for entry_id in cat.entry_ids:
                self.entry_categories[entry_id].append(cat)

    def drill_key(self,glyph):
        return "glyph:"+glyph

    def character_key(self, glyph):
        if not hasattr(self, "character_aliases"):
            self.character_aliases=json.loads(Path(__file__).with_name("data").joinpath("character_aliases.json").read_text(encoding="utf-8"))
        return "character:"+self.character_aliases.get(glyph,glyph)

    def character_example(self, glyph, language, traditional):
        cache_key=(language,traditional)
        if not hasattr(self,"character_examples"):self.character_examples={}
        if cache_key not in self.character_examples:
            examples={}
            for entry in self.entries.values():
                example=entry.example(language,traditional)
                text=example.get("text","")
                if not text or example.get("source")=="Reference":continue
                for char in set(text):
                    if "\u3400"<=char<="\u9fff" and (char not in examples or len(text)<len(examples[char]["text"])):
                        examples[char]={**example,"entry_id":entry.id}
            self.character_examples[cache_key]=examples
        found=self.character_examples[cache_key].get(glyph)
        if found:return found
        text=(f"「{glyph}」是什麼意思？" if traditional else f"「{glyph}」是什么意思？") if language=="mandarin" else (f"「{glyph}」係咩意思？" if traditional else f"「{glyph}」系咩意思？")
        return {"text":text,"english":"What does this character mean?","source":"Reference"}

    def practice_entries(self, category_ids):
        path = Path(__file__).with_name("data") / "practice_sets.json"
        if not hasattr(self, "practice_sets"):
            self.practice_sets = json.loads(path.read_text(encoding="utf-8"))["sets"]
        ids = dict.fromkeys(eid for cid in category_ids for eid in self.practice_sets.get(cid, self.category_map[cid].entry_ids))
        return [self.entries[eid] for eid in ids]

    def learned_key(self, entry, language):
        text = entry.text(language, False)
        return "character:" + text if len(text) == 1 else "entry:" + entry.id

    def target_learned_keys(self, language):
        prefix = "cant-char:" if language == "cantonese" and hasattr(self, "cantonese_targets") else "c:"
        return [self.learned_key(self.entries[prefix+glyph], language) for glyph in self.targets(language) if prefix+glyph in self.entries]

    def targets(self, language):
        return getattr(self, "cantonese_targets", self.target_characters) if language == "cantonese" else self.target_characters

    def selected_entries(self, category_ids: Iterable[str]) -> list[Entry]:
        selected = set(category_ids)
        ids = dict.fromkeys(entry_id for category in self.categories if category.id in selected for entry_id in category.entry_ids)
        return [self.entries[x] for x in ids]

    def selected_characters(self, category_ids: Iterable[str], language: str, traditional: bool, enriched: bool = False) -> list[Character]:
        glyphs = dict.fromkeys(glyph for entry in (self.practice_entries(category_ids) if enriched else self.selected_entries(category_ids)) for glyph in entry.text(language, traditional) if glyph in self.characters)
        return [self.characters[glyph] for glyph in glyphs]

    def fingerprint(self, category_id: str, language: str) -> str:
        category = self.category_map[category_id]
        contents = [(entry_id, self.entries[entry_id].text(language, False), self.entries[entry_id].text(language, True), self.entries[entry_id].meaning) for entry_id in category.entry_ids]
        return hashlib.sha256(json.dumps(contents, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:20]

    def dictionary(self, query: str = "", language: str = "mandarin", traditional: bool = False, sort: str = "frequency", category_id: str = "all", hsk: str = "all") -> list[Entry]:
        candidates = self.practice_entries([category_id]) if category_id != "all" else list(self.entries.values())
        query = query.strip().lower()
        if hsk != "all":
            candidates = [entry for entry in candidates if (entry.hsk == int(hsk) if hsk.isdigit() else entry.kind == "hong_kong")]
        if query:
            candidates = [entry for entry in candidates if query in " ".join([entry.meaning, entry.reading(language), entry.data.get("pinyin_numbers", ""), entry.text(language, False), entry.text(language, True), *[x.title for x in self.entry_categories[entry.id]]]).lower()]
        def reading_key(entry):
            value = entry.data.get("pinyin_numbers", entry.reading(language)) if language == "mandarin" else entry.reading(language)
            return re.sub(r"[0-9\s]", "", value.lower())
        if sort == "hsk":
            key = lambda entry: (entry.hsk or 99, reading_key(entry))
        elif sort == "alphabetical":
            key = lambda entry: (reading_key(entry), entry.text(language, traditional))
        elif sort == "meaning":
            key = lambda entry: entry.meaning.lower()
        elif sort == "category":
            key = lambda entry: (self.entry_categories[entry.id][0].title if self.entry_categories[entry.id] else "", entry.frequency)
        else:
            key = lambda entry: (entry.frequency, entry.text(language, traditional))
        return sorted(candidates, key=key)
