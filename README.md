![Sonic Pipe Dream](docs/header.png)

# Sonic Pipe Dream (GameCube)

**A modern take on Sonic 2's iconic half-pipe special stage, in full 3D for the Nintendo GameCube.**

> **In active development.** Sonic Pipe Dream is a work in progress: stages, controls and the way
> it plays may change from one build to the next, and some features are not there yet.
>
> Found a bug? Please report it as a ticket on the
> [Issues page](https://github.com/myuu-151/SonicPipeDream-GC/issues): what happened, what you expected,
> and how to make it happen again if you can.

The GameCube version of [Sonic Pipe Dream](https://github.com/myuu-151/SonicPipeDream).

## Features

- **Seven stages**, each with its own track, its own pipe colours, its own sky, its own music and
  its own chaos emerald.
- **Marathon**: one run made as you play it, a new one every time, built on the console while you
  run. Zone after zone, it gets harder as it goes, and after every zone the pipe and the sky change
  colour while Sonic takes a victory lap. Play 1 to 20 zones or go on without end, and choose how
  hard it starts, how fast it climbs and how many spare rings it gives you.
- **Time Attack**: the marathon against a clock that counts down. Every check passed puts time
  back. Rings only save you from a hit, and a hit takes them all; with no rings, a hit costs a life.
- **Run anywhere round the pipe**, wind up speed by holding a direction, leap across to the far
  wall, drop dash straight back down, or hold jump through a landing to bounce highest.
- **Spin dash.** Curl up and skid to a stop, rev, and let go to blast off down the pipe.
- **Eight animated skies**, streamed from the disc as they play.
- **A stage select** with a moving preview of every stage.
- **Save and Load** from the title menu, to the memory card in slot A (2 blocks, with its own
  banner and an icon whose emerald cycles through all seven colours). After the first save, every emerald you win is saved as you win it.
- **Music** streamed from the disc, the full set of sound effects, and **Options** to turn off the
  music in the stages.

## Controls

| | Menus | Stage |
|---|---|---|
| Stick or d-pad | Move the highlight | Steer round the pipe |
| A | Choose | Jump; again in the air to drop dash; hold through a landing to bounce highest |
| R (hold) | | Spin dash: skid to a stop, press A to rev, let go of R to blast off |
| B | Back | |
| Start | Choose | Pause: Continue or Exit |

## Playing it

Download the disc image from [Releases](https://github.com/myuu-151/SonicPipeDream-GC/releases)
(or build it as described in [docs/gamecube-build.md](docs/gamecube-build.md)), then run it in
Dolphin or on a GameCube that can load disc images. On a real GameCube it is played from an SD
card (the image on the card, loaded through Swiss); an SD adapter that supports DMA reads it
fastest.

**In Dolphin**, set two things in the game's properties:
- **Untick Emulate Disc Speed** (`[Core] FastDiscSpeed = True`). The game streams its sky and
  music from the disc all the time, and at emulated drive speed that slows it down.
- **Use DSP LLE** (`[Core] DSPHLE = False`). With DSP HLE the game freezes about 25 seconds in;
  the details are in the build notes.

## More

- [docs/gamecube-build.md](docs/gamecube-build.md): how the port is made from the PC repo, and how to build it.
- [docs/gamecube-fixes.md](docs/gamecube-fixes.md): everything that had to change to run in 24 MB, and why, and what took it from 28 to 55-60 frames a second on hardware.
- [docs/gamecube-memory.md](docs/gamecube-memory.md): what fills memory in a run, the difficulty-7 fragmentation hunt, and what bigger GameCube games do differently.

## Credits

- **Music**: megabaz
- **Sonic model**: murissargb
- **Lives icon**: eris1521987

Built on the [Octave engine](https://github.com/myuu-151/Octave-libogc).

*A fan game, not affiliated with SEGA. Sonic the Hedgehog is a trademark of SEGA.*
