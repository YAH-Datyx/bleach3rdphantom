"""Huffman-Decoder gegen handgebaute Streams (GBATEK-Format)."""
import struct, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "scripts"))
from decompress import decompress_huffman


def test_huffman_8bit_child_pair_uses_absolute_address():
    # Baum: Größenbyte 1 (= 4 Bytes), Wurzel @5 mit zwei Blättern, Paar @6/7.
    # Kinder-Paar = (5 & ~1) + 0*2 + 2 = 6. Der alte Decoder rechnete relativ zur
    # Wurzel und landete bei 7.
    data = bytes([0x28, 4, 0, 0, 0x01, 0xC0, ord("A"), ord("B")])
    data += struct.pack("<I", 0b0110 << 28)
    assert decompress_huffman(data) == b"ABBA"


def test_huffman_4bit_low_nibble_first():
    data = bytes([0x24, 1, 0, 0, 0x01, 0xC0, 0x3, 0xA])
    data += struct.pack("<I", 0b01 << 30)  # 3, dann A → Byte 0xA3
    assert decompress_huffman(data) == b"\xa3"


def test_rejects_non_huffman():
    with pytest.raises(ValueError):
        decompress_huffman(b"\x10\x04\x00\x00abcd")


# --- Encoder ---------------------------------------------------------------
import random

from compress import compress_huffman


@pytest.mark.parametrize("bits", [4, 8])
@pytest.mark.parametrize("data", [
    b"", b"A", b"AAAA", bytes(range(256)) * 3,
    bytes(random.Random(1).choices(range(256), k=5000)),
    # stark schiefe Verteilung → tiefer Baum, testet die 6-Bit-Offset-Planung
    bytes(b for i in range(1, 256) for b in [i] * (1 << (i % 12))),
])
def test_huffman_roundtrip(data, bits):
    c = compress_huffman(data, bits)
    assert c[0] == 0x20 | bits
    assert (4 + (c[4] + 1) * 2) % 4 == 0      # Bitstream 4-Byte-aligned
    assert decompress_huffman(c) == data
