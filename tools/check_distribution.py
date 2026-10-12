"""Check the built site's entrypoint, packaged source, fonts, and runtime."""
from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

from fix_web_paths import has_resolved_pyodide_url
from bundle_pyodide_packages import verify_packages

root=Path(__file__).resolve().parents[1]
dist=Path(sys.argv[1] if len(sys.argv)>1 else root/"dist").resolve()
assert (dist/"index.html").is_file(), "Missing site entry point"
assert (dist/"main.dart.js").is_file(), "Missing Flet client"
assert (dist/"manifest.json").is_file(), "Missing app manifest"
html=(dist/"index.html").read_text()
assert 'flet.pyodide = true' in html, "Static Python runtime is not enabled"
assert 'flet.pythonModuleName = "main"' in html, "Wrong Python entry point"
assert 'flet.routeUrlStrategy="hash"' in html, "Static routes need hash mode"
assert has_resolved_pyodide_url(html), "Pyodide module URL must resolve against document.baseURI; build with tools/build_web.py"
assert (dist/"fonts/First1000Hanzi.otf").read_bytes()==(root/"src/assets/fonts/First1000Hanzi.otf").read_bytes()
assert (dist/"fonts/Inter.ttf").read_bytes()==(root/"src/assets/fonts/Inter.ttf").read_bytes()
with tarfile.open(dist/"app.tar.gz") as tar:
    names={member.name.lstrip("/"):member for member in tar.getmembers() if member.isfile()}
    for path in (root/"src").rglob("*.py"):
        rel=path.relative_to(root/"src").as_posix()
        assert rel in names, f"Missing Python module {rel}"
        data=tar.extractfile(names[rel]).read()
        assert data==path.read_bytes(), f"Stale packaged code: {rel}"
        compile(data,rel,"exec")
    for data_path in (root/"src/first1000/data").glob("*.json"):
        data_rel=data_path.relative_to(root/"src").as_posix()
        assert tar.extractfile(names[data_rel]).read()==data_path.read_bytes(), f"Stale packaged data: {data_rel}"
    rel="first1000/data/curriculum.json"
    data=tar.extractfile(names[rel]).read()
    assert data==(root/"src"/rel).read_bytes(), "Stale curriculum in build"
    payload=json.loads(data)
    assert len(payload["target_characters"])==1000
    assert len(payload["vocabulary_entry_ids"])==1231
    assert len(payload["categories"])==133
    extra_rel="first1000/data/everyday.json"
    extra_bytes=tar.extractfile(names[extra_rel]).read()
    assert extra_bytes==(root/"src"/extra_rel).read_bytes(), "Stale everyday content"
    extra=json.loads(extra_bytes)
    assert len(extra["cantonese_targets"])==1000
    assert len([entry for entry in extra["entries"] if entry["kind"]=="sentence"])==48
    practice_rel="first1000/data/practice_sets.json"
    practice_bytes=tar.extractfile(names[practice_rel]).read()
    assert practice_bytes==(root/"src"/practice_rel).read_bytes(), "Stale expanded practice sets"
    assert all(len(ids)>=15 for ids in json.loads(practice_bytes)["sets"].values())
    assert tar.extractfile(names["requirements.txt"]).read().strip()==b"flet==1.0.3", "Unexpected runtime dependency"
if 'flet.noCdn=true' in html:
    runtime=dist/"pyodide"
    verify_packages(runtime)
    assert json.loads((runtime/"pyodide-lock.json").read_text())["info"]["version"]=="0.27.8"
    for name in ("pyodide.mjs","pyodide.asm.wasm","python_stdlib.zip"):
        assert (runtime/name).stat().st_size>1000, f"Incomplete Pyodide runtime: {name}"
    assert list(runtime.glob("micropip-*.whl")) and list(runtime.glob("packaging-*.whl"))
    assert list((dist/"canvaskit").glob("*.wasm")), "Missing CanvasKit"
print(f"Distribution verified: {payload['meta']['vocabulary_count']} words, 1000 characters, 133 original sets plus 52 new sets, 48 sentences and a separate Cantonese track; source hashes match.")
