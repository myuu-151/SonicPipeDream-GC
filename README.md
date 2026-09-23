![Sonic Pipe Dream](docs/header.png)

# Sonic Pipe Dream (GameCube)

**A 3D half-pipe racer, born from Sonic 2's special stage -- on a GameCube.**

> **In active development.** Sonic Pipe Dream is a work in progress: stages, controls and the way
> it plays may change from one build to the next, and some features are not there yet.

The GameCube version of [Sonic Pipe Dream](https://github.com/myuu-151/SonicPipeDream). Race
Sonic down a twisting half-pipe that hangs in a sky full of shifting diamonds, grab the rings,
dodge the bombs, and pass all three ring checks to win each stage's chaos emerald.

It is the whole game, on a machine with 24 MB of memory: the same seven stages, the same menus,
skies and music, running at 60 frames a second.

## Features

- **Seven stages**, each with its own track, its own pipe colours, its own sky and its own chaos
  emerald.
- **Run anywhere round the pipe**, wind up speed by holding a direction, leap across to the far
  wall or drop dash straight back down.
- **Eight animated skies**, streamed from the disc as they play.
- **A stage select** with a moving preview of every stage.
- **Save** from the title menu to the memory card in slot A (1 block, with its own icon). After
  that, every emerald you win is saved as you win it.
- **Music** streamed from the disc, and the full set of sound effects.
- **Coming:** Marathon, one endless run that gets harder as it goes.

## Controls

| | Menus | Stage |
|---|---|---|
| Stick or d-pad | Move the highlight | Steer round the pipe |
| A | Choose | Jump; again in the air to drop dash |
| B | Back, on the stage select | |
| Start | Choose | Pause: Continue or Exit |

## Playing it

Download the disc image from [Releases](https://github.com/myuu-151/SonicPipeDream-GC/releases)
(or build it as described in [docs/gamecube-build.md](docs/gamecube-build.md)), then run it in
Dolphin or on a GameCube that can load disc images. It has not yet been tried on real hardware.

**In Dolphin, use DSP LLE** (game settings: `[Core] DSPHLE = False`). With DSP HLE the game
freezes about 25 seconds in; the details are in the build notes.

## More

- [docs/gamecube-build.md](docs/gamecube-build.md): how the port is made from the PC repo, and how to build it.
- [docs/gamecube-fixes.md](docs/gamecube-fixes.md): everything that had to change to run in 24 MB, and why.

Built on the [Octave engine](https://github.com/myuu-151/Octave-libogc).

*A fan game, not affiliated with SEGA. Sonic the Hedgehog is a trademark of SEGA.*
