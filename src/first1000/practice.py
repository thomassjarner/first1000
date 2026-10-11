"""Practice rules independent of Flet, so scoring and trophies are testable."""
from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence

from .curriculum import Character, Entry


def normalize_hanzi(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).split())


def normalize_reading(value: str, language: str = "mandarin") -> str:
    value = value.lower().strip().replace("u:", "v")
    if language == "cantonese":
        return re.sub(r"[\s'’\-]+", "", value)
    syllables: list[str] = []
    letters = ""
    tone = None
    marks = {"\u0304": 1, "\u0301": 2, "\u030c": 3, "\u0300": 4}

    def flush(explicit=None):
        nonlocal letters, tone
        if letters:
            syllables.append(letters + str(explicit if explicit is not None else tone or 5))
        letters, tone = "", None

    for char in unicodedata.normalize("NFD", value):
        if char.isascii() and char.isalpha():
            letters += char
        elif char == "\u0308" and letters.endswith("u"):
            letters = letters[:-1] + "v"
        elif char in marks:
            tone = marks[char]
        elif char.isdigit():
            flush(5 if char == "0" else int(char))
        elif unicodedata.combining(char):
            continue
        else:
            flush()
    flush()
    return "".join(syllables)


@dataclass(frozen=True)
class Answer:
    item_id: str
    correct: bool
    given: str
    accepted: tuple[str, ...]


class CoreSession:
    def __init__(self, entries: Sequence[Entry], language: str, traditional: bool, rng: random.Random | None = None, shuffle: bool = True):
        self.items = list({entry.id: entry for entry in entries}.values())
        if not self.items:
            raise ValueError("Select at least one nonempty category")
        self.language, self.traditional = language, traditional
        if shuffle:
            (rng or random.Random()).shuffle(self.items)
        self.index = 0
        self.attempts = 0
        self.mistakes = 0
        self.answers: list[Answer] = []

    @property
    def current(self) -> Entry:
        if self.finished:
            raise ValueError("The quiz is finished")
        return self.items[self.index]

    @property
    def finished(self) -> bool:
        return self.index == len(self.items)

    @property
    def perfect(self) -> bool:
        return self.finished and self.mistakes == 0

    @property
    def accuracy(self) -> float:
        return (self.attempts - self.mistakes) / self.attempts if self.attempts else 0

    def answer(self, value: str) -> Answer:
        if not value.strip():
            raise ValueError("Enter a Chinese character or word")
        entry = self.current
        accepted = entry.accepted_spellings(self.language, self.traditional)
        correct = normalize_hanzi(value) in {normalize_hanzi(x) for x in accepted}
        result = Answer(entry.id, correct, value.strip(), accepted)
        self.attempts += 1
        self.mistakes += int(not correct)
        self.answers.append(result)
        if correct:
            self.index += 1
        return result


class DrillSession:
    def __init__(self, characters: Sequence[Character], language: str, reading_pool: Sequence[Character], rng: random.Random | None = None):
        self.items = list({char.glyph: char for char in characters}.values())
        if not self.items:
            raise ValueError("Select a category with characters to practise")
        self.language = language
        self.rng = rng or random.Random()
        self.rng.shuffle(self.items)
        self.pool = tuple(dict.fromkeys(reading for char in reading_pool for reading in char.readings(language)))
        self.index = 0
        self.answers: list[Answer] = []
        self.pending: Answer | None = None
        self._options: list[str] | None = None

    @property
    def current(self) -> Character:
        if self.finished:
            raise ValueError("The drill is finished")
        return self.items[self.index]

    @property
    def finished(self) -> bool:
        return self.index == len(self.items)

    @property
    def correct_count(self) -> int:
        return sum(x.correct for x in self.answers)

    @property
    def accuracy(self) -> float:
        return self.correct_count / len(self.answers) if self.answers else 0

    def options(self) -> list[str]:
        if self._options is None:
            valid = self.current.readings(self.language)
            normalized = {normalize_reading(x, self.language) for x in valid}
            distractors = list(dict.fromkeys(x for x in self.pool if normalize_reading(x, self.language) not in normalized))
            if len(distractors) < 7:
                raise ValueError("The curriculum needs at least eight distinct readings")
            options = [self.rng.choice(valid), *self.rng.sample(distractors, 7)]
            self.rng.shuffle(options)
            self._options = options
        return list(self._options)

    def answer(self, value: str) -> Answer:
        if self.pending is not None:
            raise ValueError("This character has already been answered")
        if not value.strip():
            raise ValueError("Enter a reading with its tone number")
        accepted = self.current.readings(self.language)
        correct = normalize_reading(value, self.language) in {normalize_reading(x, self.language) for x in accepted}
        self.pending = Answer(self.current.glyph, correct, value.strip(), accepted)
        self.answers.append(self.pending)
        return self.pending

    def advance(self) -> None:
        if self.pending is None:
            raise ValueError("Answer this character first")
        self.index += 1
        self.pending, self._options = None, None


class MatchSession:
    def __init__(self, entries: Sequence[Entry], language: str, traditional: bool, rng: random.Random | None = None, size: int = 6):
        rng = rng or random.Random()
        candidates = list(entries)
        rng.shuffle(candidates)
        self.items: list[Entry] = []
        text_seen, meaning_seen = set(), set()
        for entry in candidates:
            text = entry.text(language, traditional)
            if text in text_seen or entry.meaning in meaning_seen:
                continue
            self.items.append(entry)
            text_seen.add(text)
            meaning_seen.add(entry.meaning)
            if len(self.items) == size:
                break
        if len(self.items) < 2:
            raise ValueError("Select a category with at least two different words")
        self.left = list(self.items)
        self.right = list(self.items)
        rng.shuffle(self.left)
        rng.shuffle(self.right)
        self.matched: set[str] = set()
        self.attempts = 0
        self.answers: list[Answer] = []

    @property
    def finished(self) -> bool:
        return len(self.matched) == len(self.items)

    @property
    def accuracy(self) -> float:
        return len(self.matched) / self.attempts if self.attempts else 0

    def answer(self, left_id: str, right_id: str) -> Answer:
        valid = {x.id for x in self.items}
        if left_id not in valid or right_id not in valid or left_id in self.matched or right_id in self.matched:
            raise ValueError("Choose two unmatched cards")
        correct = left_id == right_id
        self.attempts += 1
        if correct:
            self.matched.add(left_id)
        result = Answer(left_id, correct, right_id, (left_id,))
        self.answers.append(result)
        return result


class SentenceSession:
    """Read a complete sentence and associate it with its English meaning."""
    def __init__(self, entries, rng=None):
        self.items = list({entry.id: entry for entry in entries if entry.kind == "sentence"}.values())
        if len({entry.meaning for entry in self.items}) < 4:
            raise ValueError("Select a situation containing at least four sentence meanings")
        self.rng = rng or random.Random()
        self.rng.shuffle(self.items)
        self.index = 0
        self.answers = []
        self.pending = None
        self._options = None

    @property
    def current(self):
        return self.items[self.index]

    @property
    def finished(self):
        return self.index == len(self.items)

    @property
    def correct_count(self):
        return sum(answer.correct for answer in self.answers)

    def options(self):
        if self._options is None:
            others = sorted({entry.meaning for entry in self.items} - {self.current.meaning})
            self._options = [self.current.meaning, *self.rng.sample(others, 3)]
            self.rng.shuffle(self._options)
        return list(self._options)

    def answer(self, value):
        if self.pending is not None:
            raise ValueError("Continue to the next sentence")
        if value not in self.options():
            raise ValueError("Choose one of the sentence meanings")
        self.pending = Answer(self.current.id, value == self.current.meaning, value, (self.current.meaning,))
        self.answers.append(self.pending)
        return self.pending

    def advance(self):
        if self.pending is None:
            raise ValueError("Choose a meaning first")
        self.index += 1
        self.pending, self._options = None, None
