import asyncio
import json
import random
from types import SimpleNamespace
import flet as ft
import pytest
from first1000.practice import reading_status,DrillSession
from first1000.progress import Progress
from test_everyday import make_app
from test_ui import walk
from test_flet_lifecycle import mounted_app

@pytest.mark.parametrize('given,accepted,language,status',[
('péng',('peng2',),'mandarin','correct'),('peng3',('peng2',),'mandarin','almost'),
('peng',('peng2',),'mandarin','almost'),('pang2',('peng2',),'mandarin','incorrect'),
('lü4',('lv4',),'mandarin','correct'),('lv2',('lv4',),'mandarin','almost'),
('lu4',('lv4',),'mandarin','incorrect'),('hang2',('xing2','hang2'),'mandarin','correct'),
('hang3',('xing2','hang2'),'mandarin','almost'),('pang4',('pang4',),'cantonese','correct'),
('pang2',('pang4',),'cantonese','almost'),('peng4',('pang4',),'cantonese','incorrect'),
('—',('peng2',),'mandarin','incorrect')])
def test_tone_classification(given,accepted,language,status):
    assert reading_status(given,accepted,language)==status


def test_latest_outcome_filters_and_reload_are_separate_from_learned():
    app=make_app();app.select_full_track()
    char=app.curriculum.characters['朋'];app.session=DrillSession([char],'mandarin',list(app.curriculum.characters.values()))
    app.screen='drill';asyncio.run(app.answer_drill('peng3'))
    key=app.curriculum.drill_key('朋')
    assert app.progress.drill_status('mandarin',key)=='almost'
    assert not app.progress.is_learned('mandarin',app.curriculum.character_key('朋'))
    restored=Progress.from_json(app.progress.export());assert restored.drill_status('mandarin',key)=='almost'
    assert restored.drill_status('cantonese',key)=='unseen'
    app.set_drill_filter('almost');assert '朋' in [char.glyph for char in app.drill_candidates()]
    assert len(app.drill_candidates())==1
    app.session=DrillSession([char],'mandarin',list(app.curriculum.characters.values()))
    asyncio.run(app.answer_drill('peng2'))
    assert app.progress.drill_status('mandarin',key)=='correct'
    assert not app.drill_candidates()
    app.set_drill_filter('correct');assert [char.glyph for char in app.drill_candidates()]==['朋']


def test_post_quiz_review_requires_explicit_selection_and_no_new_saved_accuracy():
    app=make_app();app.start('core',['core-01'])
    while app.screen=='core':
        asyncio.run(app.answer_core(app.session.current.meaning));asyncio.run(app.next_core())
    assert app.result['correct']==25
    assert app.progress.summary('mandarin',app.curriculum)['learned']==0
    assert app.result['review_glyphs']
    glyph=app.result['review_glyphs'][0]
    # A later header language switch must not change the completed quiz's language.
    app.progress.settings['language']='cantonese'
    asyncio.run(app.mark_review_character(glyph,True))
    assert app.progress.is_learned('mandarin',app.curriculum.character_key(glyph))
    assert not app.progress.is_learned('cantonese',app.curriculum.character_key(glyph))
    saved=json.loads(app.progress.export())
    session=saved['languages']['mandarin']['sessions'][-1]
    assert 'correct' not in session and 'attempts' not in session and session['score_saved'] is False
    assert saved['languages']['mandarin']['attempts']==saved['languages']['mandarin']['correct']==0
    assert Progress.from_json(app.progress.export()).state('mandarin')['sessions'][-1]['total']==25


def test_whole_mandarin_track_completes_and_review_is_paginated():
    app=make_app();app.select_full_track();chars=app.drill_candidates();assert len(chars)==1000
    app.start('drill',list(app.selected))
    session=app.session
    while not session.finished:
        assert session.answer(session.current.readings('mandarin')[0]).status=='correct'
        session.advance()
    app.complete('drill',1000,1000,1000,False,[],session.answers)
    assert len(app.result['review_glyphs'])==1000
    view=app.character_review()
    assert len([control for control in walk(view) if isinstance(control,ft.Checkbox)])==24
    assert app.progress.summary('mandarin',app.curriculum)['learned']==0
    asyncio.run(app.learn_review_page())
    assert app.progress.summary('mandarin',app.curriculum)['learned']==24


def test_legacy_results_preserved_and_migrated_without_inventing_tone_errors():
    app=make_app();p=Progress();p.state('mandarin')['characters']={'朋':{'attempts':3,'correct':3,'target_ids':['朋']},'国':{'attempts':2,'correct':1,'target_ids':['国']}}
    p.state('mandarin').update(attempts=5,correct=4)
    p.migrate_drill_outcomes(app.curriculum)
    assert p.drill_status('mandarin','glyph:朋')=='correct'
    assert p.drill_status('mandarin','glyph:国')=='incorrect'
    p.record_answer('mandarin',True,app.curriculum.characters['国'],status='almost',status_key='glyph:国')
    p.migrate_drill_outcomes(app.curriculum)
    assert p.drill_status('mandarin','glyph:国')=='almost'
    assert p.state('mandarin')['attempts']==5 and p.state('mandarin')['correct']==4


def test_mounted_drill_colours_examples_review_and_progress():
    async def scenario():
        app,session,_,_=await mounted_app()
        try:
            app.select_full_track();app.navigate('drill_setup');app.render()
            app.session=DrillSession([app.curriculum.characters['朋']],'mandarin',list(app.curriculum.characters.values()));app.screen='drill';app.render()
            example=app.example_text('朋');assert example.value and example.size==13
            await app.answer_drill('peng3');app.render()
            assert any(control.color==app.colors['amber'] and control.value=='朋' for control in session.index.values() if isinstance(control,ft.Text))
            await app.next_drill();app.render()
            await app.mark_review_character('朋',True);app.render()
            app.navigate('progress');app.render()
            text=[control.value or '' for control in walk(app.root) if isinstance(control,ft.Text)]
            assert not any('practised' in value or '%' in value for value in text)
        finally:session.close()
    asyncio.run(scenario())

@pytest.mark.parametrize('bad',[True, {'glyph:朋':{'status':'almost','updated_at':False}}, {'glyph:朋':{'status':'bogus','updated_at':'today'}}])
def test_invalid_outcome_backups_rejected(bad):
    payload=json.loads(Progress().export());payload['languages']['mandarin']['drill_outcomes']=bad
    with pytest.raises(ValueError,match='outcomes'):Progress.from_json(json.dumps(payload))
