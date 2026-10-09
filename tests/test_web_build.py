"""Regression checks for the Pyodide module URL that prevented web startup."""
import json
import re
from urllib.parse import urljoin

import pytest

from tools.fix_web_paths import fix_distribution, has_resolved_pyodide_url, resolve_pyodide_url


@pytest.mark.parametrize("base_url, expected", [
    ("https://example.com/", "https://example.com/pyodide/pyodide.mjs"),
    ("https://example.com/first1000/", "https://example.com/first1000/pyodide/pyodide.mjs"),
])
def test_runtime_url_uses_the_html_base(base_url, expected):
    html = '<script>flet.pyodideUrl="pyodide/pyodide.mjs";</script>'
    fixed = resolve_pyodide_url(html)
    assert has_resolved_pyodide_url(fixed)
    url_literal = re.search(r"new URL\((.*?), document.baseURI\)", fixed)[1]
    assert urljoin(base_url, json.loads(url_literal)) == expected


@pytest.mark.parametrize("url", [
    '"pyodide/pyodide.mjs"',
    "'pyodide/pyodide.mjs'",
    '"https://cdn.jsdelivr.net/pyodide/v0.27.8/full/pyodide.mjs"',
])
def test_preserves_generated_url_and_surrounding_content(url):
    html = f"before\nflet.pyodideUrl = {url};\nafter"
    assert resolve_pyodide_url(html) == f"before\nflet.pyodideUrl = new URL({url}, document.baseURI).href;\nafter"


def test_fix_is_idempotent_and_writes_index(tmp_path):
    index = tmp_path / "index.html"
    index.write_text('汉字\nflet.pyodideUrl="pyodide/pyodide.mjs";', encoding="utf-8")
    fix_distribution(tmp_path)
    first = index.read_bytes()
    fix_distribution(tmp_path)
    assert index.read_bytes() == first
    assert "汉字" in index.read_text(encoding="utf-8")
    assert has_resolved_pyodide_url(index.read_text(encoding="utf-8"))


@pytest.mark.parametrize("html", [
    "<html></html>",
    'flet.pyodideUrl="a.mjs"; flet.pyodideUrl="b.mjs";',
    'flet.pyodideUrl=unknownVariable;',
    'flet.pyodideUrl="a.mjs"; flet.pyodideUrl = new URL("b.mjs", document.baseURI).href;',
])
def test_unexpected_generated_configuration_fails_clearly(html):
    assert not has_resolved_pyodide_url(html)
    with pytest.raises(ValueError, match="exactly one"):
        resolve_pyodide_url(html)
