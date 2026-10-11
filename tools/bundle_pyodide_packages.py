"""Include and verify Pyodide's Flet dependencies in a no-CDN build."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

RUNTIME_PACKAGES = ("micropip", "packaging", "msgpack", "six")


def runtime_packages(lock):
    packages = lock["packages"]
    resolved = {}
    def visit(name):
        if name in resolved:
            return
        package = packages[name]
        filename = package["file_name"]
        if Path(filename).name != filename or not filename.endswith(".whl"):
            raise ValueError(f"Invalid runtime wheel filename: {filename}")
        resolved[name] = package
        for dependency in package.get("depends", []):
            visit(dependency)
    for name in RUNTIME_PACKAGES:
        visit(name)
    return resolved


def verify_packages(runtime):
    lock = json.loads((runtime / "pyodide-lock.json").read_text())
    for name, package in runtime_packages(lock).items():
        path = runtime / package["file_name"]
        if not path.is_file():
            raise ValueError(f"Missing Pyodide dependency {name}: {path.name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != package["sha256"]:
            raise ValueError(f"Invalid Pyodide dependency checksum: {path.name}")


def bundle_packages(runtime, fetch=None):
    lock = json.loads((runtime / "pyodide-lock.json").read_text())
    version = lock["info"]["version"]
    if version != "0.27.8":
        raise ValueError(f"Unexpected Pyodide version: {version}")
    def download(url):
        with urlopen(url, timeout=120) as response:
            return response.read()
    fetch = fetch or download
    for name, package in runtime_packages(lock).items():
        path = runtime / package["file_name"]
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == package["sha256"]:
            continue
        url = f"https://cdn.jsdelivr.net/pyodide/v{version}/full/{path.name}"
        data = fetch(url)
        if hashlib.sha256(data).hexdigest() != package["sha256"]:
            raise ValueError(f"Downloaded Pyodide dependency checksum mismatch: {name}")
        path.write_bytes(data)
        print(f"Bundled Pyodide dependency: {name}")
    verify_packages(runtime)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    bundle_packages(parser.parse_args().dist / "pyodide")
