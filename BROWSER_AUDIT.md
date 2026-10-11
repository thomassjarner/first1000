# Flet web compatibility audit

This audit applies to the existing First1000 source, pinned to **Flet 1.0.3** with **Python 3.12 / Pyodide 0.27.8** for static builds. The other application's Flet 0.86.3 target was not adopted. Curriculum content, category IDs and membership, scores, trophy fingerprints, the original storage key, and progress schema remain unchanged.

## The supplied 20 pitfalls

| # | Concern | Finding and action |
|---|---|---|
| 1 | Browser OS threads | App code has no `threading.Thread`, `time.sleep`, or `asyncio.to_thread`. Startup, storage, clipboard and practice saves use async handlers. Save serialization uses `asyncio.Lock`. |
| 2 | Flet version/API mismatch | Flet/runtime/CLI versions are pinned to 1.0.3. Containers use `ft.Border`, dropdowns use `ft.DropdownOption` and `on_select`. Deprecated TextField/Dropdown border properties were replaced with `ft.OutlineInputBorder` and `ft.BorderSide`, preserving their shapes/colors. No Tabs are used. |
| 3 | FilePicker/browser I/O | There is no FilePicker or desktop file dialog. Backup/restore uses visible JSON text and awaited Clipboard calls; a failed clipboard call now offers manual copying. |
| 4 | Custom control changes | There are no custom Flet control subclasses. `App` is an ordinary Python controller that builds standard Flet controls; it does not need `@ft.control`. |
| 5 | State/callback serialization | App state stays on the Python controller. Callbacks use supported event fields. No state objects or callback functions are added as serializable control fields. Actual MessagePack encoding is tested through mounted Flet sessions. |
| 6 | ExpansionTile API | No ExpansionTile is used; no obsolete `initially_expanded` property exists. |
| 7 | Dialog lifecycle | Dialogs use `page.show_dialog()` and `page.pop_dialog()`. Lifecycle tests model Flet's dismiss callback after closing; a closing dialog correctly remains mounted until that callback. |
| 8 | Updates before mounting | The root is added before rendering. There are no app calls to an unmounted child control's `update()`. Dialog content mounts through Flet's dialog API. No PopupMenuButton is used. |
| 9 | Reused mounted controls | Screen builders create fresh child controls on navigation. Only the root container is retained. Practice screens do not move a live control between parents. Mounted navigation and all four practice modes are checked. |
| 10 | Browser focus | Character/reading input uses a visible TextField with `autofocus`. No invisible input, keyboard listener, or unawaited `focus()` call exists. Actual browser Chinese IME behavior still needs confirmation. |
| 11 | Space/timer scrolling | There is no timer or Space shortcut. The app does not intercept Space or change browser scroll behavior. |
| 12 | Unbounded lists | Categories show 24 per page, dictionary 30 per page, results at most 40 missed entries, and history the 12 most recent sessions. Stored session history is capped at 300. |
| 13 | Nested scrolling | The main root owns page scrolling; child screen columns do not introduce nested scrolling. Dialogs have a separate bounded scrolling area. Large category/dictionary collections are paginated. |
| 14 | Desktop filesystem persistence | Runtime progress uses async SharedPreferences. Filesystem reads load bundled curriculum only from Pyodide's virtual filesystem. There are no desktop progress files, platformdirs, or OS file operations in user flows. |
| 15 | Data surviving updates | **Fixed:** the old load fallback could save defaults over unreadable data. The new store does not write on load, preserves `first1000.progress.v1` and schema 1, and verifies main/shadow/rollback copies. Unreadable or inconsistent copies pause autosaving; explicit restore archives raw copies before replacement. Observed external changes also pause saving. |
| 16 | Portable backups | Both languages and settings remain in the existing validated JSON format. Manual copy works when automatic clipboard access fails. Empty/nontext imports now produce a validation message; failed restores retain current in-memory progress. Browser clearing/private mode/device changes still require an exported backup. |
| 17 | Pinned environment | Requirements and static package target Flet 1.0.3; GitHub Actions selects Python 3.12. Use this project's own `.venv`, not another application's environment. |
| 18 | Browser dependencies | Static requirements contain only `flet==1.0.3`. Its Emscripten dependency markers exclude desktop HTTP/OAuth packages; runtime dependencies use pure Python or an available Pyodide `msgpack` wheel. Content generation libraries stay in development tools, outside the static app. |
| 19 | Tests versus real UI | Logic tests, mounted Flet protocol tests and a packaged WebAssembly execution check are separate from rendered browser QA. No visual, Chinese IME, or real browser storage/clipboard test is claimed. |
| 20 | Navigation/mount order | Root mounts first, then children render and the page updates. Fresh controls are created for each view; dialog notices are updated after their dialog mounts. Real Flet sessions test repeat navigation and dialogs at phone/desktop widths. |

## Verification and limits

- **78 tests passed**, with deprecation warnings treated as errors. Coverage includes original practice/curriculum behavior, legacy progress loading, injected read/write/readback failures, interrupted saves, corrupt and newer-schema data preservation, explicit restore archives, concurrent async saves, mounted navigation/dialog serialization, empty imports, failed restores and clipboard fallback.
- The static distribution was rebuilt and its source hashes, curriculum counts, fonts, pinned dependency, CanvasKit/Pyodide files and resolved module URL were verified. The earlier GitHub Pages module-URL/workflow repairs are retained.
- The packaged app is checked under Node-hosted Pyodide using its static Flet requirement. This exercises WebAssembly Python imports, mounted Flet session serialization, navigation/dialogs, each practice mode and storage recovery with an in-memory preferences adapter. It is not a browser renderer or a test of the browser's actual SharedPreferences service.
- A rendered browser preview is unavailable in this environment. After deployment, verify startup, Chinese IME input, dropdown filters, dark/Cantonese/HK-traditional switches, scroll behavior, one practice session, backup copy/restore, and progress after reloading in your browser.

Keep a normal progress backup before changing website origin or clearing browser site data. The recovery journal preserves damaged data rather than silently resetting it; it cannot recover browser data that has been deleted. SharedPreferences provides no cross-tab compare-and-swap transaction, so avoid running simultaneous practice sessions in several tabs.

## Official API references

- [Flet async apps](https://flet.dev/docs/cookbook/async-apps/)
- [Flet 1.0 migration](https://flet.dev/docs/updates/migrate-to-1-0/)
- [SharedPreferences](https://flet.dev/docs/services/sharedpreferences/)
- [Client storage](https://flet.dev/docs/cookbook/client-storage/)
- [BaseControl and nonserialized data](https://flet.dev/docs/controls/basecontrol/)
- [Static web publishing and Pyodide dependencies](https://flet.dev/docs/publish/web/static-website/)
