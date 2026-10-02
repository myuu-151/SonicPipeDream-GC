"""Super Sonic's ball for the GameCube, from Sonic's: proj/Assets/Stage/SM_PlayerBall.oct recoloured
gold and written as SM_PlayerBallSuper.oct (index 223, as export_gc.py's write_ball would make it).

    py native/recolour_ball.py

The ball's gloss is painted into its vertices (export_gc.py, write_painted_gloss): each vertex is
min(1, base * diffuse + base * spec * 1.6 + spec * 0.25) per channel. The two lights (diffuse,
spec) are solved back out of the blue ball's red and green channels, which never clip, and the
gold base lit the same way.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, "..", "proj", "Assets", "Stage")
sys.path.insert(0, os.path.join(HERE, "..", "..", "Sonic2Special3D", "native"))

BLUE = (0.12, 0.30, 0.95)
GOLD = (0.97, 0.78, 0.10)           # export_to_octave.py's SUPER_BALL
UUID_BASE = 0x51C0FFEE00003000      # export_to_octave.py's
INDEX = 223


def lights(rgb):
    """(diffuse, spec) from a painted blue vertex's red and green."""
    r, g = rgb[0] / 255.0, rgb[1] / 255.0
    # r = BLUE[0] D + (BLUE[0] * 1.6 + 0.25) S ; g = BLUE[1] D + (BLUE[1] * 1.6 + 0.25) S
    a1, b1 = BLUE[0], BLUE[0] * 1.6 + 0.25
    a2, b2 = BLUE[1], BLUE[1] * 1.6 + 0.25
    det = a1 * b2 - a2 * b1
    d = (r * b2 - g * b1) / det
    s = (a1 * g - a2 * r) / det
    return max(0.0, d), max(0.0, s)


def main():
    src = open(os.path.join(STAGE, "SM_PlayerBall.oct"), "rb").read()
    o = 0
    magic, version, type_id, flag = struct.unpack_from("<IIIB", src, o); o += 13
    o += 8                                                      # the uuid
    n = struct.unpack_from("<I", src, o)[0]; o += 4
    name = src[o:o + n].decode("ascii"); o += n
    assert name == "SM_PlayerBall", name
    nverts, nidx, nslots = struct.unpack_from("<III", src, o); o += 12
    o += 1 + 8                                                  # asset_ref: u8 1, u64
    n = struct.unpack_from("<I", src, o)[0]; o += 4 + n          # ...and its name
    o += 2                                                      # u8, u8
    out = bytearray()
    out += struct.pack("<IIIB", magic, version, type_id, flag) + struct.pack("<Q", UUID_BASE + 1 + INDEX)
    out += struct.pack("<I", len("SM_PlayerBallSuper")) + b"SM_PlayerBallSuper"
    out += src[13 + 8 + 4 + len("SM_PlayerBall"):o]              # counts, material, flags, as they were
    for _ in range(nverts):
        out += src[o:o + 40]; o += 40                           # position (7 floats), normal (3)
        c = struct.unpack_from("<I", src, o)[0]; o += 4
        d, s = lights(((c & 255), (c >> 8) & 255, (c >> 16) & 255))
        rgb = [min(255, int(round(255 * min(1.0, b * d + b * s * 1.6 + s * 0.25)))) for b in GOLD]
        out += struct.pack("<I", rgb[0] | (rgb[1] << 8) | (rgb[2] << 16) | (255 << 24))
    out += src[o:]                                              # indices, bounds
    path = os.path.join(STAGE, "SM_PlayerBallSuper.oct")
    open(path, "wb").write(out)
    print("%s: %d vertices, gold" % (path, nverts))


main()
