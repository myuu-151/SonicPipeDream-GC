"""The pipe's colours in all seven palettes, for recolouring the pipe without reading the disc.

A marathon changes the pipe's colours at every zone. The seven palettes are the same meshes
painted seven ways, and across all ten piece meshes a vertex's seven colours come in only ~1,500
different combinations. So:

    table          every combination: seven colours, 4 bytes each, as the meshes hold them
                   (little-endian), palette 1 first
    index[mesh]    per piece mesh (its name without the palette), 2 bytes a vertex: which
                   combination that vertex is, high byte first, the high byte plus 32 (so it is
                   a plain character in the Lua file, not an escaped zero)

That is ~135 KB for every palette of the whole pipe, against ~2 MB of mesh read off the SD card
for each change of colours (StaticMesh:StageColorsFrom, the way it was done before). The game
recolours from these in memory: StaticMesh:SetPaletteColors.

Writes proj/Scripts/PipePalettes.lua. Run it again whenever the piece meshes are exported again.
"""
import glob
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, "..", "proj", "Assets", "Stage")
OUT = os.path.join(HERE, "..", "proj", "Scripts", "PipePalettes.lua")
PALETTES = 7


def mesh_colours(path):
    """A static mesh .oct's vertex colours, as 4-byte strings in file order."""
    b = open(path, "rb").read()
    p = 21                                  # magic, version, type, a flag byte, uuid
    n = struct.unpack_from("<I", b, p)[0]
    p += 4 + n                              # name
    num_vertices = struct.unpack_from("<I", b, p)[0]
    p += 12                                 # vertices, indices, uv maps
    if b[p] == 1:                           # material: by uuid (and name)
        p += 1 + 8
    else:
        p += 1
    n = struct.unpack_from("<I", b, p)[0]
    p += 4 + n                              # material name
    if b[p + 1] != 1:                       # (triangle collision, vertex colours)
        raise SystemExit(f"{path}: no vertex colours")
    p += 2
    # a vertex: position 12, two texture coordinates 16, normal 12, colour 4
    return [b[p + 44 * i + 40:p + 44 * i + 44] for i in range(num_vertices)]


def lua_bytes(data):
    """A Lua string literal holding these bytes exactly. Every byte is written as itself (Lua
    strings take any byte, and the engine loads a script by its length) except the few that
    would end or bend the literal or its file: NUL, the newlines, the quote, the backslash, and
    Ctrl-Z (end of file to a Windows text-mode reader). Those are escapes of three digits, so a
    digit after one stays a digit. The file is about the data's own size."""
    out = ['"']
    for c in data:
        if c in (0, 10, 13, 26, 34, 92):
            out.append("\\%03d" % c)
        else:
            out.append(chr(c))
    out.append('"')
    return "".join(out)


def main():
    pieces = sorted({os.path.basename(f)[:-len("_P1.oct")]
                     for f in glob.glob(os.path.join(STAGE, "SM_Piece_*_P1.oct"))})
    combos, lookup, index = [], {}, {}
    for piece in pieces:
        palettes = [mesh_colours(os.path.join(STAGE, f"{piece}_P{k}.oct")) for k in range(1, PALETTES + 1)]
        if len({len(c) for c in palettes}) != 1:
            raise SystemExit(f"{piece}: the palettes' meshes differ in vertices")
        ids = bytearray()
        for combo in zip(*palettes):
            if combo not in lookup:
                lookup[combo] = len(combos)
                combos.append(combo)
            ids += bytes((32 + (lookup[combo] >> 8), lookup[combo] & 255))
        index[piece] = bytes(ids)
    if len(combos) > (255 - 32) * 256:
        raise SystemExit("too many colour combinations for 2-byte indices")
    table = b"".join(b"".join(combo) for combo in combos)

    lines = [
        "-- PipePalettes.lua: made by native/make_pipe_palettes.py from the piece meshes. Do not edit.",
        "-- The pipe's colours in all seven palettes: see that script, and StaticMesh:SetPaletteColors.",
        "PipePalettes = {",
        f"    palettes = {PALETTES},",
        f"    table = {lua_bytes(table)},",
        "    index = {",
    ]
    for piece in pieces:
        lines.append(f"        {piece} = {lua_bytes(index[piece])},")
    lines += ["    },", "}", ""]
    with open(OUT, "w", encoding="latin-1", newline="\n") as f:
        f.write("\n".join(lines))
    vertices = sum(len(v) // 2 for v in index.values())
    print(f"{len(pieces)} meshes, {vertices} vertices, {len(combos)} combinations: "
          f"{len(table) + vertices * 2} bytes of data, {os.path.getsize(OUT)} bytes of Lua -> {OUT}")


if __name__ == "__main__":
    main()
