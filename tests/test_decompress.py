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
