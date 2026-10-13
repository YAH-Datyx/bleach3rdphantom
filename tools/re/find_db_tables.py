#!/usr/bin/env python3
"""Findet die DB-Lookup-Funktionen in arm9.bin und daraus alle Datentabellen.

Muster (vom Compiler für die db_*.inc-Tabellen erzeugt):
    ldr   rX, =TABLE
    mvn   rY, #0             ; Terminator -1
    ldrsh rZ, [rX, #key]
    ...
    ldrsh rZ, [rX, #STRIDE]!  oder  add rX, rX, #STRIDE
    cmp   rZ, rY
Ausgabe: Getter-Adresse, Tabellenadresse, Eintragsgröße, Schlüssel-Offset, Einträge.

  python3 tools/re/find_db_tables.py [unpacked/arm9.bin] [--json out.json]
"""
import json, re, struct, sys
from pathlib import Path
import capstone

BASE = 0x02000000


def scan(d: bytes):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    md.detail = False
    found = {}
    for off in range(0, len(d) - 4, 4):
        ins = next(md.disasm(d[off:off + 4], BASE + off, count=1), None)
        if not ins or ins.mnemonic != "ldr" or "[pc, #" not in ins.op_str:
            continue
        reg = ins.op_str.split(",")[0]
        lit = off + 8 + int(re.search(r"#(-?(?:0x[0-9a-f]+|\d+))", ins.op_str).group(1), 0)
        if lit + 4 > len(d):
            continue
        table = struct.unpack_from("<I", d, lit)[0]
        if not BASE <= table < BASE + len(d):
            continue
        window = list(md.disasm(d[off + 4:off + 4 + 4 * 12], BASE + off + 4))
        text = [(i.mnemonic, i.op_str) for i in window]
        if not any(m == "mvn" and op.endswith("#0") for m, op in text[:2]):
            continue
        stride = key = None
        for m, op in text:
            mm = re.match(rf"\w+, \[{reg}, #(0x[0-9a-f]+|\d+)\]!$", op)
            if m.startswith("ldr") and mm:
                stride = int(mm.group(1), 0)
            mm = re.match(rf"{reg}, {reg}, #(0x[0-9a-f]+|\d+)$", op)
            if m == "add" and mm:
                stride = int(mm.group(1), 0)
            mm = re.match(rf"\w+, \[{reg}(?:, #(0x[0-9a-f]+|\d+))?\]$", op)
            if m == "ldrsh" and mm and key is None:
                key = int(mm.group(1) or "0", 0)
            if stride:
                break
        if not stride:
            continue
        # Einträge zählen bis Terminator -1 im ersten Feld (wie der Loop prüft)
        t, n = table - BASE, 0
        while t + n * stride + 2 <= len(d) and struct.unpack_from("<h", d, t + n * stride)[0] != -1 and n < 5000:
            n += 1
        found[table] = {"getter": hex(BASE + off), "table": hex(table), "stride": stride,
                        "key_offset": key, "entries": n}
    return sorted(found.values(), key=lambda e: int(e["table"], 16))


def main(argv):
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("arm9", nargs="?", type=Path,
                   default=Path(__file__).resolve().parents[2] / "unpacked" / "arm9.bin")
    p.add_argument("--json", type=Path)
    a = p.parse_args(argv[1:])
    res = scan(a.arm9.read_bytes())
    for e in res:
        print(f"getter {e['getter']}  table {e['table']}  stride {e['stride']:#5x}  "
              f"key +{e['key_offset']}  entries {e['entries']}")
    if a.json:
        a.json.write_text(json.dumps(res, indent=1))
    print(f"{len(res)} Tabellen")


if __name__ == "__main__":
    main(sys.argv)
