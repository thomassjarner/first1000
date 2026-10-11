"""Check mounting and wire serialization with Flet's real session protocol.

This exercises Python/Flet lifecycle behavior, not the Flutter browser renderer.
"""
import asyncio
from types import SimpleNamespace

import flet as ft
import msgpack
import pytest
from flet.controls.base_control import BaseControl
from flet.messaging.connection import Connection
from flet.messaging.protocol import configure_encode_object_for_msgpack
from flet.messaging.session import Session
from flet.pubsub.pubsub_hub import PubSubHub

from first1000.curriculum import Curriculum
from first1000.progress import Progress, STORAGE_KEY
from first1000.ui import App


class MemoryPreferences:
    def __init__(self):
        self.values = {}
        self.fail_writes = False

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value):
        if self.fail_writes:
            return False
        self.values[key] = value
        return True


class RecordingConnection(Connection):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.get_running_loop()
        self.pubsubhub = PubSubHub(self.loop)
        self.frames = []
        self.encoder = configure_encode_object_for_msgpack(BaseControl)

    def send_message(self, message):
        # The real encoder rejects accidentally serialized state or callables.
        self.frames.append(msgpack.packb(
            [message.action, message.body], default=self.encoder,
        ))


async def mounted_app(width=390):
    connection = RecordingConnection()
    session = Session(connection)
    session.attach_connection(connection)
    session.page.width = width
    # Reproduce register-client mounting before the application's entry point.
    msgpack.packb(session.get_page_patch(), default=connection.encoder)
    preferences = MemoryPreferences()
    app = App(session.page, Curriculum.load(), preferences)
    await app.initialize()
    return app, session, connection, preferences


def controls_in(session, cls):
    return [control for control in session.index.values() if isinstance(control, cls)]


async def click(session, label):
    button = next(control for control in controls_in(session, ft.Button)
                  if control.content == label)
    await button.on_click(SimpleNamespace(control=button))


async def dismiss_closed_dialog(session):
    # Flutter sends this after its close animation; pop_dialog intentionally
    # leaves the closed control mounted until then.
    dialog = next(dialog for dialog in controls_in(session, ft.AlertDialog)
                  if not dialog.open)
    await dialog.on_dismiss(SimpleNamespace(control=dialog, data=None))
    assert not controls_in(session, ft.AlertDialog)


@pytest.mark.parametrize("width", [390, 1180])
def test_mounted_navigation_practice_and_dialogs_serialize(width):
    async def scenario():
        app, session, connection, _ = await mounted_app(width)
        try:
            for label, screen in [
                ("Categories", "categories"), ("Dictionary", "dictionary"),
                ("Character driller", "drill_setup"), ("Progress", "progress"),
                ("Home", "home"),
            ]:
                await click(session, label)
                assert app.screen == screen
                assert app.root.page is session.page
                # Every indexed visual control has a live path to this page.
                assert all(control.page is session.page
                           for control in controls_in(session, ft.Control))
            for show in (app.show_sources, app.show_import, app.show_export):
                show()
                assert controls_in(session, ft.AlertDialog)
                app.close_dialog()
                await dismiss_closed_dialog(session)
            app.progress.settings.update(language="cantonese", traditional=True)
            for mode in ("core", "drill", "match", "flashcards"):
                app.start(mode, ["core-01"])
                app.render()
                if mode == "core":
                    app.input_value = app.session.current.text("cantonese", True)
                    await app.answer_core()
                elif mode == "drill":
                    await app.answer_drill(app.session.current.readings("cantonese")[0])
                    app.render()
                    await app.next_drill()
                elif mode == "match":
                    entry = app.session.items[0]
                    app.choose_match_left(entry.id)
                    await app.choose_match_right(entry.id)
                else:
                    app.reveal_flashcard()
                    app.render()
                    await app.rate_flashcard(True)
                app.render()
                await click(session, "Home")
            assert len(connection.frames) > 20
            for frame in connection.frames:
                msgpack.unpackb(frame, strict_map_key=False)
        finally:
            session.close()
            await asyncio.sleep(0)
    asyncio.run(scenario())


def test_empty_and_failed_restore_keep_current_progress_and_dialog():
    async def scenario():
        app, session, _, preferences = await mounted_app()
        try:
            app.progress.settings["language"] = "cantonese"
            current = app.progress
            app.show_import()
            await click(session, "Restore this backup")
            assert app.progress is current
            assert controls_in(session, ft.AlertDialog)
            assert any("valid First 1000 JSON backup" in (text.value or "")
                       for text in controls_in(session, ft.Text))
            field = next(field for field in controls_in(session, ft.TextField)
                         if field.label == "Paste a First 1000 JSON backup")
            field.value = Progress().export()
            preferences.fail_writes = True
            await click(session, "Restore this backup")
            assert app.progress is current
            assert controls_in(session, ft.AlertDialog)
            assert STORAGE_KEY not in preferences.values
            assert any("Your current progress is unchanged" in (text.value or "")
                       for text in controls_in(session, ft.Text))
            preferences.fail_writes = False
            await click(session, "Restore this backup")
            assert app.progress is not current
            await dismiss_closed_dialog(session)
            assert Progress.from_json(preferences.values[STORAGE_KEY]).settings["language"] == "mandarin"
        finally:
            session.close()
            await asyncio.sleep(0)
    asyncio.run(scenario())


def test_clipboard_failure_leaves_a_readable_manual_backup():
    class FailedClipboard:
        async def set(self, text):
            raise RuntimeError("Clipboard permission denied")

    async def scenario():
        app, session, _, _ = await mounted_app()
        try:
            app.clipboard = FailedClipboard()
            app.show_export()
            await click(session, "Copy JSON")
            assert controls_in(session, ft.AlertDialog)
            assert any("copy it manually" in (text.value or "")
                       for text in controls_in(session, ft.Text))
            field = next(field for field in controls_in(session, ft.TextField)
                         if field.read_only)
            assert Progress.from_json(field.value).data == app.progress.data
        finally:
            session.close()
            await asyncio.sleep(0)
    asyncio.run(scenario())
