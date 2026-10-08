"""Build from this checkout, then verify every packaged Python source file."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url",default="/")
args=parser.parse_args()
os.environ.setdefault("FLET_CACHE_DIR", str(root/"tools/cache"))
for path in (root/"src").rglob("__pycache__"):
    shutil.rmtree(path)
command=[sys.executable,"-m","flet.cli","publish",".","--python-version","3.12","--distpath","dist","--no-cdn","--route-url-strategy","hash","--base-url",args.base_url]
# The CLI module entry point is provided by flet-cli's installed executable.
flet=Path(sys.executable).parent/("flet.exe" if sys.platform=="win32" else "flet")
command=[str(flet),*command[3:]]
subprocess.run(command,cwd=root,check=True)
subprocess.run([sys.executable,str(root/"tools/check_distribution.py"),str(root/"dist")],cwd=root,check=True)
