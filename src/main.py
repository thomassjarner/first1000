"""Browser entry point with visible startup diagnostics and lazy app imports."""
import traceback

import flet as ft


async def main(page: ft.Page):
    page.title = "First 1000"
    status = ft.Text("Starting First 1000…")
    page.add(status)
    try:
        # Import inside the handler so import/data errors can be shown on the page.
        from first1000.ui import main as start_app
        await start_app(page)
    except Exception:
        details = traceback.format_exc()
        print(details, flush=True)
        page.controls.clear()
        page.add(ft.Column([
            ft.Text("First 1000 could not start", size=24),
            ft.Text("Copy the error below and send it with your bug report. Your saved progress has not been reset."),
            ft.Text(details, selectable=True, font_family="monospace"),
        ], scroll=ft.ScrollMode.AUTO, expand=True))
    else:
        page.controls.remove(status)
        page.update()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
