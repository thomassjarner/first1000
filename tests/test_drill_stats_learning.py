import asyncio
import flet as ft
import pytest
from first1000.curriculum import Curriculum
from first1000.progress import Progress,STORAGE_KEY
from first1000.ui import App
from test_everyday import make_app
from test_ui import FakePage,walk
from test_flet_lifecycle import mounted_app

@pytest.mark.parametrize('language',['mandarin','cantonese'])
@pytest.mark.parametrize('status',['correct','almost','incorrect','unseen'])
def test_each_stats_filter_has_pronunciation_and_saved_learned_control(language,status):
    app=make_app(language);char=app.drill_candidates(filtered=False)[0]
    if status!='unseen':
        app.progress.record_answer(language,status=='correct',char,status=status,status_key=app.curriculum.drill_key(char.glyph))
    app.set_drill_filter(status)
    view=app.character_group_view()
    rows=[control for control in walk(view) if isinstance(control,ft.Text)]
    label='Pinyin' if language=='mandarin' else 'Jyutping'
    assert any(control.value==label+': '+' / '.join(char.readings(language)) for control in rows)
    assert not any(isinstance(control,ft.Checkbox) for control in walk(view))



def test_reload_preserves_progress_outcomes_and_trophies_with_same_storage_key():
    app=make_app();char=app.drill_candidates(filtered=False)[0]
    app.progress.record_answer('mandarin',False,char,status='almost',status_key=app.curriculum.drill_key(char.glyph))
    app.progress.finish('mandarin','core',25,25,25,['core-01'],True,app.curriculum)
    asyncio.run(app.set_character_learned(char.glyph,True))
    before=app.progress.export()
    reloaded=App(FakePage(390),Curriculum.load(),app.preferences)
    asyncio.run(reloaded.initialize())
    assert reloaded.progress.export()==before
    assert reloaded.progress.drill_status('mandarin',reloaded.curriculum.drill_key(char.glyph))=='almost'
    assert reloaded.progress.has_trophy('mandarin','core-01',reloaded.curriculum)
    assert reloaded.progress.summary('mandarin',reloaded.curriculum)['learned']==1
    assert not reloaded.progress.is_character_learned('mandarin',char.glyph)
    asyncio.run(reloaded.set_character_learned(char.glyph,False))
    assert not reloaded.learned_character_entries()


def test_mounted_stats_checkboxes_and_progress_list_serialize():
    async def scenario():
        app,session,connection,_=await mounted_app(320)
        try:
            app.navigate('drill_setup');app.render()
            char=app.drill_candidates(filtered=False)[0]
            app.progress.learn_typed_character(app.language,char.glyph)
            await app.save()
            app.navigate('progress');app.render()
            assert app.learned_character_entries()
            assert any(control.value=='Characters learned by typing' for control in session.index.values() if isinstance(control,ft.Text))
            assert connection.frames
        finally:session.close()
    asyncio.run(scenario())
