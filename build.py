#!/usr/bin/python3.9

from os import system
import os
from pathlib import Path
import subprocess
import sys
import shutil
import glob
import requests

from include import gencstd

with open("version") as fp:
    VERSION = fp.read().split("VERSION=")[1]

if sys.platform == "win32":
    ARCHIVE = f"princess-win32-{VERSION}.zip"
else:
    ARCHIVE = f"princess-{VERSION}.tar.gz"

SOURCE_URL = f"https://github.com/Princess-org/Princess/releases/download/v{VERSION}-alpha/{ARCHIVE}"

WIN_ARGS = ["-llibffi", "--link-flag", "/FORCE:UNRESOLVED", "--link-flag", "/STACK:67108864", "--clang=-gcodeview"]
if sys.platform == "win32":
    WIN_ARGS += ["--link-directory", os.environ["LIBRARY_PATH"]]

def exe_file(file: str) -> str:
    if sys.platform == "win32":
        return file + ".exe"
    return file

def release():
    FOLDER=Path(f"princess-{VERSION}")
    
    print("First compilation step")
    build([])

    print("Second compilation step")
    subprocess.check_call([exe_file("bin/princess2"), "-d", "-Isrc", "--buildfolder=build", "--outfile", exe_file("bin/princess3"), "src/main.pr"])
    
    print("Creating archive")
    FOLDER.mkdir(exist_ok=True)
    (FOLDER / "bin").mkdir(exist_ok=True)
    (FOLDER / "include").mkdir(exist_ok=True)

    shutil.copy(Path(exe_file("bin/princess2")), FOLDER / exe_file("bin/princess"))
    shutil.copy(Path("version"), FOLDER)
    for path in glob.glob("include/*.h"):
        shutil.copy(path, FOLDER / "include")
    shutil.copy(Path("include/preload.pr"), FOLDER / "include")
    shutil.copy(Path("include/symbol.pr"), FOLDER / "include")
    shutil.copy(Path("include/gencstd.py"), FOLDER / "include")
    shutil.copytree(Path("std"), FOLDER / "std")

    if sys.platform == "win32":
        shutil.make_archive(f"princess-win32-{VERSION}", "zip", FOLDER)
    else:
        shutil.make_archive(f"princess-{VERSION}", "gztar", FOLDER)

    shutil.rmtree(FOLDER)

def testsuite(extra):
    if not Path(exe_file("bin/princess2")).exists():
        build([])
    args = [exe_file("bin/princess2"), "-d", "-Isrc", "--buildfolder=build", "--outfile", exe_file("bin/testsuite"), "src/test/main.pr"]
    if sys.platform == "win32":
        args += WIN_ARGS
    subprocess.check_call(args + extra)

def clean():
    shutil.rmtree(Path("build"))
    for path in glob.glob("princess*.tar.gz") + glob.glob("princess*.zip"):
        Path(path).unlink()

def download():
    print("Downloading Princess compiler from Github...")
    
    with open(ARCHIVE, "wb") as fp:
        fp.write(requests.get(SOURCE_URL).content)

    if sys.platform == "win32":
        FOLDER = f"princess-win32-{VERSION}"
    else:
        FOLDER = f"princess-{VERSION}"

    shutil.unpack_archive(ARCHIVE, Path("bin") / FOLDER)

    shutil.copy(Path("bin") / FOLDER / "bin" / exe_file("princess"), "bin")
    shutil.rmtree(Path("bin") / FOLDER)
    Path(ARCHIVE).unlink()

def build(extra):
    args = [exe_file("bin/princess"), "-d", "-Isrc", "--buildfolder=build", "--outfile", exe_file("bin/princess2"), "src/main.pr"]
    if sys.platform == "win32":
        args += WIN_ARGS
    subprocess.check_call(args + extra)

def main():
    Path("bin/").mkdir(exist_ok = True)
    Path("build/").mkdir(exist_ok = True)
    if not Path(exe_file("bin/princess")).exists():
        download()
        gencstd.main()

    args = sys.argv
    if len(args) == 1:
        build(args[1:])
    elif args[1] == "release":
        release()
    elif args[1] == "test":
        testsuite(args[2:])
    elif args[1] == "clean":
        clean()
    elif args[1] == "download":
        download()
    else:
        build(args[1:])

if __name__ == "__main__":
    main()