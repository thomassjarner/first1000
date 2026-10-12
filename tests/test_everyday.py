import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import flet as ft
import pytest
from fontTools.ttLib import TTFont
from first1000.curriculum import Curriculum
from first1000.progress import Progress
from first1000.ui import App
from test_ui import FakePage, MemoryPreferences, walk
from test_flet_lifecycle import mounted_app

def make_app(language='mandarin'):
    app=App(FakePage(390),Curriculum.load(),MemoryPreferences())
    asyncio.run(app.initialize());asyncio.run(app.set_switch('language',language))
    return app

def test_legacy_trophies_and_new_character_membership():
    curr=Curriculum.load()
    fingerprints={lang:{cat.id:curr.fingerprint(cat.id,lang) for cat in curr.categories} for lang in ('mandarin','cantonese')}
    progress=Progress();progress.finish('cantonese','core',25,25,25,['core-01'],True,curr)
    curr.add_everyday_content()
    assert len([cat for cat in curr.categories if cat.kind=='situations'])==12
    assert len([e for e in curr.entries.values() if e.kind=='sentence'])==48
    assert len(set(curr.cantonese_targets))==1000
    assert set(curr.cantonese_targets)!=set(curr.target_characters)
    for lang,categories in fingerprints.items():
        for cid,value in categories.items():assert curr.fingerprint(cid,lang)==value
    assert Progress.from_json(progress.export()).has_trophy('cantonese','core-01',curr)
    assert curr.entries['cant-char:咁'].text('cantonese',True)=='咁'

def test_category_filters_sort_and_navigation():
    app=make_app();app.set_category_filter('category_kind','situations');app.set_category_filter('category_theme','Eating out')
    assert len(app.filtered_categories())==3
    app.set_category_filter('category_sort','name');matches=app.filtered_categories()
    assert [cat.title for cat in matches]==sorted(cat.title for cat in matches)
    app.open_category(matches[0].id);app.adjacent_category(1);assert app.category_id==matches[1].id
    app.reset_category_filters();app.category_query='pay by card'
    assert app.filtered_categories()[0].id=='situation-paying-the-bill'

def test_cantonese_sets_are_separate():
    app=make_app('cantonese');assert app.selected=={'cant-core-01'}
    app.set_category_filter('category_kind','characters');assert len(app.filtered_categories())==40
    assert all(cat.id.startswith('cant-core-') for cat in app.filtered_categories())
    app.start('drill',list(app.selected));assert any(char.glyph=='唔' for char in app.session.items)

@pytest.mark.parametrize('language',['mandarin','cantonese'])
def test_enter_reveals_then_advances(language):
    app=make_app(language);app.start('drill',list(app.selected));app.input_value=''
    field=next(c for c in walk(app.drill()) if isinstance(c,ft.TextField));asyncio.run(field.on_submit(SimpleNamespace(control=field)))
    assert app.session.pending is not None and not app.session.pending.correct
    assert app.session.current.meaning in app.feedback
    field=next(c for c in walk(app.drill()) if isinstance(c,ft.TextField));assert not field.disabled
    asyncio.run(field.on_submit(SimpleNamespace(control=field)))
    assert app.session.index==1 and app.session.pending is None and len(app.session.answers)==1

@pytest.mark.parametrize('language',['mandarin','cantonese'])
def test_sentence_completion_and_backup(language):
    app=make_app(language);app.start('sentence',['situation-paying-the-bill']);assert app.active
    while app.screen=='sentence':
        assert len(set(app.session.options()))==4
        assert app.session.current.meaning in app.session.options()
        asyncio.run(app.answer_sentence(app.session.current.meaning));app.render()
        asyncio.run(app.next_sentence());app.render()
    assert app.result['correct']==4
    restored=Progress.from_json(app.progress.export())
    assert restored.state(language)['sessions'][-1]['mode']=='sentence'
    assert not restored.state(language)['trophies']

def test_new_font_coverage():
    payload=json.loads((Path(__file__).parents[1]/'src/first1000/data/everyday.json').read_text())
    covered=TTFont(Path(__file__).parents[1]/'src/assets/fonts/First1000Hanzi.otf').getBestCmap()
    for entry in payload['entries']:
        for lang in ('mandarin','cantonese'):
            for script in ('simplified','traditional'):
                assert all(ord(g) in covered for g in entry[f'{lang}_{script}'])
        if entry['kind']=='sentence':assert entry['jyutping'] and entry['pinyin']

def test_mounted_new_views_and_sentence_session():
    async def scenario():
        app,session,connection,_=await mounted_app()
        try:
            for screen in ('categories','dictionary','sentence_setup'):
                app.navigate(screen);app.render()
            app.show_entry(app.curriculum.entries['sentence:paying-the-bill:1']);app.close_dialog()
            app.start('sentence',['situation-paying-the-bill']);app.render()
            while app.screen=='sentence':
                await app.answer_sentence(app.session.current.meaning);app.render()
                await app.next_sentence();app.render()
            await app.set_switch('language','cantonese');app.navigate('categories');app.render()
            app.open_category('cant-core-01');app.render();assert connection.frames
        finally:session.close()
    asyncio.run(scenario())


def test_choice_mode_enter_reveals_and_advances():
    app=make_app('cantonese');app.drill_mode='choice';app.start('drill',list(app.selected))
    asyncio.run(app.on_keyboard(SimpleNamespace(key='Enter')))
    assert app.session.pending is not None
    asyncio.run(app.on_keyboard(SimpleNamespace(key='Enter')))
    assert app.session.index == 1 and app.session.pending is None


def test_new_cantonese_progress_uses_new_targets():
    app=make_app('cantonese');app.start('drill',list(app.selected))
    glyph=app.session.current.glyph
    asyncio.run(app.answer_drill(app.session.current.readings('cantonese')[0]))
    assert app.progress.summary('cantonese',app.curriculum)['characters'] >= 1
    assert Progress.from_json(app.progress.export()).state('cantonese')['characters'][glyph]['correct'] == 1


@pytest.mark.parametrize("width", [320, 390, 768, 1180, 1920])
def test_category_filters_are_bounded_at_all_viewports(width):
    app=make_app();app.page.width=width;app.on_resize()
    view=app.categories()
    field=next(control for control in walk(view) if isinstance(control,ft.TextField))
    assert field.height==56 and not field.expand
    assert field.col=={"xs":12,"md":9}
    dropdowns=[control for control in walk(view) if isinstance(control,ft.Dropdown)]
    assert all(control.height==56 and control.width is None for control in dropdowns)
    for row in (control for control in walk(view) if isinstance(control,ft.Row)):
        if row.wrap:assert not any(control.expand for control in row.controls)
    assert view.tight
