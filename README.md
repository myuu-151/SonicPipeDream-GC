# Sonic2Special3D-GC

The GameCube build of [Sonic2Special3D](https://github.com/myuu-151/Sonic2Special3D), a 3D take on
Sonic 2's special stage on the Octave engine.

**This repo designs nothing.** The PC repo owns the stage generator, the ring modules, the stage
`.json` files and the source art, and it is free to be as big and open-ended as it likes. This
repo reads those and writes assets cut down for a machine with 24 MB of memory. The only thing
the two share is the stage `.json` format, so nothing done over there can break the build here.

## Layout

Both repos sit side by side:

    testproj/Sonic2Special3D/        the PC repo (source of truth)
    testproj/Sonic2Special3D-GC/     this one

| Path | What it is |
|---|---|
| `native/export_gc.py` | Blender script. Reads a PC stage `.json`, writes GameCube-sized meshes and `StageData<N>.lua` into `proj/`. Reuses the PC's mesh writers without editing them. |
| `native/patch_from_pc.py` | Makes `proj/Scripts/SpecialStage.lua` from the PC's script plus a list of GameCube changes. Gameplay fixes are made on the PC and arrive here by running it again. |
| `proj/` | The Octave project that gets packaged. |

## Build

    # 1. assets and stage data (stage 1)
    blender -b ../Sonic2Special3D/external/halfpipe/TrackPiecesPack.blend --python native/export_gc.py -- 1

    # 2. the gameplay script, from the PC's
    python native/patch_from_pc.py

    # 3. the disc image -> proj/Packaged/GameCube/Sonic2Special3DGC.iso
    #    (PowerShell, devkitPPC on PATH, the octave-libogc repo's ROOT Octave.exe, run from that repo)
    Octave.exe -project <this repo>/proj/Sonic2Special3DGC.octp -headless -build GameCube

## Where it is

**First test (2026-09-21): it runs.** Stage 1, the whole track, rings, bombs, checks and the
emerald, at a reported 60 fps in Dolphin, from an 8.5 MB image. Not yet run on hardware, and
Dolphin does not model the GPU's speed, so that number is a floor for "the CPU side is fine",
not a promise about the console.

What the test leaves out, on purpose, and how each comes back:

| Left out | Plan |
|---|---|
| Sky | The 8-frame "clusters" sky the PC's `gen_s2sky_assets.py` already writes for this machine, with the row gradient added. |
| Sonic | The PC swaps 33 meshes at 42 fps. Fewer frames at a lower rate, or skeletal animation if it is fast enough. For now he is the ball. |
| UI art, font | Without the 4x upscale, compressed. |
| Music, sounds | Streamed from disc. |
| Bomb | The PC's is 4,000 triangles; a placeholder sphere stands in. |
| Other palettes | One palette a stage is loaded. Marathon swaps during its hold loop. |

Track pieces are the heavy part: a straight is 3,500 triangles, a corner 10,600, a drop 21,200.
Only the pieces within 72 frames ahead of the player are shown.

## Controls

Stick or d-pad to steer, A to jump, Start to restart.
