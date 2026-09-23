"""The memory card icon: native/save_icon.png (32 x 32) -> proj/Scripts/SaveInfo.lua.

    python native/make_save_icon.py        (needs Pillow)

What the GameCube's memory card screen (and Dolphin's memory card manager) shows beside the
game's save: this icon, the title and the description. Screens.lua hands SaveInfo to the engine
at boot (System.SetSaveInfo), and every save written after that carries them.

The icon goes in as RGB5A3, the GameCube's texture format for a picture with soft edges, in GX's
4 x 4 tiles, two bytes a pixel, big-endian: 2048 bytes. A pixel that is fully opaque keeps 5 bits
of each colour (1RRRRRGGGGGBBBBB); any other keeps 4 bits of each and 3 of alpha (0AAARRRRGGGGBBBB).
It is written into the Lua file as hex, which the engine turns back into bytes.

The save is ONE BLOCK (8 KB): the emeralds (a few bytes), a 64-byte comment and this icon.
"""

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "save_icon.png")
OUT = os.path.abspath(os.path.join(HERE, "..", "proj", "Scripts", "SaveInfo.lua"))

TITLE = "Sonic Pipe Dream"          # at most 31 characters each
DESCRIPTION = "Chaos Emeralds"


def rgb5a3(r, g, b, a):
    if a >= 0xE0:                   # the 3-bit alpha's top step is as good as opaque: use 5 bits
        return 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    return ((a >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)


def main():
    img = Image.open(ICON).convert("RGBA")
    assert img.size == (32, 32), "the memory card icon must be 32 x 32, not %s" % (img.size,)
    px = img.load()
    data = bytearray()
    for ty in range(0, 32, 4):
        for tx in range(0, 32, 4):
            for y in range(ty, ty + 4):
                for x in range(tx, tx + 4):
                    v = rgb5a3(*px[x, y])
                    data += bytes(((v >> 8) & 0xFF, v & 0xFF))
    assert len(data) == 2048
    hexed = data.hex()
    lines = [hexed[i:i + 128] for i in range(0, len(hexed), 128)]
    out = ["-- Written by native/make_save_icon.py from native/save_icon.png. Do not edit: run that.",
           "-- What the memory card screen shows for the game's save. See Screens.lua.",
           "SaveInfo = {",
           '    title = "%s",' % TITLE,
           '    description = "%s",' % DESCRIPTION,
           "    -- 32 x 32, RGB5A3 in GX's 4 x 4 tiles, as hex",
           "    icon = table.concat({"]
    out += ['        "%s",' % l for l in lines]
    out += ["    }),", "}", ""]
    open(OUT, "w", newline="\n").write("\n".join(out))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
