# What it took to run on a GameCube

The PC game runs on the GameCube with its gameplay untouched: the stage, menu and HUD scripts
are the PC's, made into this repo's by `native/patch_from_pc.py`. Everything below is what had
to change around them -- in this repo, and in the engine
([Octave-libogc](https://github.com/myuu-151/Octave-libogc)) -- and why. Each item says what
went wrong, how it showed, and what fixed it.

The short version: **a GameCube has 24 MB, and the problem was never the total.** It was the
heap being cut into pieces too small to use, the audio and sky being far bigger than memory,
and a handful of engine paths that crashed or hung instead of failing when memory ran out.

## Memory

### The heap cut to pieces (the big one)

**What happened.** Changing stage over and over, a stage's pipe pieces or a new sky's star
frames stopped loading: holes in the track, a sky twinkling between two skies' frames, and
eventually a crash. Measured in Dolphin: 9.7 MB free, but the largest single block 544 KB. At
boot the largest block was 6.5 MB; three stages later it was gone. Every load and unload of
blocks of hundreds of kilobytes left holes that small allocations (Lua tables, nodes, strings)
then moved into.

**What fixed it**, together (a 7.5 minute soak of 20 stage loads then passed with no failure):

- **Compact pipe meshes** (engine 3f75d15d, `Renderer.SetCompactUnlitMeshes`, turned on in
  `Screens.lua`). The pipe and rings are vertex-coloured and unlit, yet each vertex was kept as
  44 bytes (a normal and two sets of texture coordinates nothing draws) and each triangle corner
  as 10 bytes in its display list. They are now read straight into position + colour, 16 bytes
  a vertex and 4 a corner, and the full arrays are never made. A stage's pipe: 4.2 MB -> 1.5 MB.
  Made compact only *after* loading, a pipe piece still needed its full 430 KB array for a
  moment, in one block, and that is what failed -- so it happens as the file is read.
- **Stars refilled in place** (`Texture:ReloadFrom`, engine 3f75d15d; `Sky.lua` via
  `patch_from_pc.py`). Every sky's eight star frames are the same size and format, so a change of
  sky reads the new texels into the buffers already there, a frame a tick behind the loading
  screen. Freeing 4 MB of 512 KB frames and allocating 4 MB more on every stage was the worst
  single source of the holes.
- **Big files read through a small window** (`Stream::ReadFileWindowed`). A mesh or texture used
  to be read whole into one buffer the file's size before being parsed: a 576 KB piece needed a
  576 KB block before it needed anything for itself. Now 32 KB at a time.
- **Display lists in ~60 KB blocks.** A mesh's display list was one block -- 636 KB for a pipe
  piece.
- **A cache for freed big blocks** (`BigBlockCache_Dolphin.cpp`, a link-time wrap of malloc).
  Freed blocks of 32 KB and up are kept and handed to the next allocation of the same size; the
  big allocations a game repeats are the same sizes each time, so they reuse the same blocks and
  small allocations never get into them. Whenever any allocation fails, the cache gives its
  blocks back one by one and the allocation is tried again, so nothing can starve.
- **What every stage shares is loaded once, at boot** (`Screens.lua`, `Sky:ShowMenu`): Sonic,
  the HUD's art, the rings, the bomb, the effects. Loaded first they sit together at the bottom
  of the heap, out of the way.
- **Order of loading** (`Screens.lua`). Behind the loading screen: the menus go first, then the
  new sky's stars load alone, then the stage's biggest pieces, then the rest -- with the sky's
  own streaming held still meanwhile, since its small frames were landing in the big holes.

### The menus and a stage never in memory together

The PC keeps the menu, the stage select and the stage in one world and only hides the ones not
in use. Here they do not fit together, so `Screens.lua` destroys the menus before a stage loads
and tears the stage down (its nodes and its data) before the menus come back.
`Loading.lua` is the screen shown in between. One stage's data table is in memory at a time
(`LoadStageData`, with `Script.Run` rather than `Require`, which reads a file only once).

### The stage select's previews

Each stage's preview is a 16-frame clip; the PC loads all seven (112 pictures, 3.5 MB here).
Only the stage under the cursor has its clip in memory, asked for in the background once the
cursor rests on it.

### The menu art

The PC's menu art is drawn up to 4x and kept uncompressed: several textures are 2048 wide, more
than the GameCube's GPU takes at all (1024), and megabytes in total. `export_assets_gc.py` cooks
every piece at 1.25 art pixels a mockup pixel (the TV shows the mockup at about 1.23) and leaves
it to the console's compressed formats. The layout table carries each texture's real size, so
the layout is the PC's.

### The sky

The PC's diamond show is 384 frames, 25 MB cooked. Here it is streamed: the next few frames are
asked for in the background, each shown as it arrives and let go after (`Sky.lua`, via
`patch_from_pc.py`). About half a megabyte at a time. Holding it whole was tried three ways --
half size, a quarter of the frames, 6 MB of it -- and looked bad or crashed.

### The music

The PC's two tracks are 46 MB of PCM, twice the machine's memory. Here they are stereo Vorbis
with the engine's Stream flag, and the engine leaves a Stream sound's audio **on the disc** and
decodes it a slice a frame (engine 72775dbe, ab288d50).

### Smaller savings

- Bullet's physics pools reserved about 4 MB up front for 4,096 manifolds; 256 now, growing if
  needed (engine 44aed8e9).
- The emeralds' textures go through the compressed cook (64 KB a gem, not 512 KB).

## Crashes and hangs that were really out-of-memory

Each of these took the whole game down for one failed allocation. They now fail the one load
and carry on (the loading screen waits up to 30 seconds for anything that never arrives):

- **An allocation that threw on the background loader** had nothing to catch it, and the
  unwinder never returned: a silent freeze (engine 44aed8e9).
- **A file that could not be read** was parsed anyway, through a null pointer (engine 6fbc9d4e).
  On the disc, "Failed to open file" in the log means the *read buffer* could not be allocated,
  not a disc error.
- **A mesh's vertex array** came back null from malloc and was written through: a DSI (a
  crash) loading a pipe piece (engine a2dbbbe7). It now throws like `new`, which the loader
  turns into a failed load; a display list that cannot be allocated is skipped when drawing.
- **A background load that found its asset already loaded another way** dropped the request
  without telling the handles waiting on it: they waited for ever, and the loading screen with
  them. It now hands them the loaded asset and frees its duplicate (engine 3f75d15d).

## Frame rate on hardware (2026-09-24)

About 28 fps with stutter at first; 55-60 fps after, measured each step from the SD perf log
(a log build: `IsoLog_local.h` in the engine, `GcTest.perf` for the stage's parts):

- **Music hitches (83-117 ms):** a 16 KB music read on the main thread queued behind the sky's
  64 KB frames on the SD lock. The engine reads music ahead on its own thread now, and the asset
  loader runs below the main thread.
- **The GPU (the 28 fps):** meshes are sent as triangle strips (about 1.4 vertices a triangle, not
  3), and the CPU works on the next frame while the GPU draws this one. The GPU is no longer the limit.
- **Every five seconds:** the perf log's own SD write. Now written by a background thread.
- **The sky (30-40 ms now and then):** a full `collectgarbage()` every few streamed frames. Frames
  are released at once now (`asset:Release()`, the sky's patch in `patch_from_pc.py`).
- **The trace tube and ring sparkles:** tables made every frame for every ring and sparkle (up to
  ~16 KB of garbage a frame). The PC's `TraceMesh` and `UpdateFx` use plain numbers now
  (`PlaceXYZ`, `SetWorldPositionXYZ`), proved identical to the old code in a side-by-side run.

## Other GameCube differences

- **The pad** (`PadInput.lua`): the PC scripts only ask about keys, so the pad is folded into
  them -- A is Enter/Space, B is Backspace, Start is Escape in a stage and Enter on the menus.
  Steering reads the stick directly. A GameCube stick reads only about 0.7 at full push (the
  engine divides by 127; sticks top out near 100), so full steering -- and the momentum that
  builds only at full steering -- starts at 0.55 of the stick's travel.
- **Only the track near Sonic is drawn**: a piece is up to 21,000 triangles, so pieces more than
  72 frames ahead or 12 behind are hidden rather than left to the renderer to cull.
- **A lit material on a vertex-coloured mesh renders unlit** on the GameCube's renderer, so the
  bomb is coloured by a tiny texture of swatches instead of vertex colours.
- **The GameCube renderer has no specular highlight**, so the arch spheres' gloss is painted into
  their vertices by `export_gc.py`.
- **The HUD** keeps 4% clear of the screen's edges, for a TV's overscan.
- **Saves** go to the memory card in slot A, only once the player has chosen SAVE on the title
  menu. The engine's save writer gained a comment and an icon (`System.SetSaveInfo`), a check of
  the card before writing (`System.GetSaveCard`: no card, full, blocks needed and free), and no
  longer leaks its 40 KB work area each time it finds no card.
- **The disc banner** is `native/banner.png`, made into `proj/opening.bnr` by
  `native/make_banner.py`.

## Dolphin

- **Use DSP LLE.** With DSP HLE the game freezes about 25 seconds in, once music plays while the
  disc is read from a second thread: the CPU ends up waiting in libogc's DSP interrupt handler for
  mail that Dolphin's high-level audio emulation never sends. LLE, which behaves as a real console
  does, runs it without trouble. (Found by attaching a debugger to the frozen game.)
- **Testing without a pad**: `proj/Scripts/GcTest.lua` holds switches for Dolphin test builds --
  choose a stage by itself, leave after a set time, show free memory. Keys sent to Dolphin can
  land in another window, so tests do not press anything. They must be off (`GcTest = {}`) in
  anything committed.
