import asyncio
import json
import pytest
from first1000.character_framework import snapshot, restore, validate_snapshot
from first1000.progress import Progress
from first1000.ui import App
from first1000.curriculum import Curriculum
from test_everyday import make_app
from test_ui import FakePage, walk
import flet as ft


def test_separated_groups_and_word_selection():
    app=make_app(); selected=set(app.selected)
    groups=app.available_character_groups()
    assert len(groups)==14 and len(groups['common-1000'].glyphs)==1000
    assert all(groups[f'hsk-{n}'].glyphs for n in range(1,5))
    assert not any(cat.kind in ('characters','cantonese_characters') for cat in app.visible_categories())
    app.select_full_track();assert app.selected==selected


def test_saved_pending_answer_resumes_exact_order_then_next_and_restart():
    app=make_app();asyncio.run(app.begin_character_group('common-100'))
    order=[char.glyph for char in app.session.items];char=app.session.current
    asyncio.run(app.answer_drill(char.readings(app.language)[0]))
    assert app.progress.is_character_learned(app.language,char.glyph)
    assert not app.progress.state(app.language)['word_learning']
    reloaded=App(FakePage(390),Curriculum.load(),app.preferences)
    asyncio.run(reloaded.initialize());asyncio.run(reloaded.begin_character_group('common-100',True))
    assert [char.glyph for char in reloaded.session.items]==order
    assert reloaded.session.pending.correct and reloaded.session.index==0
    asyncio.run(reloaded.next_drill())
    saved=Progress.from_json(reloaded.progress.export()).state('mandarin')['character_sessions']['common-100::simplified']
    assert saved['index']==1 and not saved['pending']
    asyncio.run(reloaded.begin_character_group('hsk-1'))
    assert reloaded.saved_character_session('common-100')['index']==1
    asyncio.run(reloaded.begin_character_group('common-100'))
    assert reloaded.session.index==0 and reloaded.session.pending is None
    assert reloaded.progress.is_character_learned('mandarin',order[0])
    assert not reloaded.progress.is_character_learned('cantonese',order[0])


def test_choice_does_not_learn_and_retains_options():
    app=make_app();app.drill_mode='choice';asyncio.run(app.begin_character_group('common-100'))
    options=app.session.options();char=app.session.current
    asyncio.run(app.answer_drill(char.readings(app.language)[0]))
    assert not app.progress.is_character_learned(app.language,char.glyph)
    value=app.saved_character_session('common-100')
    recovered=restore(value,app.curriculum,app.language)
    assert recovered.options()==options and recovered.pending.correct


def test_invalid_saved_position_rejected_and_legacy_marks_preserved():
    app=make_app();asyncio.run(app.begin_character_group('common-100'))
    payload=json.loads(app.progress.export());state=payload['languages']['mandarin']
    state['character_sessions']['common-100::simplified']['index']=999
    with pytest.raises(ValueError):Progress.from_json(json.dumps(payload))
    old=Progress();old.set_learned('mandarin','character:国',True)
    old.migrate_frameworks(app.curriculum)
    assert old.is_learned('mandarin','character:国')
    assert not old.is_character_learned('mandarin','国')


def test_completion_checkpoint_and_readonly_result():
    app=make_app();asyncio.run(app.begin_character_group('common-100'))
    while app.screen=='drill':
        asyncio.run(app.answer_drill(app.session.current.readings('mandarin')[0]));asyncio.run(app.next_drill())
    value=app.saved_character_session('common-100');validate_snapshot(value)
    assert value['completed'] and value['index']==100 and 'outcomes' not in value
    assert len(app.progress.state('mandarin')['character_learning'])==100
    assert not any(isinstance(c,ft.Checkbox) for c in walk(app.character_result_review()))
    app.progress_view()
