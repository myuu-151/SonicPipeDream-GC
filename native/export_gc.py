"""Export a stage for the GAMECUBE build, out of the PC repo's stage data.

    blender -b ../Sonic2Special3D/external/halfpipe/TrackPiecesPack.blend \\
        --python native/export_gc.py -- [stage 1-7]

This repo designs nothing. The PC repo (a sibling folder, ../Sonic2Special3D) owns the stage
generator, the stage .json files and the source art; this script READS them and writes assets
cut down for a machine with 24 MB of memory:

    proj/Assets/Stage/SM_Piece_<Name>[_Gloss]_P<N>.oct   the track pieces in ONE palette, the stage's
    proj/Assets/Stage/SM_Ring.oct, SM_Ring_00..05.oct    a low-poly ring, 6 spin frames (the PC has 12)
    proj/Assets/Stage/SM_RingRainbow_0..8.oct            the same low-poly ring, in the arch's colours
    proj/Assets/Stage/SM_Bomb.oct                        a PLACEHOLDER: the PC's bomb is 4000 triangles
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

RING_AROUND, RING_ACROSS = 14, 6    # the PC's ring is 36 x 16: 1152 triangles. This is 168.
RING_SPIN_FRAMES = 6                # SpecialStage.lua's RING_SPIN_FRAMES must say the same

source = open(PC_EXPORTER, encoding="utf-8").read()
source = source[:source.rindex("\nmain()")]
pc = {"__name__": "pc_export", "__file__": PC_EXPORTER}
exec(compile(source, PC_EXPORTER, "exec"), pc)
pc["PROJ"], pc["ASSETS"] = PROJ, ASSETS

bmesh, grl, rm, stage_palettes = pc["bmesh"], pc["grl"], pc["rm"], pc["stage_palettes"]
write_mesh, simple, torus, gold, to_octave = pc["write_mesh"], pc["simple"], pc["torus"], pc["gold"], pc["to_octave"]
STAGE = pc["STAGE"]


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
    colours_of = palette["materials"]
    for i, (piece, p) in enumerate(pieces.items()):
        slots = [m.name.split(".")[0] if m else "" for m in p["mesh"].materials]
        colours = [colours_of.get(n, (1.0, 0.0, 1.0)) for n in slots]
        glossy = [n in pc["GLOSSY_SLOTS"] for n in slots]
        write_mesh("SM_Piece_%s_P%d" % (piece, STAGE), 16 * STAGE + i, p["mesh"], lambda k, c=colours: c[k],
                   material="M_StageMatte", keep_slot=lambda k, g=glossy: not g[k])
        write_mesh("SM_Piece_%s_Gloss_P%d" % (piece, STAGE), 16 * STAGE + 8 + i, p["mesh"],
                   lambda k, c=colours: c[k], material="M_StageGloss", keep_slot=lambda k, g=glossy: g[k])
        print("  piece %-12s %5d triangles" % (piece, triangles(p["mesh"])))

    def ring(spin=0.0):
        return simple("Ring", lambda bm: torus(bm, around=RING_AROUND, across=RING_ACROSS, spin=spin))

    write_mesh("SM_Ring", 200, ring(), lambda k: pc["GOLD"], material="M_StageMatte", paint=gold)
    for i in range(RING_SPIN_FRAMES):
        write_mesh("SM_Ring_%02d" % i, 230 + i, ring(math.pi * i / RING_SPIN_FRAMES), lambda k: pc["GOLD"],
                   material="M_StageMatte", paint=gold)
    for i, c in enumerate(pc["RAINBOW"] if "RAINBOW" in pc else __import__("gen_stage").RAINBOW):
        write_mesh("SM_RingRainbow_%d" % i, 210 + i, ring(), lambda k, c=c: c, material="M_StageGlow")
    write_mesh("SM_Bomb", 220, simple("Bomb", lambda bm: bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.5)),
               lambda k: (0.80, 0.08, 0.10))
    write_mesh("SM_PlayerBall", 221, simple("Ball", lambda bm: bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.7)),
               lambda k: (0.12, 0.30, 0.95))
    write_mesh("SM_Emerald", 222, simple("Emerald", pc["octahedron"]), lambda k: (0.10, 0.85, 0.95))

    # The track and the stage table: exactly what the PC writes, one palette's names.
    paths = pc["piece_paths"]()
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
        sky=0, palette=STAGE, palette_skies=[0] * 7, pieces=piece_list, sections=sections, path=path_list)
    out = os.path.join(PROJ, "Scripts", "StageData%d.lua" % STAGE)
    open(out, "w", encoding="ascii", newline="\n").write(
        "-- Written by native/export_gc.py from the PC repo's %s.json. Do not edit by hand.\n"
        "StageData%d = %s\n" % (name, STAGE, pc["lua"](table)))
    total = sum(os.path.getsize(os.path.join(ASSETS, f)) for f in os.listdir(ASSETS))
    print("\nstage -> %s (%d pieces, %d frames, %d objects)" % (
        out, len(piece_list), frames, sum(len(x["objects"]) for x in sections)))
    print("assets: %d files, %.2f MB uncooked" % (len(os.listdir(ASSETS)), total / 1048576.0))


main()
