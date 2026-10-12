#!/usr/bin/env python3
"""Nintendo-Huffman-Encoder (0x28 8-bit / 0x24 4-bit), Gegenstück zu decompress.py.

Damit lassen sich geänderte Dateien wieder so komprimieren, wie das Spiel sie
erwartet. Format nach GBATEK (SWI 13h):

  Header  u32  typ | (entpackte Größe << 8)
  Baum    Größenbyte, dann Knoten. Knotenbyte = Offset (6 Bit) | 0x80/0x40,
          wenn Kind 0/1 ein Blatt ist. Das Kinder-Paar eines Knotens im Paar p
          liegt im Paar p + 1 + Offset, also höchstens 64 Paare später.
  Daten   Bitstream in 32-Bit-LE-Wörtern, MSB zuerst

Die Schwierigkeit ist die 6-Bit-Grenze. Die Kinder werden deshalb mit Fristen
platziert: in die Tiefe, solange alle Fristen einhaltbar bleiben, sonst nach
der frühesten Frist.

  python3 tools/scripts/compress.py <in> <out> [--bits 4|8]
"""
from __future__ import annotations
import heapq, itertools, struct, sys


class _Node:
    __slots__ = ("sym", "left", "right")

    def __init__(self, sym=None, left=None, right=None):
        self.sym, self.left, self.right = sym, left, right

    @property
    def leaf(self) -> bool:
        return self.sym is not None


def _symbols(data: bytes, bits: int) -> list[int]:
    if bits == 8:
        return list(data)
    return [v for b in data for v in (b & 0x0F, b >> 4)]


def _build_tree(syms: list[int]) -> _Node:
    freq: dict[int, int] = {}
    for s in syms:
        freq[s] = freq.get(s, 0) + 1
    if len(freq) == 1:  # Baum braucht zwei Blätter
        freq[(next(iter(freq)) + 1) & 0xFF] = 0
    tie = itertools.count()
    heap = [(f, next(tie), _Node(sym=s)) for s, f in sorted(freq.items())]
    heapq.heapify(heap)
    while len(heap) > 1:
        f1, _, a = heapq.heappop(heap)
        f2, _, b = heapq.heappop(heap)
        heapq.heappush(heap, (f1 + f2, next(tie), _Node(left=a, right=b)))
    return heap[0][2]


def _feasible(deadlines: list[int], next_pair: int) -> bool:
    """Lassen sich alle Wartenden ab next_pair (eins pro Paar) fristgerecht platzieren?"""
    for k, d in enumerate(sorted(deadlines)):
        if d < next_pair + k:
            return False
    return True


def _layout(root: _Node) -> bytes:
    """Ordnet die Knoten in Paaren an, so dass jeder Offset in 6 Bit passt.

    Wartende innere Knoten haben eine Frist (eigenes Paar + 64). Bevorzugt wird
    der neueste (Tiefe zuerst, das hält die Warteschlange kurz), aber nur, wenn
    danach alle Fristen noch einhaltbar bleiben. Sonst kommt die früheste Frist dran.
    """
    tree = bytearray([0, 0])          # [Größenbyte, Wurzel]
    pending: list[tuple[int, _Node]] = [(1, root)]   # (Index im Baum, innerer Knoten)
    while pending:
        pair = len(tree) // 2
        deadline = [i // 2 + 64 for i, _ in pending]
        k = len(pending) - 1
        node = pending[k][1]
        new = [pair + 64 for c in (node.left, node.right) if not c.leaf]
        if not _feasible(deadline[:k] + new, pair + 1):
            k = min(range(len(pending)), key=deadline.__getitem__)
        idx, node = pending.pop(k)
        offset = pair - idx // 2 - 1
        if not 0 <= offset <= 63:
            raise ValueError("Huffman-Baum nicht platzierbar (6-Bit-Offset)")
        flags = 0
        for bit, child in ((0, node.left), (1, node.right)):
            if child.leaf:
                tree.append(child.sym)
                flags |= 0x80 >> bit
            else:
                tree.append(0)
                pending.append((len(tree) - 1, child))
        tree[idx] = offset | flags
    if len(tree) % 4:                 # Bitstream muss 4-Byte-aligned beginnen
        tree += b"\0\0"
    tree[0] = len(tree) // 2 - 1
    return bytes(tree)


def _codes(root: _Node) -> dict[int, tuple[int, int]]:
    codes = {}
    stack = [(root, 0, 0)]
    while stack:
        n, code, length = stack.pop()
        if n.leaf:
            codes[n.sym] = (code, length)
        else:
            stack.append((n.left, code << 1, length + 1))
            stack.append((n.right, code << 1 | 1, length + 1))
    return codes


def compress_huffman(data: bytes, bits: int = 8) -> bytes:
    if bits not in (4, 8):
        raise ValueError("bits muss 4 oder 8 sein")
    if len(data) >= 1 << 24:
        raise ValueError("Datei zu groß für den 24-Bit-Größenheader")
    syms = _symbols(data, bits)
    root = _build_tree(syms or [0])
    out = bytearray(struct.pack("<I", (0x20 | bits) | len(data) << 8))
    out += _layout(root)
    codes = _codes(root)
    acc = nbits = 0
    for s in syms:
        code, length = codes[s]
        for i in range(length - 1, -1, -1):
            acc = acc << 1 | (code >> i & 1)
            nbits += 1
            if nbits == 32:
                out += struct.pack("<I", acc)
                acc = nbits = 0
    if nbits:
        out += struct.pack("<I", acc << (32 - nbits))
    return bytes(out)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    bits = int(argv[argv.index("--bits") + 1]) if "--bits" in argv else 8
    data = open(argv[1], "rb").read()
    open(argv[2], "wb").write(compress_huffman(data, bits))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
