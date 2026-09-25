"""The memory card icon and banner: native/save_icon.png (32 x 32) and native/banner.png
(96 x 32) -> proj/Scripts/SaveInfo.lua.

    python native/make_save_icon.py        (needs Pillow)

What the GameCube's memory card screen (and Dolphin's memory card manager) shows beside the
game's save: this icon, the banner, the title and the description. Screens.lua hands SaveInfo to the engine
at boot (System.SetSaveInfo), and every save written after that carries them.

The icon is ANIMATED: the emerald in each of the seven emeralds' colours in turn, stage 1 to 7
(the stage select's own recolouring: the PC's gen_menu_assets.py, recolour and EMERALD_HUE), a
frame every 12 retraces, in a loop. The frames go in as CI8 sharing one palette: one byte a pixel
in GX's 8 x 4 tiles (1024 bytes a frame), then 256 RGB5A3 colours (512 bytes). RGB5A3 is two
bytes a pixel: a fully opaque pixel keeps 5 bits of each colour (1RRRRRGGGGGBBBBB), any other 4
bits of each and 3 of alpha (0AAARRRRGGGGBBBB). It is all written into the Lua file as hex, which
the engine turns back into bytes.

The banner goes in as CI8 too: 3072 bytes, then its own palette (512 bytes). As RGB5A3 it would
be 6144 bytes.

The save is TWO BLOCKS (16 KB): the emeralds (a few bytes), a 64-byte comment, the banner (3584)
and the seven icon frames with their palette (7680). A still icon kept it to one block; the
owner chose the seven colours over the block.
"""

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.abspath(os.path.join(HERE, "..", "..", "Sonic2Special3D"))
sys.path.insert(0, os.path.join(PC, "native"))
from gen_menu_assets import EMERALD_HUE, recolour     # the stage select's seven emerald colours

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


def gem_only(img):
    """The icon's emerald alone: its green pixels (the tile behind it is blue), the rest cleared.
    The recolouring is the stage select's, which colours everything it is given."""
    import colorsys
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            h, s, _v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if a == 0 or not (0.18 <= h <= 0.46 and s > 0.3):
                px[x, y] = (0, 0, 0, 0)
    return out


def icon_frames_ci8():
    """The icon with its emerald in each of the seven colours, as CI8 frames sharing one
    256-colour palette (made from all seven together), then that palette."""
    img = Image.open(ICON).convert("RGBA")
    assert img.size == (32, 32), "the memory card icon must be 32 x 32, not %s" % (img.size,)
    gem = gem_only(img)
    frames = []
    for stage in range(1, 8):
        frame = img.copy()
        frame.alpha_composite(recolour(gem, *EMERALD_HUE[stage]))    # the gem's pixels, recoloured
        frames.append(frame)

    # One palette for all of them: quantize the seven side by side. Pixels quantize as RGBA, so
    # a see-through pixel keeps its alpha in its palette entry.
    strip = Image.new("RGBA", (32 * len(frames), 32))
    for i, f in enumerate(frames):
        strip.paste(f, (32 * i, 0))
    q = strip.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = q.getpalette("RGBA")[:1024]
    pal += [0] * (1024 - len(pal))
    px = q.load()

    data = bytearray()
    for i in range(len(frames)):
        for ty in range(0, 32, 4):
            for tx in range(0, 32, 8):
                for y in range(ty, ty + 4):
                    for x in range(tx, tx + 8):
                        data.append(px[32 * i + x, y])
    for c in range(256):
        v = rgb5a3(pal[c * 4], pal[c * 4 + 1], pal[c * 4 + 2], pal[c * 4 + 3])
        data += bytes(((v >> 8) & 0xFF, v & 0xFF))
    assert len(data) == 7 * 1024 + 512
    return data, frames


def as_hex_lines(data):
    hexed = data.hex()
    return ['        "%s",' % hexed[i:i + 128] for i in range(0, len(hexed), 128)]


def main():
    data, _ = icon_frames_ci8()
    out = ["-- Written by native/make_save_icon.py from native/save_icon.png and banner.png.",
           "-- Do not edit: run that.",
           "-- What the memory card screen shows for the game's save. See Screens.lua.",
           "SaveInfo = {",
           '    title = "%s",' % TITLE,
           '    description = "%s",' % DESCRIPTION,
           "    -- 32 x 32, animated: 7 CI8 frames (GX's 8 x 4 tiles), then their shared RGB5A3 palette, as hex",
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
