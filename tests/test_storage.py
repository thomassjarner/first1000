"""Fault-injection checks for browser saves, recovery, and legacy progress."""
import asyncio
import json

import pytest

from first1000.progress import Progress, STORAGE_KEY
from first1000.storage import COPY_KEYS, ROLLBACK_KEY, SHADOW_KEY, ProgressStore


class Preferences:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.writes = []
        self.fail_read = set()
        self.fail_write = set()
        self.drop_write = set()

    async def get(self, key):
        if key in self.fail_read:
            raise RuntimeError("read unavailable")
        return self.values.get(key)

    async def set(self, key, value):
        self.writes.append((key, value))
        if key in self.fail_write:
            return False
        if key not in self.drop_write:
            self.values[key] = value
        return True


def run(coro):
    return asyncio.run(coro)


def scored(attempts=3):
    progress = Progress()
    progress.state("mandarin").update(attempts=attempts,correct=attempts)
    progress.settings.update(language="cantonese", traditional=True, dark=True)
    return progress


def test_existing_v1_key_and_schema_load_unchanged_without_initial_writes():
    original = scored().export()
    preferences = Preferences({STORAGE_KEY: original})
    store = ProgressStore(preferences)
    progress = run(store.load())
    assert progress.export() == original
    assert not store.blocked and not preferences.writes
    assert STORAGE_KEY == "first1000.progress.v1" and progress.data["schema"] == 1


@pytest.mark.parametrize("bad", ["", "not json", None, 7, False, '{"app":"first1000","schema":2}'])
def test_unreadable_progress_is_never_overwritten_by_autosave(bad):
    if bad is None:
        bad = '{"app":"first1000","schema":1,"settings":null}'
    preferences = Preferences({STORAGE_KEY: bad})
    store = ProgressStore(preferences)
    progress = run(store.load())
    progress.record_answer("mandarin", True)
    assert not run(store.save(progress))
    assert preferences.values[STORAGE_KEY] == bad and not preferences.writes
    assert store.blocked and "paused" in store.message


def test_read_failure_blocks_saving_even_when_a_valid_backup_is_available():
    original = scored().export()
    preferences = Preferences({SHADOW_KEY: original})
    preferences.fail_read.add(STORAGE_KEY)
    store = ProgressStore(preferences)
    progress = run(store.load())
    assert progress.export() == original and store.blocked
    assert not run(store.save(progress)) and not preferences.writes


@pytest.mark.parametrize("backup_key", [SHADOW_KEY, ROLLBACK_KEY])
def test_valid_backup_is_recovered_without_replacing_broken_main(backup_key):
    original = scored().export()
    preferences = Preferences({STORAGE_KEY: "broken main", backup_key: original})
    store = ProgressStore(preferences)
    assert run(store.load()).export() == original
    assert store.blocked and not preferences.writes
    assert preferences.values[STORAGE_KEY] == "broken main"


def test_interrupted_save_keeps_main_authoritative_and_preserves_shadow_for_review():
    old, pending = scored(2).export(), scored(4).export()
    preferences = Preferences({STORAGE_KEY: old, SHADOW_KEY: pending})
    store = ProgressStore(preferences)
    assert run(store.load()).export() == old
    assert store.blocked and not preferences.writes
    assert json.loads(store.recovery_export())["original"][SHADOW_KEY] == pending


def test_successful_saves_keep_new_main_shadow_and_previous_rollback():
    original = scored(2).export()
    preferences = Preferences({STORAGE_KEY: original})
    store = ProgressStore(preferences)
    progress = run(store.load())
    progress.record_answer("cantonese", False)
    assert run(store.save(progress))
    assert preferences.values[STORAGE_KEY] == preferences.values[SHADOW_KEY] == progress.export()
    assert preferences.values[ROLLBACK_KEY] == original
    assert not store.blocked


@pytest.mark.parametrize("failed_key", list(COPY_KEYS))
def test_failed_write_preserves_last_good_data_and_pauses_future_saves(failed_key):
    original = scored(2).export()
    preferences = Preferences({STORAGE_KEY: original})
    store = ProgressStore(preferences)
    progress = run(store.load())
    progress.record_answer("mandarin", False)
    preferences.fail_write.add(failed_key)
    assert not run(store.save(progress))
    assert preferences.values[STORAGE_KEY] == original
    assert original in preferences.values.values()
    previous_writes = list(preferences.writes)
    assert not run(store.save(progress))
    assert preferences.writes == previous_writes


def test_readback_detects_a_write_that_claims_success_but_was_not_retained():
    original = scored().export()
    preferences = Preferences({STORAGE_KEY: original})
    preferences.drop_write.add(SHADOW_KEY)
    store = ProgressStore(preferences)
    progress = run(store.load())
    progress.record_answer("mandarin", False)
    assert not run(store.save(progress)) and store.blocked
    assert preferences.values[STORAGE_KEY] == original


def test_external_storage_change_is_preserved_instead_of_overwritten():
    preferences = Preferences({STORAGE_KEY: scored().export()})
    store = ProgressStore(preferences)
    progress = run(store.load())
    preferences.values[STORAGE_KEY] = "a changed or newer stored format"
    assert not run(store.save(progress))
    assert not preferences.writes
    assert preferences.values[STORAGE_KEY] == "a changed or newer stored format"


def test_explicit_restore_archives_original_data_and_resumes_safe_saving():
    original = {STORAGE_KEY: "broken main", SHADOW_KEY: "", ROLLBACK_KEY: 12}
    preferences = Preferences(original)
    store = ProgressStore(preferences)
    run(store.load())
    restored = scored(7)
    assert run(store.restore(restored))
    assert all(Progress.from_json(preferences.values[key]) for key in COPY_KEYS)
    archives = [value for key, value in preferences.values.items() if key.startswith(STORAGE_KEY + ".recovery.")]
    assert len(archives) == 1
    assert json.loads(archives[0])["original"] == original
    assert not store.blocked and not store.message
    restored.record_answer("cantonese", True)
    assert run(store.save(restored))
    assert archives[0] in preferences.values.values()


def test_failed_archive_prevents_restore_from_replacing_existing_progress():
    class RejectArchives(Preferences):
        async def set(self, key, value):
            if ".recovery." in key:
                return False
            return await super().set(key, value)
    original = "unreadable progress that must be kept"
    preferences = RejectArchives({STORAGE_KEY: original})
    store = ProgressStore(preferences)
    run(store.load())
    assert not run(store.restore(scored()))
    assert preferences.values[STORAGE_KEY] == original


def test_concurrent_saves_do_not_interleave_the_three_copy_writes():
    async def scenario():
        class SlowPreferences(Preferences):
            async def set(self, key, value):
                await asyncio.sleep(0)
                return await super().set(key, value)
        preferences = SlowPreferences()
        store = ProgressStore(preferences)
        await store.load()
        first, second = scored(1), scored(2)
        assert await asyncio.gather(store.save(first), store.save(second)) == [True, True]
        assert preferences.values[STORAGE_KEY] == preferences.values[SHADOW_KEY] == second.export()
        assert preferences.values[ROLLBACK_KEY] == first.export()
        assert len(preferences.writes) == 6
    run(scenario())
