# GameCube memory

Notes from the difficulty-7 crash hunt (2026-09-24). This covers what fills memory during a run,
what actually went wrong, what fixed it, and what bigger GameCube games do that this build does
not do yet.

## The symptoms

At starting difficulty 7, in a marathon or time attack:

- the game quit ("Lua Error: not enough memory") while the second zone was being built
- or it kept running, but the sky's diamonds flickered, then pipe geometry stopped appearing
- with MMU off in Dolphin, a separate libvorbis bug wrote through a null pointer when a decode
  buffer could not be allocated. That one is fixed in the engine (`4c8dc7b9`)

## What is in memory during a run

Measured with `System.MemoryCensus` (engine, test builds only; `GcTest.census = seconds` logs it)
in a difficulty-7 time attack:

| What | Size |
|---|---|
| Sky star frames: 8 × 1024×1024 CMPR, kept at full size by choice | 4.0 MB |
| Pipe pieces: 5 shapes × pipe + gloss, one palette | ~1.7 MB |
| Other meshes (Sonic, rings, arch, sky dome, …) | ~2.7 MB |
| Lua: the marathon kit (~0.6 MB), the zones, the scripts | 2.2–3.0 MB |
| HUD font `F_SonicUI` | 512 KB, now 256 KB |
| Sound effects, decoded PCM, all kept loaded | ~620 KB |
| Bomb mesh + texture | 280 KB, now ~105 KB |
| Engine fonts (Roboto32, RobotoMono16) | 170 KB |
| Sky diamond frames in the stream window | ~6 × 64 KB |

Also in the 24 MB: the game's code (`.dol`, ~3.9 MB), framebuffers, the GX FIFO and audio buffers.

## What actually went wrong: fragmentation, not size

3 MB of Lua is not too much in itself. The allocation log showed failures with **1.3–1.7 MB free**:

- a 5 KB `malloc` failed, then 31 KB ones, then the sky's 64 KB frames (250 failures in 3 minutes)
- the free memory was all there, but in pieces smaller than any of those requests

The cause is how the heap is used:

- One heap serves everything: Lua, textures, meshes, the engine.
- Building one difficulty-7 zone creates about **10 MB of short-lived Lua tables**. Difficulty-7
  zones are about 1.5× the size of difficulty-2 zones (≈3000 path frames and 1500 rings/bombs
  each).
- newlib's allocator cannot move blocks. So each zone build leaves small live allocations scattered
  across the free space. Once a big block is freed, small ones land in it and it is gone for good.
- The engine's `BigBlockCache` keeps freed blocks of 32 KB and up for reuse. But it hands them
  back to the heap whenever any allocation fails, and there Lua's small allocations cut them up.

## What fixed it

| Change | Where | Effect |
|---|---|---|
| **Pinned blocks** for the sky's 64 KB frames: kept for the next frame, never given back (at most 8) | engine `BigBlockCache_Dolphin.cpp`, `System.PinBlocks`; `Screens.lua` pins `SKY_FRAME_BYTES` at boot | sky-frame failures 250 → 0 |
| A growing Lua array can take a kept block of its new size | `BigBlockCache_Dolphin.cpp` `__wrap_realloc` | no failed 64 KB `realloc` |
| **Zones are no longer copied** when they join the run: the generator's own path and object tables are moved into place | PC `SpecialStage.lua` `JoinZone` | Lua ~3.0 → ~2.2 MB, far less garbage |
| Bomb: the owner's texture at 128×128 on a 1500-triangle mesh (from 4000) | `native/export_gc.py` (`BOMB_TEX_SIZE`, `BOMB_TRIANGLES`, `decimated`) | 280 KB → ~105 KB |
| HUD font atlas as RGB5A3 (16 bpp) instead of RGBA8 | `native/export_assets_gc.py` `hud()` | 512 → 256 KB, same look |
| On-screen readout only with `GcTest.readout` | `native/patch_from_pc.py` | no text rebuilt twice a second |
| Time attack clock shows M:SS | PC `SpecialStage.lua` `FormatClock` | its text changes once a second, not every frame |

Result: 3-minute difficulty-7 time attacks in Dolphin with no allocation failures, and 1.2–1.8 MB
free throughout.

Tried and rejected: star frames at half size (512×512) would have saved 3 MB, but they looked bad.
The stars stay at 1024.

## How bigger GameCube games manage much more

They are not given more memory; they manage it differently.

1. **ARAM.** The GameCube has 16 MB of auxiliary RAM besides the 24 MB main RAM. Games keep sound
   banks there, and the DSP plays them straight from ARAM. Many also stage streamed data there and
   DMA it into main RAM when needed. **This build uses none of it.**
2. **Fixed pools, not one shared heap.** A general `malloc` is rarely used during gameplay:
   - each level or area gets its own region, wiped all at once when it ends
   - particles, sounds, textures and so on get fixed-size pools

   Nothing small can land between big blocks, so nothing fragments.
3. **No garbage-collected scripting doing heavy work.** Generation and gameplay data live in
   compiled code, writing into preallocated buffers. No 10 MB of garbage per zone.
4. **Data prepared offline, streamed into fixed slots.** Assets arrive into reserved slots, not
   `malloc`/`free` per item. The sky's pinned frames are a small version of this.

## Where this build could go next

In order of payoff, if more content ever needs more headroom:

1. **A dedicated Lua memory pool.** A fixed region of a few MB with its own allocator (TLSF, or a
   dlmalloc mspace), passed to Lua through `lua_newstate`. Lua's small tables could then never
   fragment the memory textures and meshes need, and a Lua out-of-memory would stay inside Lua.
   A moderate engine change; the biggest structural win.
2. **Sound effects in ARAM.** About 620 KB of main RAM back. libasnd plays from main RAM, so this
   means DSP playback from ARAM, or an ARAM cache with a small main-RAM staging buffer.
3. **Music stream buffers in ARAM:** smaller, but the same idea.
4. **The marathon generator in C++,** writing zones into a preallocated buffer: no Lua garbage per
   zone at all. The largest job, and it would need keeping in step with the PC's Lua generator.
5. **Engine fonts:** Roboto32 is the `Text` widget's default and stays loaded (85 KB). The game
   sets its own font everywhere, so the engine could skip loading it on the GameCube.

## Tools

- `System.MemoryCensus([top])`: logs every loaded asset's size (textures, meshes, sounds, fonts),
  totals by type, Lua's share and the free heap. It needs a log build: `OCT_DOLPHIN_EMU_LOG 1` in
  `System_Dolphin.cpp`, `Logging=1` in `proj/Config.ini`, OSREPORT on in Dolphin's `Logger.ini`.
  Revert all three before any hardware build.
  - Its "largest block" figure is not reliable, so don't trust it.
- `GcTest` switches for this kind of testing:
  - `marathon`, `timeAttack`, `autoplay`: a run that plays itself
  - `start = 1-7`: starting difficulty
  - `lives`
  - `census = seconds`
  - `readout`
- To find which allocation fails, add a temporary report where `__wrap_malloc` / `__wrap_realloc`
  give up in `BigBlockCache_Dolphin.cpp`. Use `SYS_Report` in Dolphin only: it corrupts the RTC
  counter on hardware.
- A PC in a Dolphin "Invalid read/write" message maps to a function with
  `powerpc-eabi-addr2line -f -C -e Standalone/Build/GCN/Octave.elf <pc>`.
