import asyncio
import json
from types import SimpleNamespace
import pytest
import flet as ft
from first1000.progress import Progress
from first1000.curriculum import Curriculum
from test_everyday import make_app
from test_ui import walk
from test_flet_lifecycle import mounted_app


def test_legacy_backup_adds_learned_field_without_resetting_scores():
    old=Progress();old.state('mandarin').update(attempts=1,correct=1)
    incoming=json.loads(old.export())
    for state in incoming['languages'].values():state.pop('learned')
    restored=Progress.from_json(json.dumps(incoming))
    assert restored.state('mandarin')['attempts']==1
    assert restored.state('mandarin')['learned']=={}
    restored.set_learned('mandarin','character:国',True)
    assert Progress.from_json(restored.export()).is_learned('mandarin','character:国')
    assert not restored.is_learned('cantonese','character:国')
    restored.set_learned('mandarin','character:国',False)
    assert not restored.is_learned('mandarin','character:国')


def test_learned_checkbox_persists_and_counts_without_practice():
    app=make_app()
    entry=app.curriculum.entries['c:国']
    field=next(control for control in walk(app.entry_row(entry)) if isinstance(control,ft.Checkbox))
    asyncio.run(field.on_change(SimpleNamespace(control=SimpleNamespace(value=True))))
    assert app.progress.summary('mandarin',app.curriculum)['learned']==1
    assert app.progress.summary('mandarin',app.curriculum)['attempts']==0
    other=app.curriculum.entries['w:国'] if 'w:国' in app.curriculum.entries else entry
    assert app.curriculum.learned_key(other,'mandarin')==app.curriculum.learned_key(entry,'mandarin')
    stored=Progress.from_json(app.preferences.values['first1000.progress.v1'])
    assert stored.is_learned('mandarin','character:国')


def test_every_practice_set_is_at_least_fifteen_and_trophies_unchanged():
    curriculum=Curriculum.load();before={cat.id:curriculum.fingerprint(cat.id,'mandarin') for cat in curriculum.categories}
    curriculum.add_everyday_content()
    for cat in curriculum.categories:
        assert len(curriculum.practice_entries([cat.id]))>=15
    for cid,fp in before.items():assert curriculum.fingerprint(cid,'mandarin')==fp
    bill=curriculum.practice_entries(['situation-paying-the-bill'])
    assert len(bill)==15 and sum(entry.kind=='sentence' for entry in bill)==4
    assert 'w:信用卡' in {entry.id for entry in bill}


def test_pick_all_ignores_filters_and_uses_current_language():
    app=make_app('cantonese');app.category_query='bill';app.category_kind='situations'
    app.pick_all()
    assert app.selected=={cat.id for cat in app.visible_categories()}
    assert 'cant-core-40' in app.selected and 'core-01' not in app.selected
    app.start('drill',list(app.selected))
    assert len(app.session.items)==len({char.glyph for char in app.session.items})
    assert len(app.session.items)>=1000


def test_sort_twice_reverses_frequency_and_keeps_unranked_last():
    app=make_app()
    first=app.dictionary_entries()
    assert first[0].frequency<=first[10].frequency
    app.sort_dictionary('frequency')
    second=app.dictionary_entries()
    ranked=[entry for entry in second if entry.data.get('frequency')]
    assert [entry.id for entry in ranked]==list(reversed([entry.id for entry in first if entry.data.get('frequency')]))
    assert second[-1].data.get('frequency') is None
    app.sort_dictionary('frequency');assert [entry.id for entry in app.dictionary_entries()]==[entry.id for entry in first]


def test_recognition_wrong_answer_cannot_retry_and_score_uses_first_attempt():
    app=make_app();app.start('core',['core-01'])
    assert not any(isinstance(control,ft.TextField) for control in walk(app.core()))
    wrong=next(meaning for meaning in app.session.options() if meaning!=app.session.current.meaning)
    asyncio.run(app.answer_core(wrong))
    assert 'Correct meaning:' in app.feedback
    with pytest.raises(ValueError):asyncio.run(app.answer_core(app.session.current.meaning))
    asyncio.run(app.next_core())
    while app.screen=='core':
        asyncio.run(app.answer_core(app.session.current.meaning));asyncio.run(app.next_core())
    assert app.result['correct']==24 and app.result['attempts']==25
    assert not app.result['perfect']


def test_mounted_learned_controls_and_recognition_complete():
    async def scenario():
        app,session,connection,_=await mounted_app()
        try:
            app.navigate('dictionary');app.render()
            entry=app.curriculum.entries['c:国'];await app.mark_learned(entry,True);app.render()
            app.dictionary_learned='learned';app.render();assert len(app.dictionary_entries())>=1
            app.start('core',['situation-paying-the-bill']);app.render()
            while app.screen=='core':
                await app.answer_core(app.session.current.meaning);app.render()
                await app.next_core();app.render()
            assert app.result['total']==15 and app.result['perfect']
            assert Progress.from_json(app.progress.export()).is_learned('mandarin','character:国')
            assert connection.frames
        finally:session.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('invalid',[[], {'character:国':True}, {'x':'x'*65}])
def test_invalid_learned_backup_is_rejected(invalid):
    payload=json.loads(Progress().export());payload['languages']['mandarin']['learned']=invalid
    with pytest.raises(ValueError,match='learned'):Progress.from_json(json.dumps(payload))


def test_explicit_flashcard_ratings_update_learned_status():
    app=make_app();app.start('flashcards',['core-01'])
    entry=app.flash_items[0];key=app.curriculum.learned_key(entry,'mandarin')
    app.reveal_flashcard();asyncio.run(app.rate_flashcard(True))
    assert app.progress.is_learned('mandarin',key)
    assert Progress.from_json(app.progress.export()).is_learned('mandarin',key)
    app.start('flashcards',['core-01']);entry=app.flash_items[0];key=app.curriculum.learned_key(entry,'mandarin')
    app.progress.set_learned('mandarin',key,True)
    app.reveal_flashcard();asyncio.run(app.rate_flashcard(False))
    assert not app.progress.is_learned('mandarin',key)


def test_learning_all_cantonese_targets_reaches_the_full_goal():
    app=make_app('cantonese')
    for key in app.curriculum.target_learned_keys('cantonese'):
        app.progress.set_learned('cantonese',key,True)
    assert app.progress.summary('cantonese',app.curriculum)['learned']==1000
