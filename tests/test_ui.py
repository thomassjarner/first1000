"""Exercise real Flet controls and handler flows without a browser runtime."""
import asyncio
import inspect
from types import SimpleNamespace

import flet as ft
import pytest

from first1000.curriculum import Curriculum
from first1000.progress import Progress, STORAGE_KEY
from first1000.ui import App


class MemoryPreferences:
    def __init__(self):self.values={}
    async def get(self,key):return self.values.get(key)
    async def set(self,key,value):self.values[key]=value;return True


class FakePage:
    def __init__(self,width):self.width=width;self.controls=[];self.dialogs=[]
    def add(self,*controls):self.controls.extend(controls)
    def update(self):pass
    def show_dialog(self,dialog):self.dialogs.append(dialog)
    def pop_dialog(self):self.dialogs.pop()


def walk(control):
    yield control
    for name in ("controls","actions"):
        for child in getattr(control,name,[]) or []:yield from walk(child)
    for name in ("content","title"):
        child=getattr(control,name,None)
        if isinstance(child,ft.Control):yield from walk(child)


def run(coro):return asyncio.run(coro)


@pytest.mark.parametrize("width",[390,1180])
@pytest.mark.parametrize("language",["mandarin","cantonese"])
@pytest.mark.parametrize("traditional",[False,True])
def test_all_screens_construct_and_sessions_complete(width,language,traditional):
    preferences=MemoryPreferences();app=App(FakePage(width),Curriculum.load(),preferences)
    run(app.initialize())
    app.progress.settings.update(language=language,traditional=traditional)
    for screen in ("home","categories","category","dictionary","drill_setup","progress"):
        app.navigate(screen);app.render()
        assert list(walk(app.root))
    app.start("core",["core-01"]);app.render()
    core_text=[x.value for x in walk(app.core()) if isinstance(x,ft.Text)]
    assert app.session.current.reading(language) not in core_text
    assert app.session.current.text(language,traditional) in core_text
    switches=[x for x in walk(app.header()) if isinstance(x,ft.Switch)]
    assert not switches[0].disabled and switches[1].disabled and switches[2].disabled
    assert all(inspect.iscoroutinefunction(x.on_change) for x in switches)
    while app.screen=="core":
        app.input_value=app.session.current.meaning;run(app.answer_core());app.render();run(app.next_core());app.render()
    assert app.result["perfect"] and app.progress.has_trophy(language,"core-01",app.curriculum)
    assert Progress.from_json(preferences.values[STORAGE_KEY]).has_trophy(language,"core-01",app.curriculum)
    app.drill_mode="choice";app.start("drill",["core-01"]);app.render()
    assert len(app.session.options())==8
    while app.screen=="drill":
        run(app.answer_drill(app.session.current.readings(language)[0]));app.render();run(app.next_drill());app.render()
    assert app.result["correct"]==app.result["total"]
    app.start("match",["core-01"]);app.render()
    for item in app.session.items:
        app.choose_match_left(item.id);run(app.choose_match_right(item.id));app.render()
    assert app.screen=="result"
    app.start("flashcards",["core-01"]);app.render()
    while app.screen=="flashcards":
        app.reveal_flashcard();app.render();run(app.rate_flashcard(True));app.render()
    assert app.result["correct"]==25
    app.show_sources();assert app.page.dialogs
    app.close_dialog();app.show_import();assert app.page.dialogs


def test_restore_and_switch_handlers():
    app=App(FakePage(1000),Curriculum.load(),MemoryPreferences());run(app.initialize())
    switches=[x for x in walk(app.header()) if isinstance(x,ft.Switch)]
    run(switches[1].on_change(SimpleNamespace(control=SimpleNamespace(value=True))))
    assert app.language=="cantonese"
    app.start("core",["core-01"])
    run(app.set_switch("language","mandarin"))
    assert app.language=="cantonese"
    run(app.set_switch("dark",True));assert app.colors["bg"]=="#121D1B"


def test_failed_storage_is_visible():
    class FailedPreferences(MemoryPreferences):
        async def set(self,key,value):return False
    app=App(FakePage(1000),Curriculum.load(),FailedPreferences());run(app.initialize())
    run(app.save());app.render()
    assert "could not save" in app.storage_error
