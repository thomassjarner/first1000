"""Viewport scrolling and Flet constraint checks, without claiming rendering QA."""
import asyncio

import flet as ft
import pytest

from test_flet_lifecycle import mounted_app
from test_ui import walk


@pytest.mark.parametrize("width,height",[(320,568),(390,844),(768,1024),(1024,768),(1440,900),(1920,1080)])
def test_all_screens_use_one_outer_scroller_and_content_sized_columns(width,height):
    async def scenario():
        app,session,connection,_=await mounted_app(width)
        try:
            session.page.height=height
            app.on_resize()
            assert isinstance(session.page.scroll,ft.Scrollbar)
            assert session.page.scroll.orientation==ft.ScrollbarOrientation.RIGHT
            assert not app.root.expand and app.root.scroll is None
            for screen in ('home','categories','category','dictionary','drill_setup','sentence_setup','progress'):
                app.navigate(screen);app.render()
                content=app.root.controls[0]
                assert 0<content.width<=width-32
                for control in walk(app.root):
                    if isinstance(control,ft.Column):
                        assert control.tight
                        assert control.scroll is None
                    if isinstance(control,ft.Row) and control.wrap:
                        assert not any(child.expand for child in control.controls)
                    if isinstance(control,ft.ResponsiveRow):
                        assert not any(child.expand for child in control.controls)
                if screen=='categories':
                    fields=[control for control in walk(app.root) if isinstance(control,(ft.TextField,ft.Dropdown))]
                    assert fields and all(control.height==56 for control in fields)
            assert connection.frames
        finally:session.close()
    asyncio.run(scenario())


def test_resizing_within_desktop_breakpoint_updates_width_without_resetting_state():
    async def scenario():
        app,session,_,_=await mounted_app(900)
        try:
            app.navigate('categories');app.category_query='bill';app.render()
            original=app.root.controls[0].width
            session.page.width=1100
            app.on_resize()
            assert app.root.controls[0].width>original
            assert app.category_query=='bill' and app.screen=='categories'
            app.start('drill',['core-01']);app.input_value='peng2';app.render()
            practice=app.session
            session.page.width=800;app.on_resize()
            assert app.session is practice and app.input_value=='peng2'
            assert app.root.controls[0].width==768
        finally:session.close()
    asyncio.run(scenario())


def test_dialog_fits_short_phone_viewport():
    async def scenario():
        app,session,_,_=await mounted_app(320)
        try:
            session.page.height=400
            app.show_sources()
            dialog=next(control for control in session.index.values() if isinstance(control,ft.AlertDialog))
            assert dialog.content.width<=256
            assert dialog.content.height<=220
        finally:session.close()
    asyncio.run(scenario())
