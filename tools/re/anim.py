#!/usr/bin/env python3
"""Animationen exportieren, umbauen und zurückschreiben.

  # alles mit Animationen finden
  python3 tools/re/anim.py list

  # eine Datei (z. B. Einheiten-Sprite) in einen Arbeitsordner exportieren
  python3 tools/re/anim.py export yamada/FPiece/FPiece_2d_001n.bin build/anim/fp001

  # Kampf-Animation aus einem Charakter-Paket: datei.cpk#ID (IDs: tools/re/cpk.py list)
  python3 tools/re/anim.py export kuro/c001/c001.cpk#3 build/anim/c001_3

  # nach dem Bearbeiten zurück nach unpacked-decomp/ schreiben
  python3 tools/re/anim.py import build/anim/fp001

Danach wie gewohnt `recompress.py` und `build_rom.py` ausführen.

Arbeitsordner:
  source.json   Herkunft: Datei + Index von NCER/NANR/NCGR/NCLR im Archiv;
                tile_count erhöhen (und tiles.png vergrößern) = neue Tiles anhängen
  nanr.json     Sequenzen: Name, Loop-Start, Modus, Frames (Zelle, Dauer, …)  ← umbauen
  ncer.json     Zellen: OAM-Objekte (x, y, w, h, tile, palette, flip)          ← umbauen
  tiles.png     NCGR als indiziertes PNG (Index = Farbnummer)                  ← bemalen
  cells/        jede Zelle gerendert (nur Ansicht)
  preview/      je Sequenz ein GIF (nur Ansicht)

Pfade beziehen sich auf unpacked-decomp/data. Exportierte Grafiken gehören den
Rechteinhabern und bleiben lokal (build/ ist gitignored).
"""
from __future__ import annotations
import argparse, json, struct, sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nitro_anim as na  # noqa: E402
from nitro2png import parse_nclr, section  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEC = ROOT / "unpacked-decomp" / "data"


# --- Archiv-Zugriff ---------------------------------------------------------

def _split_cpk(path: Path) -> tuple[Path, int | None]:
    """'datei.cpk#3' → (datei.cpk, 3); sonst (path, None)."""
    s = str(path)
    if "#" in s:
        base, _, cid = s.rpartition("#")
        return Path(base), int(cid)
    return path, None


def cpk_palette(cpk_path: Path) -> bytes | None:
    """Kampf-Pakete enthalten die Palette(n) als eigene Einträge (IDs ab 10000)."""
    import cpk as cpkmod
    c = cpkmod.read_cpk(cpk_path)
    for f in c["files"]:
        d = cpkmod.file_data(c, f)
        if d[:4] == b"RLCN":
            return d
    return None


def load_parts(path: Path) -> tuple[list[bytes], bool]:
    base, cid = _split_cpk(path)
    if cid is not None:
        import cpk as cpkmod
        c = cpkmod.read_cpk(base)
        f = next(f for f in c["files"] if f["id"] == cid)
        data = cpkmod.file_data(c, f)
        import ndspy.narc
        return list(ndspy.narc.NARC(data).files), True
    data = path.read_bytes()
    if data[:4] == b"NARC":
        import ndspy.narc
        return list(ndspy.narc.NARC(data).files), True
    return [data], False


def save_parts(path: Path, parts: list[bytes], is_narc: bool) -> None:
    base, cid = _split_cpk(path)
    if cid is not None:
        import cpk as cpkmod
        import ndspy.narc
        c = cpkmod.read_cpk(base)
        f = next(f for f in c["files"] if f["id"] == cid)
        narc = ndspy.narc.NARC(cpkmod.file_data(c, f))
        narc.files = parts
        base.write_bytes(cpkmod.build_cpk(c, {cid: narc.save()}))
        return
    if not is_narc:
        path.write_bytes(parts[0])
        return
    import ndspy.narc
    narc = ndspy.narc.NARC(path.read_bytes())
    narc.files = parts
    path.write_bytes(narc.save())


def find_groups(parts: list[bytes]) -> list[dict]:
    """Ordnet NCER/NANR/NCGR/NCLR zu Gruppen: n-te NCER ↔ n-te NANR/NCGR/NCLR."""
    idx = {m: [i for i, p in enumerate(parts) if p[:4] == m] for m in (b"RECN", b"RNAN", b"RGCN", b"RLCN")}
    groups = []
    for n, ncer in enumerate(idx[b"RECN"]):
        def pick(m):
            lst = idx[m]
            return lst[min(n, len(lst) - 1)] if lst else None
        groups.append({"ncer": ncer, "nanr": pick(b"RNAN"), "ncgr": pick(b"RGCN"), "nclr": pick(b"RLCN")})
    return groups


# --- NCGR <-> indizierte Pixel ---------------------------------------------

def ncgr_info(ncgr: bytes) -> dict:
    s = section(ncgr, b"RAHC")
    h, w, depth, mapping, tiled, size, off = struct.unpack_from("<HHIIIII", s, 8)
    return {"bpp": 4 if depth == 3 else 8, "data_off": 0x10 + 8 + off, "size": size,
            "w_tiles": w if w != 0xFFFF else 0, "h_tiles": h if h != 0xFFFF else 0, "mapping": mapping}


def char_data(ncgr: bytes) -> bytes:
    i = ncgr_info(ncgr)
    return ncgr[i["data_off"]:i["data_off"] + i["size"]]


def tiles_to_image(chars: bytes, bpp: int, pal: list, width_tiles: int = 16) -> Image.Image:
    tsize = 8 * bpp
    n = len(chars) // tsize
    rows = max(1, (n + width_tiles - 1) // width_tiles)
    img = Image.new("P", (width_tiles * 8, rows * 8))
    flat = (pal + [(0, 0, 0)] * 256)[:256]
    img.putpalette([c for rgb in flat for c in rgb])
    px = img.load()
    for t in range(n):
        tx, ty = (t % width_tiles) * 8, (t // width_tiles) * 8
        chunk = chars[t * tsize:(t + 1) * tsize]
        vals = list(chunk) if bpp == 8 else [v for b in chunk for v in (b & 15, b >> 4)]
        for k, v in enumerate(vals):
            px[tx + k % 8, ty + k // 8] = v
    return img


def image_to_tiles(img: Image.Image, bpp: int, n_tiles: int) -> bytes:
    if img.mode != "P":
        raise ValueError("tiles.png muss ein indiziertes PNG bleiben (Modus P)")
    w = img.width // 8
    px = img.load()
    out = bytearray()
    for t in range(n_tiles):
        tx, ty = (t % w) * 8, (t // w) * 8
        vals = [px[tx + k % 8, ty + k // 8] for k in range(64)]
        if bpp == 8:
            out += bytes(vals)
        else:
            if max(vals) > 15:
                raise ValueError(f"Tile {t}: 4-bit-Grafik erlaubt nur Farbindex 0–15")
            out += bytes(vals[k] | vals[k + 1] << 4 for k in range(0, 64, 2))
    return bytes(out)


def replace_char_data(ncgr: bytes, chars: bytes) -> bytes:
    """Ersetzt die Tile-Daten. Die Anzahl darf wachsen oder schrumpfen; Größenfelder
    (Datei, RAHC-Sektion, Datengröße, Höhe in Tiles) werden nachgezogen."""
    i = ncgr_info(ncgr)
    out = bytearray(ncgr[:i["data_off"]] + chars + ncgr[i["data_off"] + i["size"]:])
    delta = len(chars) - i["size"]
    if delta:
        sec = 0x10                                    # RAHC folgt direkt auf den Header
        struct.pack_into("<I", out, 8, len(out))      # Dateigröße
        struct.pack_into("<I", out, sec + 4, struct.unpack_from("<I", out, sec + 4)[0] + delta)
        struct.pack_into("<I", out, sec + 0x18, len(chars))
        if i["w_tiles"]:                              # 2D-Layout: Höhe neu berechnen
            n = len(chars) // (8 * i["bpp"])
            if n % i["w_tiles"]:
                raise ValueError(f"Tile-Anzahl muss ein Vielfaches von {i['w_tiles']} sein (2D-Grafik)")
            struct.pack_into("<H", out, sec + 8, n // i["w_tiles"])
    return bytes(out)


# --- Rendern ----------------------------------------------------------------

def render_cell(cell: dict, ncer: dict, chars: bytes, bpp: int, pal: list, index: int) -> tuple[Image.Image, int, int]:
    """Setzt die OAM-Objekte einer Zelle zusammen. Gibt Bild + Ursprung (x0, y0) zurück."""
    if not cell["oam"]:
        return Image.new("RGBA", (1, 1)), 0, 0
    x0 = min(o["x"] for o in cell["oam"]); y0 = min(o["y"] for o in cell["oam"])
    x1 = max(o["x"] + o["w"] for o in cell["oam"]); y1 = max(o["y"] + o["h"] for o in cell["oam"])
    img = Image.new("RGBA", (x1 - x0, y1 - y0))
    px = img.load()
    base = ncer["vram"]["cells"][index][0] if "vram" in ncer else 0
    unit = 32 << (ncer["mapping"] & 3) if ncer["mapping"] < 4 else 32
    for o in reversed(cell["oam"]):          # erstes OAM liegt oben
        b8 = o["bpp8"] or bpp == 8
        tsize = 64 if b8 else 32
        tw, th = o["w"] // 8, o["h"] // 8
        start = base + o["tile"] * unit
        for ty in range(th):
            for tx in range(tw):
                off = start + (ty * tw + tx) * tsize
                chunk = chars[off:off + tsize]
                if len(chunk) < tsize:
                    continue
                vals = list(chunk) if b8 else [v for b in chunk for v in (b & 15, b >> 4)]
                pb = 0 if b8 else o["palette"] * 16
                for k, v in enumerate(vals):
                    if v == 0:
                        continue
                    x, y = tx * 8 + k % 8, ty * 8 + k // 8
                    if o["hflip"]:
                        x = o["w"] - 1 - x
                    if o["vflip"]:
                        y = o["h"] - 1 - y
                    c = pal[pb + v] if pb + v < len(pal) else (255, 0, 255)
                    px[o["x"] - x0 + x, o["y"] - y0 + y] = (*c, 255)
    return img, x0, y0


def frame_images(nanr: dict, ncer: dict, rendered: list) -> list[list[tuple[Image.Image, int]]]:
    """Pro Sequenz: Liste (Bild auf gemeinsamer Leinwand, Dauer in 1/60 s)."""
    out = []
    for s in nanr["sequences"]:
        cells = [rendered[f["cell"]] for f in s["frames"] if f["cell"] < len(rendered)]
        if not cells:
            out.append([])
            continue
        offs = [(f.get("x", f.get("tx", 0)), f.get("y", f.get("ty", 0))) for f in s["frames"]]
        x0 = min(c[1] + o[0] for c, o in zip(cells, offs)); y0 = min(c[2] + o[1] for c, o in zip(cells, offs))
        x1 = max(c[1] + o[0] + c[0].width for c, o in zip(cells, offs))
        y1 = max(c[2] + o[1] + c[0].height for c, o in zip(cells, offs))
        frames = []
        for (img, cx, cy), (ox, oy), f in zip(cells, offs, s["frames"]):
            canvas = Image.new("RGBA", (x1 - x0, y1 - y0))
            canvas.alpha_composite(img, (cx + ox - x0, cy + oy - y0))
            frames.append((canvas, f["duration"]))
        out.append(frames)
    return out


# --- Befehle ----------------------------------------------------------------

def _anim_sources(dec: Path):
    for f in sorted(dec.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix == ".cpk":
            import cpk as cpkmod
            try:
                c = cpkmod.read_cpk(f)
            except Exception:
                continue
            for e in c["files"]:
                d = cpkmod.file_data(c, e)
                if d[:4] == b"NARC":
                    yield Path(f"{f}#{e['id']}")
        else:
            yield f


def cmd_list(dec: Path) -> None:
    for f in _anim_sources(dec):
        try:
            parts, _ = load_parts(f)
        except Exception:
            continue
        groups = find_groups(parts)
        for g in groups:
            if g["nanr"] is None:
                continue
            nanr = na.parse_nanr(parts[g["nanr"]])
            names = nanr.get("labels") or []
            print(f"{f.relative_to(dec)}  [ncer {g['ncer']}]  {len(nanr['sequences'])} Sequenzen  "
                  f"{', '.join(names[:6])}{' …' if len(names) > 6 else ''}")


def cmd_export(rel: str, out: Path, group: int, dec: Path) -> None:
    src = dec / rel
    parts, _ = load_parts(src)
    groups = find_groups(parts)
    if not groups:
        raise SystemExit("Keine NCER in dieser Datei")
    g = groups[group]
    ncer = na.parse_ncer(parts[g["ncer"]])
    nanr = na.parse_nanr(parts[g["nanr"]]) if g["nanr"] is not None else None
    ncgr = parts[g["ncgr"]]
    base, cid = _split_cpk(src)
    if g["nclr"] is not None:
        pal = parse_nclr(parts[g["nclr"]])
    elif cid is not None and (p := cpk_palette(base)):
        pal = parse_nclr(p)
    else:
        pal = [(i, i, i) for i in range(0, 256)]   # Graustufen, falls keine Palette gefunden
    info = ncgr_info(ncgr)
    chars = char_data(ncgr)
    out.mkdir(parents=True, exist_ok=True)
    n_tiles = len(chars) // (8 * info["bpp"])
    (out / "source.json").write_text(json.dumps({"file": rel, "group": group, **g, "bpp": info["bpp"],
                                                 "tile_count": n_tiles}, indent=1))
    (out / "ncer.json").write_text(json.dumps(ncer, indent=1))
    if nanr:
        (out / "nanr.json").write_text(json.dumps(nanr, indent=1))
    tiles_to_image(chars, info["bpp"], pal).save(out / "tiles.png")
    (out / "cells").mkdir(exist_ok=True)
    rendered = []
    for i, c in enumerate(ncer["cells"]):
        r = render_cell(c, ncer, chars, info["bpp"], pal, i)
        rendered.append(r)
        r[0].save(out / "cells" / f"cell_{i:03d}.png")
    if nanr:
        (out / "preview").mkdir(exist_ok=True)
        names = nanr.get("labels") or []
        for k, frames in enumerate(frame_images(nanr, ncer, rendered)):
            if not frames:
                continue
            name = names[k] if k < len(names) else f"seq{k}"
            imgs = [f[0] for f in frames]
            imgs[0].save(out / "preview" / f"{k:02d}_{name}.gif", save_all=True, append_images=imgs[1:],
                         duration=[max(20, round(d * 1000 / 60)) for _, d in frames], loop=0, disposal=2)
    print(f"→ {out}: {len(ncer['cells'])} Zellen, "
          f"{len(nanr['sequences']) if nanr else 0} Sequenzen, {len(chars) // (8 * info['bpp'])} Tiles")


def cmd_import(work: Path, dec: Path) -> None:
    src = json.loads((work / "source.json").read_text())
    path = dec / src["file"]
    parts, is_narc = load_parts(path)
    parts[src["ncer"]] = na.build_ncer(json.loads((work / "ncer.json").read_text()))
    if (work / "nanr.json").exists() and src.get("nanr") is not None:
        parts[src["nanr"]] = na.build_nanr(json.loads((work / "nanr.json").read_text()))
    ncgr = parts[src["ncgr"]]
    info = ncgr_info(ncgr)
    n_tiles = src.get("tile_count", info["size"] // (8 * info["bpp"]))   # erhöhen = neue Tiles
    img = Image.open(work / "tiles.png")
    if (img.width // 8) * (img.height // 8) < n_tiles:
        raise ValueError(f"tiles.png enthält weniger als tile_count={n_tiles} Tiles — Bild vergrößern")
    chars = image_to_tiles(img, info["bpp"], n_tiles)
    parts[src["ncgr"]] = replace_char_data(ncgr, chars)
    save_parts(path, parts, is_narc)
    print(f"← {path.relative_to(dec)} aktualisiert. Weiter: recompress.py → build_rom.py")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dec", type=Path, default=DEC, help="entpacktes Datenverzeichnis")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    e = sub.add_parser("export")
    e.add_argument("file")
    e.add_argument("out", type=Path)
    e.add_argument("--group", type=int, default=0, help="n-te NCER im Archiv")
    i = sub.add_parser("import")
    i.add_argument("work", type=Path)
    a = p.parse_args(argv)
    if a.cmd == "list":
        cmd_list(a.dec)
    elif a.cmd == "export":
        cmd_export(a.file, a.out, a.group, a.dec)
    else:
        cmd_import(a.work, a.dec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
