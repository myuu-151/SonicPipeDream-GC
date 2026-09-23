# The GameCube build

How this port is made from the PC repo, how to build the disc image, and why it is shaped the way it is.
Everything that had to change to run on the console is in [gamecube-fixes.md](gamecube-fixes.md).

The GameCube build of [Sonic Pipe Dream](https://github.com/myuu-151/SonicPipeDream), a 3D half-pipe racer born from
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

**2026-09-23: the whole game -- menu, stage select, all seven stages, pause, emeralds saved to the
memory card -- plays in Dolphin at about 60 fps.** A test build cycled every stage in and out for
seven and a half minutes (twenty loads) with no failed load. Not yet run on hardware. Dolphin does
not model the GPU's speed, so that number says the CPU side is fine and nothing about the
console's fill rate or triangle budget.

MEMORY IS THE WHOLE STORY HERE. A stage, its sky and the menus do not fit together, and even one
at a time, changing stage over and over used to cut the heap into pieces too small for a pipe
piece or a star frame. What keeps it working (see Screens.lua, and the engine at or after
"Consoles: stages that load forever"):

- the menus and a stage are never in memory together: the loading screen is between them
- the pipe and rings are kept as position and colour only (`Renderer.SetCompactUnlitMeshes`): a
  stage's pipe is 1.5 MB, not 4.2
- a change of sky refills the same eight star textures in place (`Texture:ReloadFrom`)
- Sonic, the HUD and the rings are loaded once, at boot, and kept
- the engine reads big assets through a small window, builds display lists in small blocks, and
  keeps freed big blocks for reuse (BigBlockCache_Dolphin.cpp)

| Part | State |
|---|---|
| Stages | All seven, each in its own palette with the PC's checkered pipe, under its own sky, with its own chaos emerald. A piece is 3,500 to 21,200 triangles; only those within 72 frames ahead are shown. |
| Menus | The PC's menu and stage select, the art sized for a TV (1.25 art pixels a mockup pixel, compressed). The select's preview clip plays for the stage under the cursor only. Menu sounds. |
| Loading screen | GameCube only (Loading.lua): the stage, its emerald's colour (faint until won) and NOW LOADING, between the stage select and a stage, and back. |
| Pause | The PC's: Start, then CONTINUE or EXIT to the stage select. |
| Sonic | In: the PC's 33 meshes as they are (1.7 MB). |
| Sky | All eight of the PC's skies (the menu's is Noir). The medley: all 384 frames at 512 x 256, STREAMED. `Sky.lua` asks for the next few frames in the background, shows each as it arrives and lets the old ones go, so about half a megabyte is in memory however big the show is (25 MB cooked on the disc). Holding the sky in memory was tried three ways and looked bad or crashed. |
| Music | The PC's two tracks, mono 32 kHz Vorbis, streamed from the disc by the engine. |
| Sound effects | Ring, lose rings, jump, checkpoint, emerald, fail, explosion, exit, and the menus' three: mono 22 kHz PCM. |
| Light | Stronger sun, lower ambient than the PC: the GX renderer has diffuse light only. |
| HUD | The PC's, whole: SONIC / RINGS, the TOTAL box, START dropping in and scattering, COOL ! and TOO BAD ! with the emblem and glove, in the Sonic font. The art goes in at the size it was drawn (the PC scales it up 4x) and cooks to about 430 KB; the font draws only the glyphs the game prints. Kept 4% clear of the screen's edges for a TV's overscan. One small debug line at the bottom: fps, worst frame, pieces drawn, free memory. |
| Rings, bombs | The PC's own meshes. The bomb is LIT for real (a swatch texture, no vertex colours): a lit material on a vertex-coloured mesh renders unlit on GX. |
| Effects | Ring sparkles, the bomb's explosion, drop shadows: the PC's. |
| Marathon | Not yet (nor on the PC). |

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

**Saving.** SAVE, the title menu's fifth item (the GameCube's own), opens `SavePrompt.lua`: what
is in slot A -- no card, not a memory card, damaged or unformatted, another region's, FULL, or
ready -- with the blocks the save needs (1) and the blocks free. A saves. Nothing is written to a
card until the player has saved there once; after that each emerald won is saved into the file
(`StageSelect:SaveWon`, patched by `patch_from_pc.py`). The save carries a title, a description
and a 32 x 32 icon for the card's own screen: `native/save_icon.png`, made into
`proj/Scripts/SaveInfo.lua` by `native/make_save_icon.py`. In the file the 64-byte comment comes
first, then the icon, then the emeralds: libogc only takes an icon that starts in a file's first
512 bytes.
