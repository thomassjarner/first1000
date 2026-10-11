"""Async browser persistence that preserves unreadable and interrupted saves."""
from __future__ import annotations

import asyncio
import hashlib
import json

from .progress import Progress, STORAGE_KEY

SHADOW_KEY = f"{STORAGE_KEY}.shadow"
ROLLBACK_KEY = f"{STORAGE_KEY}.rollback"
COPY_KEYS = (STORAGE_KEY, SHADOW_KEY, ROLLBACK_KEY)


class ProgressStore:
    def __init__(self, preferences):
        self.preferences = preferences
        self.loaded = False
        self.blocked = True
        self.message = "Saved progress has not been checked yet."
        self.loaded_values = {}
        self.current_values = {}
        self.read_errors = []
        self.recovery_snapshot = None
        self._last_good = None
        self._lock = asyncio.Lock()

    async def load(self) -> Progress:
        async with self._lock:
            valid, invalid = {}, []
            self.read_errors = []
            self.loaded_values = {}
            for key in COPY_KEYS:
                try:
                    value = await self.preferences.get(key)
                except Exception:
                    self.read_errors.append(key)
                    continue
                self.loaded_values[key] = value
                if value is not None:
                    try:
                        valid[key] = Progress.from_json(value)
                    except ValueError:
                        invalid.append(key)
            self.current_values = dict(self.loaded_values)
            selected = next((key for key in COPY_KEYS if key in valid), None)
            progress = valid[selected] if selected else Progress()
            self._last_good = self.loaded_values[selected] if selected else None
            different_copies = (
                STORAGE_KEY in valid and SHADOW_KEY in valid
                and valid[STORAGE_KEY].data != valid[SHADOW_KEY].data
            )
            recovered = selected is not None and selected != STORAGE_KEY
            self.blocked = bool(self.read_errors or invalid or different_copies or recovered)
            self.loaded = True
            if self.blocked:
                reason = (
                    "Usable progress was recovered from a browser backup. " if recovered else
                    "Different saved copies were found; the main copy was loaded. " if different_copies else
                    "Your browser's saved progress could not be fully read. "
                )
                self.message = reason + "Automatic saving is paused to preserve the original data. Copy a backup in Progress, then restore a valid progress backup to resume saving."
            else:
                self.message = ""
            return progress

    async def _write_verified(self, key: str, value: str) -> None:
        if await self.preferences.set(key, value) is not True:
            raise RuntimeError("Browser storage rejected the write")
        if await self.preferences.get(key) != value:
            raise RuntimeError("Browser storage did not retain the write")
        if key in COPY_KEYS:
            self.current_values[key] = value

    async def _commit(self, progress: Progress) -> None:
        snapshot = progress.export()
        Progress.from_json(snapshot)
        previous = self._last_good or snapshot
        # Preserve the last known good value before staging the new one. Main
        # remains authoritative; a partial write is detected on the next load.
        await self._write_verified(ROLLBACK_KEY, previous)
        await self._write_verified(SHADOW_KEY, snapshot)
        await self._write_verified(STORAGE_KEY, snapshot)
        self._last_good = snapshot
        self.blocked = False
        self.message = ""

    def _failed_save(self) -> None:
        self.blocked = True
        self.message = "Progress is in memory, but this browser could not save it. Automatic saving is paused. Copy a backup from Progress before closing, then restore it to retry saving."

    async def save(self, progress: Progress) -> bool:
        async with self._lock:
            if not self.loaded or self.blocked:
                return False
            try:
                for key in COPY_KEYS:
                    current = await self.preferences.get(key)
                    if current != self.current_values.get(key):
                        self.current_values[key] = current
                        self.blocked = True
                        self.message = "Browser progress changed elsewhere. Automatic saving is paused to keep both versions. Copy a backup in Progress, then restore the version you want to use."
                        return False
                await self._commit(progress)
            except Exception:
                self._failed_save()
                return False
            return True

    async def restore(self, progress: Progress) -> bool:
        """An explicit restore preserves existing raw copies before replacing them."""
        async with self._lock:
            try:
                Progress.from_json(progress.export())
                current = {key: await self.preferences.get(key) for key in COPY_KEYS}
                if any(value is not None for value in [*self.loaded_values.values(), *current.values()]):
                    archive = json.dumps({
                        "app": "first1000-stored-data", "schema": 1,
                        "original": self.loaded_values, "current": current,
                        "unreadable_keys": self.read_errors,
                    }, ensure_ascii=False, sort_keys=True)
                    digest = hashlib.sha256(archive.encode("utf-8")).hexdigest()
                    key = f"{STORAGE_KEY}.recovery.{digest}"
                    existing = await self.preferences.get(key)
                    if existing is None:
                        await self._write_verified(key, archive)
                    elif existing != archive:
                        raise RuntimeError("The existing recovery archive must be preserved")
                    self.recovery_snapshot = archive
                await self._commit(progress)
                self.loaded = True
            except Exception:
                self._failed_save()
                return False
            return True

    def recovery_export(self) -> str:
        if self.recovery_snapshot is not None:
            return self.recovery_snapshot
        return json.dumps({
            "app": "first1000-stored-data", "schema": 1,
            "original": self.loaded_values, "current": self.current_values,
            "unreadable_keys": self.read_errors,
        }, ensure_ascii=False, indent=2, sort_keys=True)
