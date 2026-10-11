"""Portable, validated progress. Each language has its own scores and trophies."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

from .curriculum import Curriculum, LANGUAGES, Character

STORAGE_KEY = "first1000.progress.v1"
MAX_BACKUP_BYTES = 2_000_000


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def language_state() -> dict:
    return {"attempts": 0, "correct": 0, "trophies": {}, "characters": {}, "sessions": [], "flashcards": 0}


class Progress:
    def __init__(self, data: dict | None = None):
        self.data = data or {"app": "first1000", "schema": 1, "settings": {"dark": False, "language": "mandarin", "traditional": False}, "languages": {lang: language_state() for lang in LANGUAGES}, "updated_at": now()}

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def state(self, language: str) -> dict:
        return self.data["languages"][language]

    def record_answer(self, language: str, correct: bool, character: Character | None = None) -> None:
        state = self.state(language)
        state["attempts"] += 1
        state["correct"] += int(correct)
        if character:
            stats = state["characters"].setdefault(character.glyph, {"attempts": 0, "correct": 0, "target_ids": list(character.target_ids)})
            stats["attempts"] += 1
            stats["correct"] += int(correct)
            stats["target_ids"] = list(character.target_ids)
        self.data["updated_at"] = now()

    def finish(self, language: str, mode: str, total: int, correct: int, attempts: int, category_ids: list[str], perfect: bool = False, curriculum: Curriculum | None = None) -> list[str]:
        state = self.state(language)
        state["sessions"].append({"mode": mode, "total": total, "correct": correct, "attempts": attempts, "category_ids": list(category_ids), "finished_at": now()})
        state["sessions"] = state["sessions"][-300:]
        earned = []
        if mode == "core" and perfect and curriculum:
            for category_id in category_ids:
                fingerprint = curriculum.fingerprint(category_id, language)
                if not self.has_trophy(language, category_id, curriculum):
                    earned.append(category_id)
                state["trophies"][category_id] = {"earned_at": now(), "fingerprint": fingerprint}
        self.data["updated_at"] = now()
        return earned

    def has_trophy(self, language: str, category_id: str, curriculum: Curriculum) -> bool:
        record = self.state(language)["trophies"].get(category_id)
        return bool(record and category_id in curriculum.category_map and record.get("fingerprint") == curriculum.fingerprint(category_id, language))

    def summary(self, language: str, curriculum: Curriculum) -> dict:
        state = self.state(language)
        practised = set(target for record in state["characters"].values() if record["attempts"] for target in record["target_ids"])
        practised &= set(curriculum.target_characters)
        return {"attempts": state["attempts"], "accuracy": state["correct"] / state["attempts"] if state["attempts"] else None, "trophies": sum(self.has_trophy(language, cat.id, curriculum) for cat in curriculum.categories), "characters": len(practised), "sessions": len(state["sessions"])}

    def export(self) -> str:
        return json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "Progress":
        if not isinstance(text, str):
            raise ValueError("Paste a valid First 1000 JSON backup")
        if len(text.encode("utf-8")) > MAX_BACKUP_BYTES:
            raise ValueError("This backup is too large")
        try:
            incoming = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            raise ValueError("Paste a valid First 1000 JSON backup") from None
        if not isinstance(incoming, dict) or incoming.get("app") != "first1000" or incoming.get("schema") != 1:
            raise ValueError("This is not a supported First 1000 backup")
        settings = incoming.get("settings", {})
        if not isinstance(settings, dict) or settings.get("language") not in LANGUAGES or type(settings.get("dark")) is not bool or type(settings.get("traditional")) is not bool:
            raise ValueError("The backup settings are invalid")
        languages = incoming.get("languages")
        if not isinstance(languages, dict) or set(languages) != set(LANGUAGES):
            raise ValueError("The backup must contain separate Mandarin and Cantonese progress")
        for language in LANGUAGES:
            state = languages[language]
            if not isinstance(state, dict):
                raise ValueError("Invalid progress section")
            for key in ("attempts", "correct", "flashcards"):
                value = state.get(key)
                if type(value) is not int or value < 0 or value > 100_000_000:
                    raise ValueError("Invalid practice counts")
            if state["correct"] > state["attempts"]:
                raise ValueError("Correct answers cannot exceed attempts")
            trophies, chars, sessions = state.get("trophies"), state.get("characters"), state.get("sessions")
            if not isinstance(trophies, dict) or len(trophies) > 1000 or not isinstance(chars, dict) or len(chars) > 20000 or not isinstance(sessions, list) or len(sessions) > 300:
                raise ValueError("Invalid progress records")
            for key, record in trophies.items():
                if not isinstance(key, str) or not isinstance(record, dict) or not isinstance(record.get("earned_at"), str) or not isinstance(record.get("fingerprint"), str):
                    raise ValueError("Invalid trophy record")
            for glyph, record in chars.items():
                if not isinstance(glyph, str) or len(glyph) != 1 or not isinstance(record, dict):
                    raise ValueError("Invalid character record")
                a, c, targets = record.get("attempts"), record.get("correct"), record.get("target_ids")
                if type(a) is not int or type(c) is not int or not 0 <= c <= a <= 100_000_000 or not isinstance(targets, list) or any(not isinstance(x, str) or len(x) != 1 for x in targets):
                    raise ValueError("Invalid character scores")
            for session in sessions:
                if not isinstance(session, dict) or session.get("mode") not in ("core", "drill", "match", "flashcards"):
                    raise ValueError("Invalid session record")
                for key in ("total", "correct", "attempts"):
                    if type(session.get(key)) is not int or not 0 <= session[key] <= 100_000_000:
                        raise ValueError("Invalid session counts")
                if session["correct"] > session["attempts"] or not isinstance(session.get("finished_at"), str) or not isinstance(session.get("category_ids"), list) or any(not isinstance(x, str) for x in session["category_ids"]):
                    raise ValueError("Invalid session details")
        return cls(copy.deepcopy(incoming))
