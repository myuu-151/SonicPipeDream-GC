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

    # 1. the stage: track pieces, rings, stage data (stage 1)
    blender -b ../Sonic2Special3D/external/halfpipe/TrackPiecesPack.blend --python native/export_gc.py -- 1

    # 2. everything else: Sonic, sounds, music, the sky   (needs Pillow, numpy, soundfile)
    #    The music and the sky are big and are NOT in git: this step makes them.
    python native/export_assets_gc.py

    # 3. the scripts, from the PC's
    python native/patch_from_pc.py

    # 4. the disc image -> proj/Packaged/GameCube/Sonic2Special3DGC.iso
    #    (PowerShell, devkitPPC on PATH, the octave-libogc repo's ROOT Octave.exe, run from that repo)
    Octave.exe -project <this repo>/proj/Sonic2Special3DGC.octp -headless -build GameCube

Needs the octave-libogc fork at or after "GameCube: a Stream sound leaves its compressed audio
on the disc": without it the music does not fit in memory.

## Where it is

**2026-09-21: stage 1 plays start to emerald in Dolphin at a reported 60 fps.** Not yet run on
hardware. Dolphin does not model the GPU's speed, so that number says the CPU side is fine and
nothing about the console's fill rate or triangle budget.

| Part | State |
|---|---|
| Track, rings, bombs, checks, emerald | In. One palette a stage. A piece is 3,500 to 21,200 triangles; only those within 72 frames ahead are shown. |
| Sonic | In: the PC's 33 meshes as they are (1.7 MB). |
| Sky | The PC's OWN medley: all 384 frames at 512 x 256, STREAMED. `Sky.lua` asks for the next few frames in the background, shows each as it arrives and lets the old ones go, so about half a megabyte is in memory however big the show is (25 MB cooked on the disc). Holding the sky in memory was tried three ways and looked bad or crashed. |
| Music | The PC's two tracks, mono 32 kHz Vorbis, streamed from the disc by the engine. |
| Sound effects | Ring, lose rings, jump, checkpoint, emerald: mono 22 kHz PCM. |
| Light | Stronger sun, lower ambient than the PC: the GX renderer has diffuse light only. |
| UI | NOT YET. One line of text: fps, pieces shown, rings against the quota. |
| Bomb | A PLACEHOLDER sphere: the PC's is 4,000 triangles. |
| Other palettes, marathon | Not yet. |

## Running it in Dolphin

**Use DSP LLE for this game** (Dolphin's `GameSettings/GOCT01.ini`: `[Core]` `DSPHLE = False`).
With DSP HLE the game freezes about 25 seconds in: the CPU ends up spinning in libogc's DSP
interrupt handler (`__dsp_def_taskcb`, waiting for mail that Dolphin's high-level emulation of
the libasnd mixer never sends) once music is playing while the disc is read from a second
thread. LLE, which is how a real console behaves, runs it without trouble. It took a debugger
on the frozen game to find; the symptom looks like anything but audio.

## Controls

Stick or d-pad to steer, A to jump, Start to restart.
