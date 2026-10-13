"""Portable, validated progress. Each language has its own scores and trophies."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

from .curriculum import Curriculum, LANGUAGES, Character

STORAGE_KEY = "first1000.progress.v1"
MAX_BACKUP_BYTES = 12_000_000


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def language_state() -> dict:
    return {"attempts": 0, "correct": 0, "trophies": {}, "characters": {}, "sessions": [], "flashcards": 0, "learned": {}, "drill_outcomes": {}}


class Progress:
    def __init__(self, data: dict | None = None):
        self.data = data or {"app": "first1000", "schema": 1, "settings": {"dark": False, "language": "mandarin", "traditional": False}, "languages": {lang: language_state() for lang in LANGUAGES}, "updated_at": now()}

        for language in LANGUAGES:
            self.data["languages"][language].setdefault("learned", {})
            self.data["languages"][language].setdefault("drill_outcomes", {})
            self.data["languages"][language].setdefault("word_learning", {})
            self.data["languages"][language].setdefault("character_learning", {})
            self.data["languages"][language].setdefault("character_sessions", {})
            self.data["languages"][language].setdefault("frameworks_separated", False)

    def is_learned(self, language, key):
        return key in self.state(language)["learned"]

    def set_learned(self, language, key, value):
        if value:
            self.state(language)["learned"][key] = now()
        else:
            self.state(language)["learned"].pop(key, None)
        self.data["updated_at"] = now()

    def migrate_frameworks(self,curriculum):
        for language in LANGUAGES:
            state=self.state(language)
            if state["frameworks_separated"]:continue
            for entry in curriculum.entries.values():
                if entry.kind not in ("vocabulary","hong_kong","sentence"):continue
                key=curriculum.learned_key(entry,language)
                if key in state["learned"]:
                    state["word_learning"].setdefault(entry.id,state["learned"][key])
            state["frameworks_separated"]=True

    def is_word_learned(self,language,entry_id):
        return entry_id in self.state(language)["word_learning"]

    def set_word_learned(self,language,entry_id,value):
        if value:self.state(language)["word_learning"][entry_id]=now()
        else:self.state(language)["word_learning"].pop(entry_id,None)
        self.data["updated_at"]=now()

    def is_character_learned(self,language,glyph):
        return glyph in self.state(language)["character_learning"]

    def learn_typed_character(self,language,glyph):
        self.state(language)["character_learning"][glyph]=now()
        self.data["updated_at"]=now()

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def state(self, language: str) -> dict:
        return self.data["languages"][language]

    def migrate_drill_outcomes(self,curriculum):
        for language in LANGUAGES:
            inferred={}
            state=self.state(language)
            for glyph,record in state["characters"].items():
                if not record["attempts"]:continue
                key=curriculum.drill_key(glyph)
                status="correct" if record["correct"]==record["attempts"] else "incorrect"
                if key not in inferred or status=="incorrect":inferred[key]=status
            for key,status in inferred.items():
                state["drill_outcomes"].setdefault(key,{"status":status,"updated_at":self.data.get("updated_at",now())})

    def drill_status(self,language,key):
        return self.state(language)["drill_outcomes"].get(key,{}).get("status","unseen")

    def record_answer(self,language,correct,character=None,status=None,status_key=None):
        # Session accuracy lives on the active session/result, not in saved totals.
        # Retain historical aggregate fields unchanged for old backups.
        if character:
            state=self.state(language)
            record=state["characters"].setdefault(character.glyph,{"attempts":1,"correct":0,"target_ids":list(character.target_ids)})
            record["attempts"]=max(record["attempts"],1)
            record["target_ids"]=list(character.target_ids)
            key=status_key or "glyph:"+character.glyph
            state["drill_outcomes"][key]={"status":status or ("correct" if correct else "incorrect"),"updated_at":now()}
        self.data["updated_at"]=now()

    def finish(self, language: str, mode: str, total: int, correct: int, attempts: int, category_ids: list[str], perfect: bool = False, curriculum: Curriculum | None = None) -> list[str]:
        state = self.state(language)
        state["sessions"].append({"mode":mode,"total":total,"category_ids":list(category_ids),"finished_at":now(),"score_saved":False})
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
        practised &= set(curriculum.targets(language))
        return {"learned": sum(key in state["learned"] for key in curriculum.target_learned_keys(language)), "learned_entries": len(state["learned"]), "attempts": state["attempts"], "accuracy": None, "trophies": sum(self.has_trophy(language, cat.id, curriculum) for cat in curriculum.categories), "characters": len(practised), "sessions": len(state["sessions"])}

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
            learned = state.get("learned", {})
            if not isinstance(learned, dict) or len(learned) > 20000 or any(not isinstance(key, str) or not 1 <= len(key) <= 256 or not isinstance(value, str) or not 1 <= len(value) <= 64 for key, value in learned.items()):
                raise ValueError("Invalid learned records")
            from .character_framework import validate_snapshot
            for field in ("word_learning","character_learning"):
                mapping=state.get(field,{})
                if not isinstance(mapping,dict) or len(mapping)>20000 or any(not isinstance(key,str) or not 1<=len(key)<=256 or not isinstance(value,str) or not 1<=len(value)<=64 for key,value in mapping.items()):raise ValueError("Invalid separated learning records")
                if field=="character_learning" and any(len(key)!=1 for key in mapping):raise ValueError("Invalid learned character")
            if type(state.get("frameworks_separated",False)) is not bool:raise ValueError("Invalid learning migration state")
            checkpoints=state.get("character_sessions",{})
            if not isinstance(checkpoints,dict) or len(checkpoints)>256:raise ValueError("Invalid saved character sessions")
            for key,value in checkpoints.items():
                if not isinstance(key,str) or not 1<=len(key)<=140:raise ValueError("Invalid saved character group")
                validate_snapshot(value)
                if not isinstance(value.get("updated_at",""),str):raise ValueError("Invalid checkpoint timestamp")
                from .character_framework import session_key
                if key!=session_key(value["group_id"],value["traditional"]):raise ValueError("Saved character group mismatch")
            outcomes=state.get("drill_outcomes",{})
            if not isinstance(outcomes,dict) or len(outcomes)>20000 or any(not isinstance(key,str) or not 1<=len(key)<=256 or not isinstance(record,dict) or record.get("status") not in ("correct","almost","incorrect") or not isinstance(record.get("updated_at"),str) for key,record in outcomes.items()):
                raise ValueError("Invalid drill outcomes")
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
                if not isinstance(session, dict) or session.get("mode") not in ("core", "drill", "match", "flashcards", "sentence"):
                    raise ValueError("Invalid session record")
                for key in (("total",) if session.get("score_saved") is False else ("total","correct","attempts")):
                    if type(session.get(key)) is not int or not 0 <= session[key] <= 100_000_000:
                        raise ValueError("Invalid session counts")
                if (session.get("score_saved") is not False and session["correct"] > session["attempts"]) or not isinstance(session.get("finished_at"), str) or not isinstance(session.get("category_ids"), list) or any(not isinstance(x, str) for x in session["category_ids"]):
                    raise ValueError("Invalid session details")
        return cls(copy.deepcopy(incoming))
