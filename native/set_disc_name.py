"""Give the packaged disc image its name with spaces: "Sonic Pipe Dream".

    python native/set_disc_name.py [path/to/SonicPipeDream.iso]

Octave's packager writes the project's name into the disc header's game-name field (0x20, 0x3E0
bytes), and the project is "SonicPipeDream": that is what Swiss and Dolphin list the game as. The
field is plain text with no checksum, so it is set here after packaging. (The banner, opening.bnr,
carries the same name already: make_banner.py.) Run it after every package build.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = os.path.join(HERE, "..", "proj", "Packaged", "GameCube", "SonicPipeDream.iso")
NAME = "Sonic Pipe Dream"
AT, SIZE = 0x20, 0x3E0


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else ISO
    with open(path, "r+b") as f:
        if f.read(0x20)[:4] != b"GOCT":
            raise SystemExit("%s: not this game's disc image" % path)
        f.seek(AT)
        f.write(NAME.encode("ascii").ljust(SIZE, b"\0"))
    print("%s: named \"%s\"" % (path, NAME))


if __name__ == "__main__":
    main()
