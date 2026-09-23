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
| `native/export_assets_gc.py` | Everything else, from the PC repo: Sonic, sounds, music, the HUD, all eight skies, the emeralds, and the menu art sized for a television. |
| `native/patch_from_pc.py` | Makes the scripts from the PC's (`SpecialStage`, `Sky`, `Menu`, `StageSelect`, the HUD, the music) plus a list of GameCube changes to each. Gameplay fixes are made on the PC and arrive here by running it again. |
| `proj/Scripts/Screens.lua`, `Loading.lua`, `PadInput.lua` | The only scripts written here: how the game gets between the menus and a stage in 24 MB, the loading screen, and the pad. |
| `proj/` | The Octave project that gets packaged. |

## Build

    # 1. the stages: track pieces, rings, stage data, one run a stage (1 to 7), about 40 s each
    for n in 1 2 3 4 5 6 7; do
        blender -b ../Sonic2Special3D/external/halfpipe/TrackPiecesPack.blend --python native/export_gc.py -- $n
    done

    # 2. everything else: Sonic, sounds, music, HUD, skies, emeralds, menus  (needs Pillow, numpy, soundfile)
    #    The music and the skies are big and are NOT in git: this step makes them (1.8 GB of skies).
    #    Name parts to make only those: python native/export_assets_gc.py menu emeralds
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
| HUD | The PC's, whole: SONIC / RINGS, the TOTAL box, START dropping in and scattering, COOL ! and TOO BAD ! with the emblem and glove, in the Sonic font. The art goes in at the size it was drawn (the PC scales it up 4x) and cooks to about 430 KB; the font draws only the glyphs the game prints. Kept 4% clear of the screen's edges for a TV's overscan. One small debug line at the bottom: fps, worst frame, pieces drawn, free memory. |
| Rings, bombs | The PC's own meshes. The bomb is LIT for real (a swatch texture, no vertex colours): a lit material on a vertex-coloured mesh renders unlit on GX. |
| Effects | Ring sparkles, the bomb's explosion, drop shadows: the PC's. |
| Other palettes, marathon | Not yet. |

## Running it in Dolphin

**Use DSP LLE for this game** (Dolphin's `GameSettings/GOCT01.ini`: `[Core]` `DSPHLE = False`).
With DSP HLE the game freezes about 25 seconds in: the CPU ends up spinning in libogc's DSP
interrupt handler (`__dsp_def_taskcb`, waiting for mail that Dolphin's high-level emulation of
the libasnd mixer never sends) once music is playing while the disc is read from a second
thread. LLE, which is how a real console behaves, runs it without trouble. It took a debugger
on the frozen game to find; the symptom looks like anything but audio.

## Controls

| | Menus | Stage |
|---|---|---|
| Stick or d-pad | Move the highlight | Steer round the pipe |
| A | Choose | Jump (again in the air to drop back down) |
| B | Back, on the stage select | |
| Start | Choose | Pause: CONTINUE or EXIT to the stage select |

Emeralds won are saved on the memory card in slot A.
