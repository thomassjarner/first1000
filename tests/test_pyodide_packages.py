import hashlib
import json

import pytest

from tools.bundle_pyodide_packages import bundle_packages, verify_packages


def fixture_lock(tmp_path):
    packages = {}
    for name in ('micropip', 'packaging', 'msgpack', 'six', 'dependency'):
        packages[name] = dict(file_name=f'{name}-test.whl', sha256=hashlib.sha256(name.encode()).hexdigest(), depends=['dependency'] if name == 'msgpack' else [])
    (tmp_path / 'pyodide-lock.json').write_text(json.dumps(dict(info=dict(version='0.27.8'), packages=packages)))


def test_bundles_transitive_packages_and_reuses_verified_files(tmp_path):
    fixture_lock(tmp_path)
    urls = []
    def fetch(url):
        urls.append(url)
        return url.rsplit('/', 1)[-1].split('-')[0].encode()
    bundle_packages(tmp_path, fetch)
    assert len(urls) == 5
    assert all('/v0.27.8/full/' in url for url in urls)
    verify_packages(tmp_path)
    bundle_packages(tmp_path, lambda _: pytest.fail('unnecessary download'))
    (tmp_path / 'msgpack-test.whl').unlink()
    with pytest.raises(ValueError, match='Missing Pyodide dependency msgpack'):
        verify_packages(tmp_path)


def test_rejects_corrupt_download_before_writing(tmp_path):
    fixture_lock(tmp_path)
    with pytest.raises(ValueError, match='checksum mismatch'):
        bundle_packages(tmp_path, lambda _: b'wrong')
    assert not list(tmp_path.glob('*.whl'))
