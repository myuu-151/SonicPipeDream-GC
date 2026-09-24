"""The memory card icon and banner: native/save_icon.png (32 x 32) and native/banner.png
(96 x 32) -> proj/Scripts/SaveInfo.lua.

    python native/make_save_icon.py        (needs Pillow)

What the GameCube's memory card screen (and Dolphin's memory card manager) shows beside the
game's save: this icon, the banner, the title and the description. Screens.lua hands SaveInfo to the engine
at boot (System.SetSaveInfo), and every save written after that carries them.

The icon goes in as RGB5A3, the GameCube's texture format for a picture with soft edges, in GX's
4 x 4 tiles, two bytes a pixel, big-endian: 2048 bytes. A pixel that is fully opaque keeps 5 bits
of each colour (1RRRRRGGGGGBBBBB); any other keeps 4 bits of each and 3 of alpha (0AAARRRRGGGGBBBB).
It is written into the Lua file as hex, which the engine turns back into bytes.

The banner goes in as CI8: 256 colours, one byte a pixel in GX's 8 x 4 tiles (3072 bytes), then
its palette, 256 RGB5A3 colours (512 bytes). As RGB5A3 it would be 6144 bytes, and the save would
not fit one block any more.

The save is ONE BLOCK (8 KB): the emeralds (a few bytes), a 64-byte comment, the banner and the
icon.
"""

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "save_icon.png")
BANNER = os.path.join(HERE, "banner.png")          # the disc banner (make_banner.py): the same picture
OUT = os.path.abspath(os.path.join(HERE, "..", "proj", "Scripts", "SaveInfo.lua"))

TITLE = "Sonic Pipe Dream"          # at most 31 characters each
DESCRIPTION = "Chaos Emeralds"


def rgb5a3(r, g, b, a):
    if a >= 0xE0:                   # the 3-bit alpha's top step is as good as opaque: use 5 bits
        return 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    return ((a >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)


def banner_ci8():
    img = Image.open(BANNER).convert("RGBA")
    assert img.size == (96, 32), "the memory card banner must be 96 x 32, not %s" % (img.size,)
    flat = Image.new("RGBA", img.size, (0, 0, 0, 255))
    flat.alpha_composite(img)                   # the banner is opaque
    q = flat.convert("RGB").quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    px = q.load()
    data = bytearray()
    for ty in range(0, 32, 4):
        for tx in range(0, 96, 8):
            for y in range(ty, ty + 4):
                for x in range(tx, tx + 8):
                    data.append(px[x, y])
    pal = q.getpalette()[:768]
    pal += [0] * (768 - len(pal))
    for i in range(256):
        v = rgb5a3(pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2], 255)
        data += bytes(((v >> 8) & 0xFF, v & 0xFF))
    assert len(data) == 3072 + 512
    return data


def as_hex_lines(data):
    hexed = data.hex()
    return ['        "%s",' % hexed[i:i + 128] for i in range(0, len(hexed), 128)]


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
    out = ["-- Written by native/make_save_icon.py from native/save_icon.png and banner.png.",
           "-- Do not edit: run that.",
           "-- What the memory card screen shows for the game's save. See Screens.lua.",
           "SaveInfo = {",
           '    title = "%s",' % TITLE,
           '    description = "%s",' % DESCRIPTION,
           "    -- 32 x 32, RGB5A3 in GX's 4 x 4 tiles, as hex",
           "    icon = table.concat({"]
    out += as_hex_lines(data)
    out += ["    }),",
            "    -- 96 x 32, CI8 in GX's 8 x 4 tiles, then its 256-colour RGB5A3 palette, as hex",
            "    banner = table.concat({"]
    out += as_hex_lines(banner_ci8())
    out += ["    }),", "}", ""]
    open(OUT, "w", newline="\n").write("\n".join(out))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
