"""Exercise the actual entry handler without a browser renderer."""
import asyncio
import importlib.util
from pathlib import Path

from first1000 import ui

spec = importlib.util.spec_from_file_location("entry", Path(__file__).parents[1] / "src/main.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)

class Page:
    def __init__(self):
        self.controls = []
        self.updated = False
    def add(self, control):
        self.controls.append(control)
    def update(self):
        self.updated = True


def test_entry_displays_complete_startup_error(monkeypatch):
    async def fail(page):
        raise RuntimeError("diagnostic test error")
    monkeypatch.setattr(ui, "main", fail)
    page = Page()
    asyncio.run(entry.main(page))
    error = page.controls[0].controls[-1]
    assert "RuntimeError: diagnostic test error" in error.value
    assert "Traceback" in error.value
    assert error.selectable


def test_success_removes_loading_indicator(monkeypatch):
    async def start(page):
        page.add("app")
    monkeypatch.setattr(ui, "main", start)
    page = Page()
    asyncio.run(entry.main(page))
    assert page.controls == ["app"]
    assert page.updated


def test_resize_does_not_render_during_initialization():
    app = object.__new__(ui.App)
    app.ready = False
    app.render = lambda: (_ for _ in ()).throw(AssertionError("premature render"))
    app.on_resize()
