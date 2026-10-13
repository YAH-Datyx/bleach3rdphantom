#!/usr/bin/env python3
"""Baut das Taschenkonsole-Artifact (DS-Emulator im Browser) nach build/taschenkonsole/.

Lädt EmulatorJS 4.2.3 und die Kerne melonDS/DeSmuME 2015 von npm (GPL-3.0),
bettet emulator.css in template.html ein und benennt die Kern-Archive in .wasm
um (Artifacts liefern .data nicht aus; die Seite mappt die Namen per EJS_paths).

  python3 apps/taschenkonsole/build.py
Danach build/taschenkonsole/index.html + ejs/ als Artifact veröffentlichen.
"""
import io, shutil, tarfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "build" / "taschenkonsole"
VER = "4.2.3"


def npm(pkg: str) -> tarfile.TarFile:
    name = pkg.split("/")[-1]
    url = f"https://registry.npmjs.org/@emulatorjs/{name}/-/{name}-{VER}.tgz"
    return tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(url).read()))


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    ejs = OUT / "ejs"
    (ejs / "cores" / "reports").mkdir(parents=True)
    (ejs / "localization").mkdir()
    (ejs / "compression").mkdir()
    base = npm("emulatorjs")
    files = {m.name: m for m in base.getmembers()}
    get = lambda p: base.extractfile(files["package/" + p]).read()
    css = get("data/emulator.css").decode()
    for f in ("extract7z.js", "extractzip.js", "libunrar.js", "libunrar.wasm"):
        (ejs / "compression" / f).write_bytes(get("data/compression/" + f))
    for f in ("de-GER.json", "en-US.json"):
        (ejs / "localization" / f).write_bytes(get("data/localization/" + f))
    (ejs / "version.json").write_bytes(get("data/version.json"))
    (ejs / "LICENSE.txt").write_bytes(get("LICENSE"))
    for core in ("melonds", "desmume2015"):
        t = npm("core-" + core)
        for m in t.getmembers():
            n = m.name.split("/")[-1]
            if n in (f"{core}-wasm.data", f"{core}-legacy-wasm.data"):
                (ejs / "cores" / n.replace(".data", ".wasm")).write_bytes(t.extractfile(m).read())
            elif m.name.endswith(f"reports/{core}.json"):
                (ejs / "cores" / "reports" / n).write_bytes(t.extractfile(m).read())
    page = (HERE / "template.html").read_text().replace("/*__EJS_CSS__*/", css)
    (OUT / "index.html").write_text(page)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
