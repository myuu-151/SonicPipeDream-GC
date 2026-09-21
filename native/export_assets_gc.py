"""Everything but the stage itself, for the GameCube: Sonic, the sounds and the sky.

    python native/export_assets_gc.py        (needs Pillow, numpy and soundfile)

All of it comes out of the PC repo (../Sonic2Special3D); nothing is designed here.

SONIC      proj/Assets/Sonic/ is copied as it is. It looked like the expensive part -- 33 meshes,
           one for every frame of his animation -- and it is 1.7 MB. It fits.

SOUNDS     The PC keeps its two music tracks as raw PCM: 46 MB, twice this machine's memory.
           Here they are Ogg Vorbis with the asset's STREAM flag set, which the engine's GameCube
           audio decodes a little at a time as it plays: a track then costs its compressed size.
           Mono, 32 kHz. The effects stay raw PCM (they must start the instant they are asked
           for) but go down to mono 22 kHz, which takes them from 2 MB to about half a megabyte.

SKY        The PC's classic sky is a 384-frame show of diamond patterns, about 200 MB. It is THAT
           sky here too, cut to fit: every second frame, at half the size -- 192 frames of
           256 x 128, about 3 MB once cooked. See sky().
"""

import io
import os
import shutil
import struct
import sys

import numpy
import soundfile

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.abspath(os.path.join(HERE, "..", "..", "Sonic2Special3D"))
PROJ = os.path.abspath(os.path.join(HERE, "..", "proj"))

MAGIC, VERSION, TYPE_SOUNDWAVE = 0x4F435421, 14, 0x9A6A5AC0
MUSIC_RATE, MUSIC_QUALITY = 32000, 0.35
EFFECT_RATE = 22050

# file in the PC's external/audio, asset name, uuid: the names and uuids are the PC's, so the
# scripts find the same assets on both machines
MUSIC = [("ss_intro.wav", "SW_SpecialStage_Intro", 0x51C0FFEE00300001),
         ("ss_loop.wav", "SW_SpecialStage_Loop", 0x51C0FFEE00300002)]
EFFECTS = [("Ring.wav", "SW_Ring", 0x51C0FFEE00300010), ("LoseRings.ogg", "SW_LoseRings", 0x51C0FFEE00300011),
           ("Jump.ogg", "SW_Jump", 0x51C0FFEE00300012), ("Checkpoint.wav", "SW_Checkpoint", 0x51C0FFEE00300013),
           ("Get_Emerald.wav", "SW_GetEmerald", 0x51C0FFEE00300014)]
NORMALISE = {"SW_GetEmerald": 0.97}         # as the PC does: that file is quiet


def mono_at(path, rate):
    data, src_rate = soundfile.read(path, dtype="float64", always_2d=True)
    mono = data.mean(axis=1)
    if src_rate != rate:
        # a gentle low-pass first (a moving average as wide as the step), then straight-line
        # resampling: plenty for a TV speaker, and it needs nothing beyond numpy
        width = max(1, int(round(src_rate / float(rate))))
        if width > 1:
            mono = numpy.convolve(mono, numpy.ones(width) / width, mode="same")
        n = int(len(mono) * rate / float(src_rate))
        mono = numpy.interp(numpy.arange(n) * (src_rate / float(rate)), numpy.arange(len(mono)), mono)
    return mono


def sound_header(asset, uuid, stream, channels, rate, frames):
    name = asset.encode("ascii")
    d = struct.pack("<IIIB", MAGIC, VERSION, TYPE_SOUNDWAVE, 0)
    d += struct.pack("<Q", uuid) + struct.pack("<I", len(name)) + name
    d += struct.pack("<ff", 1.0, 1.0) + struct.pack("<b", 0)
    d += struct.pack("<???", stream, stream, stream)        # compress, compress internal, STREAM
    d += struct.pack("<IIIIII", channels, 16, rate, frames, channels * 2, rate * channels * 2)
    return d


def sounds():
    out = os.path.join(PROJ, "Assets", "Sounds")
    os.makedirs(out, exist_ok=True)
    src = os.path.join(PC, "external", "audio")
    total = 0
    for file_name, asset, uuid in MUSIC:
        mono = mono_at(os.path.join(src, file_name), MUSIC_RATE)
        if os.environ.get("GC_MUSIC_SECONDS"):                 # a test: is a hang or a silence about SIZE?
            mono = mono[:int(float(os.environ["GC_MUSIC_SECONDS"]) * MUSIC_RATE)]
        # RAW PCM here, with the COMPRESS and STREAM flags set: the engine's own cook then encodes
        # the Vorbis for the console. A track encoded here (libsndfile) and handed over ready-made
        # hung the GameCube at the loading screen; the engine's encoder is the one its streaming
        # decoder was written against. These two source files are big (17 MB each) and are not
        # committed: this script remakes them from the PC repo's WAVs.
        pcm = numpy.clip(mono * 32767.0, -32768, 32767).astype("<i2").tobytes()
        name = asset.encode("ascii")
        d = struct.pack("<IIIB", MAGIC, VERSION, TYPE_SOUNDWAVE, 0)
        d += struct.pack("<Q", uuid) + struct.pack("<I", len(name)) + name
        d += struct.pack("<ff", 1.0, 1.0) + struct.pack("<b", 0)
        d += struct.pack("<???", True, False, True)             # compress (at cook), not internally, STREAM
        d += struct.pack("<IIIIII", 1, 16, MUSIC_RATE, len(mono), 2, MUSIC_RATE * 2)
        d += struct.pack("<?", False) + struct.pack("<I", len(pcm)) + pcm
        open(os.path.join(out, asset + ".oct"), "wb").write(d)
        total += len(d)
        print("  %-24s PCM to be cooked to streamed Vorbis, %.1f s, %.2f MB" % (asset, len(mono) / float(MUSIC_RATE), len(d) / 1048576.0))
    for file_name, asset, uuid in EFFECTS:
        mono = mono_at(os.path.join(src, file_name), EFFECT_RATE)
        if asset in NORMALISE:
            mono = mono * (NORMALISE[asset] / max(1e-9, numpy.abs(mono).max()))
        pcm = numpy.clip(mono * 32767.0, -32768, 32767).astype("<i2").tobytes()
        d = sound_header(asset, uuid, False, 1, EFFECT_RATE, len(mono))
        d += struct.pack("<?", False) + struct.pack("<I", len(pcm)) + pcm
        open(os.path.join(out, asset + ".oct"), "wb").write(d)
        total += len(d)
        print("  %-24s PCM, %.2f s, %d KB" % (asset, len(mono) / float(EFFECT_RATE), len(d) // 1024))
    print("sounds: %.2f MB" % (total / 1048576.0))


def sonic():
    src, dst = os.path.join(PC, "proj", "Assets", "Sonic"), os.path.join(PROJ, "Assets", "Sonic")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    size = sum(os.path.getsize(os.path.join(dst, f)) for f in os.listdir(dst))
    print("Sonic: %d files, %.2f MB" % (len(os.listdir(dst)), size / 1048576.0))


SKY_EVERY = 2                       # keep every Nth frame of the PC's 384: 192 frames. Sky.lua is told the same
SKY_SHRINK = 2                      # and halve them: 256 x 128. Cooked, a frame is 16 KB, so 3 MB in all.
# TRIED AND REJECTED (2026-09-21): every fourth frame at the full 512 x 256. Sharper, but 96 frames
# is too few to read as motion, and its 6 MB crashed the console: the sky has about 3 MB to live
# in. The size must be a power of two (the texture repeats, and GX only repeats those), so there
# is no in-between size to try. Sharper than this means NOT HOLDING EVERY FRAME IN MEMORY.


def sky():
    """THE PC'S OWN SKY: the 384-frame medley of diamond patterns, row gradient and all -- not the
    8-frame clusters sky its generator can also write, which the game never shows. The PC's
    generator is run as it is; only the frames it is handed are different. It asks the medley
    module for each frame's pixels, so that module is told there are half as many frames, each
    half the size, and gives every second frame of the real show, scaled down."""
    from PIL import Image
    sys.path.insert(0, os.path.join(PC, "native"))
    import gen_s2sky_assets as pc_sky
    import s2sky_medley as medley

    full_w, full_h, full_pixels = medley.TEX_W, medley.TEX_H, medley.frame_pixels

    def small(f):
        img = Image.frombytes("RGBA", (full_w, full_h), full_pixels(f * SKY_EVERY))
        # Scaled with the colour weighted by its opacity ("RGBa"), or the transparent black round
        # every diamond bleeds into its edge. Then hard alpha again: the console's compressed
        # textures have one bit of it.
        img = img.convert("RGBa").resize((full_w // SKY_SHRINK, full_h // SKY_SHRINK), Image.BOX).convert("RGBA")
        r, g, b, a = img.split()
        return Image.merge("RGBA", (r, g, b, a.point(lambda v: 255 if v >= 128 else 0))).tobytes()

    medley.FRAMES = medley.FRAMES // SKY_EVERY
    medley.TEX_W, medley.TEX_H = full_w // SKY_SHRINK, full_h // SKY_SHRINK
    medley.frame_pixels = small

    textures = os.path.join(PROJ, "Assets", "Textures")
    if os.path.isdir(textures):                      # the clusters sky's frames, if an older export left them
        for name in os.listdir(textures):
            if name.startswith("T_S2Sky_Diamonds_") or name.startswith("T_S2Sky_Medley_"):
                os.remove(os.path.join(textures, name))
    pc_sky.OUT = os.path.join(PROJ, "Assets")
    pc_sky.DIAMOND_MODE = "medley"
    pc_sky.main()
    print("sky: %d frames at %d x %d" % (medley.FRAMES, medley.TEX_W, medley.TEX_H))


if __name__ == "__main__":
    sonic()
    sounds()
    sky()
