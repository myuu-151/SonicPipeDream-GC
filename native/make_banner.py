"""The disc banner: native/banner.png -> proj/opening.bnr.

    python native/make_banner.py        (needs Pillow)

The picture Dolphin, Swiss and the console's own disc menu show for the game: 96 x 32. The
packager (octave-libogc's ActionManager) puts a project's own opening.bnr on the disc in place
of the engine's default, and leaves its text alone -- so the names are written here.

BNR1 layout: "BNR1", padding to 0x20; the picture at 0x20, 96 x 32 RGB5A3 in 4 x 4 tiles,
big-endian (0x1800 bytes); then at 0x1820 the short name (0x20), short maker (0x20), long name
(0x40), long maker (0x40) and description (0x80). 0x1960 bytes in all.
"""

import os
import struct

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "banner.png")
OUT = os.path.abspath(os.path.join(HERE, "..", "proj", "opening.bnr"))

NAME = "Sonic Pipe Dream"
MAKER = "Octave Engine"                 # as the engine's default banner
DESCRIPTION = "Made with the Octave engine"


def rgb5a3(r, g, b, a):
    if a >= 0xE0:                       # opaque: 1 RRRRR GGGGG BBBBB
        return 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    # translucent: 0 AAA RRRR GGGG BBBB
    return ((a >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)


def text(value, size):
    data = value.encode("ascii")[:size - 1]
    return data + b"\0" * (size - len(data))


def main():
    img = Image.open(SRC).convert("RGBA")
    if img.size != (96, 32):
        img = img.resize((96, 32), Image.LANCZOS)
    px = img.load()

    d = bytearray(b"BNR1" + b"\0" * 0x1C)
    for ty in range(0, 32, 4):
        for tx in range(0, 96, 4):
            for y in range(ty, ty + 4):
                for x in range(tx, tx + 4):
                    d += struct.pack(">H", rgb5a3(*px[x, y]))
    d += text(NAME, 0x20) + text(MAKER, 0x20) + text(NAME, 0x40) + text(MAKER, 0x40) + text(DESCRIPTION, 0x80)
    assert len(d) == 0x1960, hex(len(d))
    open(OUT, "wb").write(bytes(d))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
