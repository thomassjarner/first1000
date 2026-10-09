"""Check the built site's entrypoint, packaged source, fonts, and runtime."""
from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

from fix_web_paths import has_resolved_pyodide_url

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
    rel="first1000/data/curriculum.json"
    data=tar.extractfile(names[rel]).read()
    assert data==(root/"src"/rel).read_bytes(), "Stale curriculum in build"
    payload=json.loads(data)
    assert len(payload["target_characters"])==1000
    assert len(payload["vocabulary_entry_ids"])==1231
    assert len(payload["categories"])==133
    assert tar.extractfile(names["requirements.txt"]).read().strip()==b"flet==1.0.3", "Unexpected runtime dependency"
if 'flet.noCdn=true' in html:
    runtime=dist/"pyodide"
    assert json.loads((runtime/"pyodide-lock.json").read_text())["info"]["version"]=="0.27.8"
    for name in ("pyodide.mjs","pyodide.asm.wasm","python_stdlib.zip"):
        assert (runtime/name).stat().st_size>1000, f"Incomplete Pyodide runtime: {name}"
    assert list(runtime.glob("micropip-*.whl")) and list(runtime.glob("packaging-*.whl"))
    assert list((dist/"canvaskit").glob("*.wasm")), "Missing CanvasKit"
print(f"Distribution verified: {payload['meta']['vocabulary_count']} words, 1000 characters, 133 sets; source hashes match.")
