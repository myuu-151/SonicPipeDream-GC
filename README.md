![Sonic Pipe Dream](docs/header.png)

# Sonic Pipe Dream (GameCube)

**Sonic 2's special stages, rebuilt in 3D -- on a GameCube.**

> **In active development.** Sonic Pipe Dream is a work in progress: stages, controls and the way
> it plays may change from one build to the next, and some features are not there yet.

The GameCube version of [Sonic Pipe Dream](https://github.com/myuu-151/SonicPipeDream). Race
Sonic down a twisting half-pipe that hangs in a sky full of shifting diamonds, grab the rings,
dodge the bombs, and pass all three ring checks to win each stage's chaos emerald.

It is the whole game, on a machine with 24 MB of memory: the same seven stages laid out from
Sonic 2's own, the same menus, skies and music, running at 60 frames a second.

## Features

- **Seven special stages**, each with its own pipe colours, its own sky and its own chaos
  emerald.
- **Run anywhere round the pipe**, wind up speed by holding a direction, jump across to the far
  wall or drop dash straight back down.
- **Eight animated skies**, streamed from the disc as they play.
- **A stage select** with a moving preview of every stage; emeralds you win are saved to the
  memory card in slot A.
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
Dolphin or on a GameCube that can load disc images. It has not yet been tried on real
hardware.

**In Dolphin, use DSP LLE** (game settings: `[Core] DSPHLE = False`). With DSP HLE the game
freezes about 25 seconds in; the details are in the build notes.

## More

How the port is made, how to build it, and how it fits in 24 MB: [docs/gamecube-build.md](docs/gamecube-build.md).

Built on the [Octave engine](https://github.com/myuu-151/Octave-libogc).

*A fan game, not affiliated with SEGA. Sonic the Hedgehog is a trademark of SEGA.*
