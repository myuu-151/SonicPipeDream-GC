"""Export a stage for the GAMECUBE build, out of the PC repo's stage data.

    blender -b ../Sonic2Special3D/external/halfpipe/TrackPiecesPack.blend \\
        --python native/export_gc.py -- [stage 1-7]

This repo designs nothing. The PC repo (a sibling folder, ../Sonic2Special3D) owns the stage
generator, the stage .json files and the source art; this script READS them and writes assets
cut down for a machine with 24 MB of memory:

    proj/Assets/Stage/SM_Piece_<Name>[_Gloss]_P<N>.oct   the track pieces in ONE palette, the stage's
    proj/Assets/Stage/SM_Ring.oct, SM_Ring_00..11.oct    the PC's ring and its 12 spin frames
    proj/Assets/Stage/SM_RingRainbow_0..8.oct            the arch's rings, in its colours
    proj/Assets/Stage/SM_Bomb.oct                        the PC's bomb
    proj/Assets/Stage/SM_PlayerBall.oct, SM_Emerald.oct
    proj/Scripts/StageData<N>.lua                        the same table the PC game reads

HOW IT REUSES THE PC EXPORTER WITHOUT TOUCHING IT. The PC's export_to_octave.py runs main() as
it is imported, so it cannot simply be imported. Its source is read, the last line is left off,
and the rest is run here: every writer in it (write_mesh, write_materials, torus, gold, the
stage table) is then used as it stands, pointed at this project's folders. A fix to the PC's
mesh writer reaches the GameCube on the next export; nothing here can change the PC's output.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.abspath(os.path.join(HERE, "..", "..", "Sonic2Special3D"))
PC_EXPORTER = os.path.join(PC, "native", "export_to_octave.py")
PROJ = os.path.abspath(os.path.join(HERE, "..", "proj"))
ASSETS = os.path.join(PROJ, "Assets", "Stage")

# GEOMETRY IS NOT WHAT THIS MACHINE IS SHORT OF. The small meshes are the PC's own, triangle for
# triangle: the 36 x 16 ring in all 12 spin frames, the 4,000 triangle bomb. They were cut down here
# at first out of habit, and it cost the ring its metal: the gold is painted per vertex in bands
# that run round the tube, and at 6 segments the bands fell between the vertices. What is short
# is MEMORY (textures, audio), and that is where the GameCube build differs from the PC.
RING_SPIN_FRAMES = 12               # as the PC; SpecialStage.lua counts the same
BOMB_TEX_SIZE = 256                 # the bomb's texture here (the PC's is 1024): a bomb is small on a TV

source = open(PC_EXPORTER, encoding="utf-8").read()
source = source[:source.rindex("\nmain()")]
pc = {"__name__": "pc_export", "__file__": PC_EXPORTER}
exec(compile(source, PC_EXPORTER, "exec"), pc)
pc["PROJ"], pc["ASSETS"] = PROJ, ASSETS

bmesh, grl, rm, stage_palettes = pc["bmesh"], pc["grl"], pc["rm"], pc["stage_palettes"]
write_mesh, simple, torus, gold, to_octave = pc["write_mesh"], pc["simple"], pc["torus"], pc["gold"], pc["to_octave"]
STAGE = pc["STAGE"]


# --- the gloss, painted -------------------------------------------------------------------
# On the PC the arch spheres are a LIT material with a strong specular highlight. The GameCube
# renderer has diffuse light only, so there the spheres came out flat. The highlight is painted
# into the vertices here instead, the way the gold rings' reflection is: this game only ever
# looks DOWN THE TRACK, so where a highlight sits on a sphere is known in advance.
#   - the light is the PC's: the same ambient and sun strengths, from above and a little ahead
#   - the eye is up the track behind the sphere and in toward the pipe's axis, where the camera rides
#   - the highlight is tinted by the sphere's own colour, as the PC's shader tints its specular
# It follows the TRACK: a corner piece turns through 90 degrees, so each vertex takes "forward"
# and "up" from the nearest point of the piece's own centre line, not from the piece as a whole.
PC_AMBIENT, PC_SUN = 0.62, 0.45     # SpecialStage.lua's ambient light and sun, as on the PC
GLOSS_SPECULAR = 0.85               # M_StageGloss on the PC
GLOSS_SHININESS = 22.0              # the PC's is 48; a vertex-painted highlight needs to be a little
                                    # broader than that, or it falls between the vertices and flickers
PATH_SAMPLES = 32
# (A brighter version -- the diffuse lifted 1.3x, a sharper and stronger highlight -- was tried to
# chase the PC's brighter orange. The darker one here was preferred, so this is it.)

def write_painted_gloss(name, index, mesh, colour_of_slot, keep_slot, path, light_ahead=0.25):
    Vector = pc["Vector"]
    if path is not None:
        frames = [path.frame(path.length * i / PATH_SAMPLES) for i in range(PATH_SAMPLES + 1)]
        spots = [(m.translation.copy(), m.col[0].xyz.normalized(), m.col[2].xyz.normalized()) for m in frames]
    else:
        # A thing the game stands on the pipe (a bomb): its own X is up the track and its own Z
        # is away from the pipe's surface, toward the axis, wherever round the pipe it is.
        spots = [(Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)))]
    radius = rm.PIPE_RADIUS

    def paint(p, n, base):
        origin, fwd, up = min(spots, key=lambda sp: (sp[0] - p).length_squared)
        axis = origin + up * radius                         # the middle of the pipe, level with here
        inward = (axis - p)
        inward = inward.normalized() if (path is not None and inward.length > 1e-6) else up
        light = (up + fwd * light_ahead).normalized()      # (negative: from behind, the camera's side)
        eye = (-fwd + inward * 0.35).normalized()
        half = (light + eye).normalized()
        diffuse = PC_AMBIENT + PC_SUN * max(0.0, n.dot(light))
        spec = GLOSS_SPECULAR * max(0.0, n.dot(half)) ** GLOSS_SHININESS
        return tuple(min(1.0, c * diffuse + c * spec * 1.6 + spec * 0.25) for c in base)

    mesh.calc_loop_triangles()
    normals = [Vector(n.vector) for n in mesh.corner_normals]
    verts, index_of, idx = [], {}, []
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for tri in mesh.loop_triangles:
        if not keep_slot(tri.material_index):
            continue
        base = colour_of_slot(tri.material_index)
        for corner, loop in zip(tri.vertices, tri.loops):
            p = mesh.vertices[corner].co
            n = normals[loop] if tri.use_smooth else Vector(tri.normal)
            rgb = tuple(max(0, min(255, int(round(255 * c)))) for c in paint(p, n, base))
            key = (round(p.x, 4), round(p.y, 4), round(p.z, 4), rgb)
            if key not in index_of:
                index_of[key] = len(verts)
                verts.append((to_octave(p), to_octave(n), rgb))
                for k in range(3):
                    lo[k], hi[k] = min(lo[k], to_octave(p)[k]), max(hi[k], to_octave(p)[k])
            idx.append(index_of[key])
    if not verts:
        return 0
    centre = (lo + hi) * 0.5
    far = max((Vector(v[0]) - centre).length for v in verts)
    u8, u32, f32 = pc["u8"], pc["u32"], pc["f32"]
    d = pc["header"](pc["TYPE_STATICMESH"], pc["UUID_BASE"] + 1 + index, name)
    d += u32(len(verts)) + u32(len(idx)) + u32(1)
    d += pc["asset_ref"](pc["MATERIALS"]["M_StageMatte"][0], "M_StageMatte")     # unlit: the paint IS the light
    d += u8(0) + u8(1)
    for p, n, rgb in verts:
        d += f32(p[0]) + f32(p[1]) + f32(p[2]) + f32(0) + f32(0) + f32(0) + f32(0)
        d += f32(n[0]) + f32(n[1]) + f32(n[2])
        d += u32(rgb[0] | (rgb[1] << 8) | (rgb[2] << 16) | (255 << 24))
    for i in idx:
        d += u32(i)
    d += u8(0) + u32(0)
    d += f32(centre.x) + f32(centre.y) + f32(centre.z) + f32(far)
    open(os.path.join(ASSETS, name + ".oct"), "wb").write(d)
    return len(idx) // 3


# SONIC'S BALL, its gloss painted on too. On the PC it is lit and shiny (M_StageGloss); here a lit
# material on vertex colours comes out unlit, and the ball was a flat blue disc. Painted as a thing
# standing on the pipe (write_painted_gloss with no path): its own X up the track, Z away from the
# surface -- which is how the ball is turned in the air here, where it does NOT roll (the patch in
# patch_from_pc.py; a roll would carry the highlight round with it, and on a plain sphere the roll
# itself was never visible). Subdivided once more than before, so the highlight has vertices to sit on.
# The ball's light comes from BEHIND and above (the arch spheres' is a little ahead), which brings
# its highlight down off the top of the ball onto the side the camera sees: about 40 degrees up,
# not 60.
BALL_LIGHT_AHEAD = -0.6


def write_ball():
    write_painted_gloss("SM_PlayerBall", 221,
                        simple("Ball", lambda bm: bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.7)),
                        lambda k: (0.12, 0.30, 0.95), lambda k: True, None, light_ahead=BALL_LIGHT_AHEAD)


# --- really lit -----------------------------------------------------------------------------
# On this machine a LIT material on a mesh that carries VERTEX COLOURS comes out unlit. Sonic, who
# has a texture and no vertex colours, is lit properly. So a thing that must take the light gets
# its colours Sonic's way: a tiny texture of swatches, one for each of its materials, with every
# face's UVs parked in the middle of its swatch -- and no vertex colours at all.
TYPE_TEXTURE = 0xCDBBDA30
SWATCH = 8                          # pixels a swatch; nearest filtering, so the middle is the colour


def write_lit_swatched(name, index, mesh, colours, specular=0.85, shininess=48.0):
    Vector = pc["Vector"]
    u8, u32, i32, f32 = pc["u8"], pc["u32"], pc["i32"], pc["f32"]
    header, asset_ref, null_ref = pc["header"], pc["asset_ref"], pc["null_ref"]
    uuid = pc["UUID_BASE"] + 0x900 + index * 4

    # the swatches: one row
    count = max(1, len(colours))
    width = 1
    while width < count * SWATCH:
        width *= 2
    pixels = bytearray()
    for y in range(SWATCH):
        for x in range(width):
            c = colours[min(x // SWATCH, count - 1)]
            pixels += bytes((int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), 255))
    d = header(TYPE_TEXTURE, uuid + 1, "T_" + name[3:])
    d += u32(width) + u32(SWATCH) + u32(1) + u32(1)
    d += u32(2) + u32(0) + u32(0)                          # RGBA8, NEAREST, clamp
    d += u8(0) + u8(0) + u8(1) + u8(1) + u8(1)             # no mips, not a target, sRGB, keep uncompressed
    d += bytes(pixels)
    open(os.path.join(ASSETS, "T_" + name[3:] + ".oct"), "wb").write(d)

    d = header(pc["TYPE_MATERIALLITE"], uuid + 2, "M_" + name[3:])
    d += u32(0) + u32(1) + u32(0) + u32(0)                 # no params; LIT; opaque; no vertex colour
    d += u32(1)
    d += asset_ref(uuid + 1, "T_" + name[3:]) + u8(0) + u8(1)
    for _ in range(3):
        d += null_ref() + u8(0) + u8(1)
    for _ in range(2):
        d += f32(0) + f32(0) + f32(1) + f32(1)
    d += f32(1) + f32(1) + f32(1) + f32(1)
    d += f32(1) + f32(0) + f32(0) + f32(0)
    d += f32(1.0) + f32(0.0) + f32(0.30) + f32(specular)   # fresnel power, emission, wrap lighting, specular
    d += u32(2) + f32(1.0) + f32(0.5) + f32(shininess)
    d += i32(0)
    d += u8(0) + u8(0) + u8(1)
    d += u8(0)
    open(os.path.join(ASSETS, "M_" + name[3:] + ".oct"), "wb").write(d)

    mesh.calc_loop_triangles()
    normals = [Vector(n.vector) for n in mesh.corner_normals]
    verts, index_of, idx = [], {}, []
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for tri in mesh.loop_triangles:
        su = (min(tri.material_index, count - 1) + 0.5) * SWATCH / float(width)
        for corner, loop in zip(tri.vertices, tri.loops):
            p = mesh.vertices[corner].co
            n = normals[loop] if tri.use_smooth else Vector(tri.normal)
            key = (round(p.x, 4), round(p.y, 4), round(p.z, 4), round(n.x, 3), round(n.y, 3), round(n.z, 3), su)
            if key not in index_of:
                index_of[key] = len(verts)
                verts.append((to_octave(p), to_octave(n), su))
                for k in range(3):
                    lo[k], hi[k] = min(lo[k], to_octave(p)[k]), max(hi[k], to_octave(p)[k])
            idx.append(index_of[key])
    centre = (lo + hi) * 0.5
    far = max((Vector(v[0]) - centre).length for v in verts)
    d = header(pc["TYPE_STATICMESH"], uuid, name)
    d += u32(len(verts)) + u32(len(idx)) + u32(1)
    d += asset_ref(uuid + 2, "M_" + name[3:])
    d += u8(0) + u8(0)                                     # no triangle collision; NO vertex colour
    for p, n, su in verts:
        d += f32(p[0]) + f32(p[1]) + f32(p[2]) + f32(su) + f32(0.5) + f32(0) + f32(0)
        d += f32(n[0]) + f32(n[1]) + f32(n[2])
    for i in idx:
        d += u32(i)
    d += u8(0) + u32(0)
    d += f32(centre.x) + f32(centre.y) + f32(centre.z) + f32(far)
    open(os.path.join(ASSETS, name + ".oct"), "wb").write(d)
    return len(idx) // 3


def triangles(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    name = "Stage%d_seed%d" % (STAGE, pc["GAUNTLET_SEED"][STAGE])
    data = json.load(open(os.path.join(pc["STAGES"], name + ".json"), encoding="utf-8"))
    palette = stage_palettes.palette(STAGE)
    pc["write_materials"]()

    print("\nGameCube meshes -> %s" % ASSETS)
    pieces = grl.load_pieces()
    piece_path = pc["piece_paths"]()
    colours_of = palette["materials"]
    for i, (piece, p) in enumerate(pieces.items()):
        slots = [m.name.split(".")[0] if m else "" for m in p["mesh"].materials]
        colours = [colours_of.get(n, (1.0, 0.0, 1.0)) for n in slots]
        glossy = [n in pc["GLOSSY_SLOTS"] for n in slots]
        # the pipe's check of two shades, the PC's own pattern (export_to_octave.py's checkers())
        checker = pc["checkers"](STAGE, p["mesh"].name, slots)
        write_mesh("SM_Piece_%s_P%d" % (piece, STAGE), 16 * STAGE + i, p["mesh"], lambda k, c=colours: c[k],
                   material="M_StageMatte", keep_slot=lambda k, g=glossy: not g[k], colour_of_face=checker)
        write_painted_gloss("SM_Piece_%s_Gloss_P%d" % (piece, STAGE), 16 * STAGE + 8 + i, p["mesh"],
                            lambda k, c=colours: c[k], lambda k, g=glossy: g[k], piece_path[piece])
        print("  piece %-12s %5d triangles" % (piece, triangles(p["mesh"])))

    def ring(spin=0.0):
        return simple("Ring", lambda bm: torus(bm, spin=spin))          # the PC's ring: torus() as it stands

    def from_blend(blend, mesh_name):
        with pc["bpy"].data.libraries.load(blend) as (src, dst):
            dst.meshes = [n for n in src.meshes if n == mesh_name]
        return dst.meshes[0]

    write_mesh("SM_Ring", 200, ring(), lambda k: pc["GOLD"], material="M_StageMatte", paint=gold)
    for i in range(RING_SPIN_FRAMES):
        write_mesh("SM_Ring_%02d" % i, 230 + i, ring(math.pi * i / RING_SPIN_FRAMES), lambda k: pc["GOLD"],
                   material="M_StageMatte", paint=gold)
    arch_ring = from_blend(pc["RING_BLEND"], "Ring")
    for i, c in enumerate(__import__("gen_stage").RAINBOW):
        write_mesh("SM_RingRainbow_%d" % i, 210 + i, arch_ring, lambda k, c=c: c, material="M_StageGlow")
    bomb = from_blend(pc["BOMB_BLEND"], "Bomb")
    # (Cutting the bomb to 800 triangles was tried when the build dropped to 52-58 fps. It changed
    # nothing, frame times stayed at 22-27 ms: geometry is not the cost here. The PC's bomb stays.)
    bomb_colours = [tuple(pc["linear_to_srgb"](x) for x in m.diffuse_color[:3]) for m in bomb.materials]
    # LIT, for real: see write_lit_swatched. (Painting the shading on, as the arch spheres have it,
    # was tried first and still read as unlit: a bomb turns with the pipe, and painted light does not.)
    if os.path.exists(pc["BOMB_TEXTURED"]) and os.path.exists(pc["BOMB_LIT"]):
        # THE PC'S TEXTURED BOMB (native/texture_bomb.py): its metal detail and lighting baked into
        # one picture, on a basic lit material, no vertex colours -- written by the PC's own writer,
        # the texture at BOMB_TEX_SIZE (the PC's is 1024).
        # The GameCube's texture is the 256 x 256 the project's owner made from Bomb_lit.png
        # (external/bomb/bomb256.png), used as it is; without it, Bomb_lit.png scaled down.
        own = os.path.join(os.path.dirname(pc["BOMB_LIT"]), "bomb256.png")
        png, size = (own, None) if os.path.exists(own) else (pc["BOMB_LIT"], BOMB_TEX_SIZE)
        pc["write_lit_textured"]("SM_Bomb", 220, from_blend(pc["BOMB_TEXTURED"], "Bomb"), png,
                                 "T_Bomb", "M_Bomb", size=size, basic=pc["BOMB_BASIC_LIT"])
    else:
        write_lit_swatched("SM_Bomb", 0, bomb, bomb_colours)
    write_ball()
    write_mesh("SM_Emerald", 222, simple("Emerald", pc["octahedron"]), lambda k: (0.10, 0.85, 0.95))
    pc["write_shadow"]()            # the drop shadow blob: the PC's, as it is

    # The track and the stage table: exactly what the PC writes, one palette's names.
    paths = piece_path
    chain = pc["ChainPath"]([paths[n] for n in data["pieces"]])
    piece_list = []
    for piece, (start, origin, path) in zip(data["pieces"], chain.parts):
        q = origin.to_quaternion()
        piece_list.append(dict(mesh="SM_Piece_%s_P" % piece, gloss="SM_Piece_%s_Gloss_P" % piece,
                               pos=list(to_octave(origin.translation)), quat=[q.x, q.z, -q.y, q.w],
                               first_frame=start / rm.STEP, last_frame=(start + path.length) / rm.STEP))
    frames = int(math.floor(chain.length / rm.STEP)) + 1
    path_list = []
    for f in range(frames + 1):
        m = chain.frame(min(f * rm.STEP, chain.length))
        path_list.append(list(to_octave(m.translation)) + list(to_octave(m.col[0].xyz)) + list(to_octave(m.col[2].xyz)))
    sections = []
    for sec in data["sections"]:
        sections.append(dict(first_frame=sec["first_frame"], check_frame=sec["check_frame"], last_frame=sec["last_frame"],
                             quota=sec["quota"], asks=sec["asks"], rings=sec["rings"], leads_to=sec["leads_to"],
                             objects=[[o[0], o[1], 1 if o[2] == rm.BOMB else 0] for o in sec["objects"]]))
    arch = data["sections"][0]["ring_check"]["rainbow_arch"]
    table = dict(
        name=name, stage=STAGE, step=rm.STEP, frames=frames, pipe_radius=rm.PIPE_RADIUS, hover=rm.HOVER,
        angle_00_side=-1 if rm.ANGLE_00_SIDE == "right" else 1,
        arch=dict(rings=arch["rings"], reach=rm.PIPE_RADIUS + 1.6, from_deg=12.0, ring_scale=arch["ring_scale"],
                  toward_player=0.72, steps_per_second=arch["steps_per_second"]),
        # the stage's own sky, as on the PC (stage_palettes.py's SKY): all eight are on the disc,
        # streamed (export_assets_gc.py's skies())
        sky=palette["sky"], palette=STAGE,
        palette_skies=[stage_palettes.palette(n)["sky"] for n in sorted(stage_palettes.S2_LINE)],
        pieces=piece_list, sections=sections, path=path_list)
    out = os.path.join(PROJ, "Scripts", "StageData%d.lua" % STAGE)
    open(out, "w", encoding="ascii", newline="\n").write(
        "-- Written by native/export_gc.py from the PC repo's %s.json. Do not edit by hand.\n"
        "StageData%d = %s\n" % (name, STAGE, pc["lua"](table)))
    total = sum(os.path.getsize(os.path.join(ASSETS, f)) for f in os.listdir(ASSETS))
    print("\nstage -> %s (%d pieces, %d frames, %d objects)" % (
        out, len(piece_list), frames, sum(len(x["objects"]) for x in sections)))
    print("assets: %d files, %.2f MB uncooked" % (len(os.listdir(ASSETS)), total / 1048576.0))


main()
