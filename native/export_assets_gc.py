"""Everything but the stage itself, for the GameCube: Sonic, the sounds and the sky.

    python native/export_assets_gc.py        (needs Pillow, numpy and soundfile)

All of it comes out of the PC repo (../Sonic2Special3D); nothing is designed here.

SONIC      proj/Assets/Sonic/ is copied as it is. It looked like the expensive part -- 33 meshes,
           one for every frame of his animation -- and it is 1.7 MB. It fits.

SOUNDS     The PC keeps its two music tracks as raw PCM: 46 MB, twice this machine's memory.
           Here they are stereo Ogg Vorbis at 32 kHz with the asset's STREAM flag set: the engine
           leaves the audio ON THE DISC and decodes it a little at a time as it plays, so a track
           costs no memory to speak of. The effects stay raw PCM (they must start the instant they are asked
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
MUSIC_RATE, MUSIC_QUALITY = 32000, 0.5     # stereo, Vorbis quality 0.5: about 96 kbit/s
EFFECT_RATE = 22050

# file in the PC's external/audio, asset name, uuid: the names and uuids are the PC's, so the
# scripts find the same assets on both machines
MUSIC = [("ss_intro.wav", "SW_SpecialStage_Intro", 0x51C0FFEE00300001),
         ("ss_loop.wav", "SW_SpecialStage_Loop", 0x51C0FFEE00300002)]
EFFECTS = [("Ring.wav", "SW_Ring", 0x51C0FFEE00300010), ("LoseRings.ogg", "SW_LoseRings", 0x51C0FFEE00300011),
           ("Jump.ogg", "SW_Jump", 0x51C0FFEE00300012), ("Checkpoint.wav", "SW_Checkpoint", 0x51C0FFEE00300013),
           ("Get_Emerald.wav", "SW_GetEmerald", 0x51C0FFEE00300014),
           ("Fail.wav", "SW_Fail", 0x51C0FFEE00300019), ("Explosion2.wav", "SW_Explosion", 0x51C0FFEE0030001A),
           ("Exit_SS.wav", "SW_ExitStage", 0x51C0FFEE0030001B)]
NORMALISE = {"SW_GetEmerald": 0.97}         # as the PC does: that file is quiet


def stereo_at(path, rate):
    """Both channels (a mono file is doubled), at `rate`. Shape: frames x 2."""
    data, src_rate = soundfile.read(path, dtype="float64", always_2d=True)
    if data.shape[1] == 1:
        data = numpy.repeat(data, 2, axis=1)
    data = data[:, :2]
    if src_rate == rate:
        return data
    width = max(1, int(round(src_rate / float(rate))))
    n = int(len(data) * rate / float(src_rate))
    at = numpy.arange(n) * (src_rate / float(rate))
    out = numpy.empty((n, 2))
    for c in range(2):
        ch = data[:, c]
        if width > 1:
            ch = numpy.convolve(ch, numpy.ones(width) / width, mode="same")
        out[:, c] = numpy.interp(at, numpy.arange(len(ch)), ch)
    return out


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
        audio = stereo_at(os.path.join(src, file_name), MUSIC_RATE)
        if os.environ.get("GC_MUSIC_SECONDS"):                 # a test: trims the tracks
            audio = audio[:int(float(os.environ["GC_MUSIC_SECONDS"]) * MUSIC_RATE)]
        # ENCODED HERE, stereo, at a proper quality. The engine's own cook encodes Vorbis at quality
        # 0.1 (about 55 kbit/s mono), and it showed. A ready-made track was tried once before and
        # hung the console at the loading screen -- but that was MEMORY: it was held in RAM then.
        # The engine now leaves a Stream sound's audio on the disc, so its size costs nothing.
        # Written in blocks: libsndfile's Vorbis writer dies without a word when handed minutes at once.
        ogg = io.BytesIO()
        with soundfile.SoundFile(ogg, "w", samplerate=MUSIC_RATE, channels=2, format="OGG", subtype="VORBIS",
                                 compression_level=1.0 - MUSIC_QUALITY) as f:
            for at in range(0, len(audio), MUSIC_RATE):
                f.write(audio[at:at + MUSIC_RATE])
        body = ogg.getvalue()
        d = sound_header(asset, uuid, True, 2, MUSIC_RATE, len(audio))
        d += struct.pack("<?", True) + struct.pack("<I", len(body)) + body
        open(os.path.join(out, asset + ".oct"), "wb").write(d)
        total += len(d)
        print("  %-24s stereo Vorbis, streamed from the disc, %.1f s, %.2f MB, %d kbit/s" % (
            asset, len(audio) / float(MUSIC_RATE), len(d) / 1048576.0, len(body) * 8 / (len(audio) / float(MUSIC_RATE)) / 1000))
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


SKY_EVERY = 1                       # keep every Nth frame of the PC's 384. Sky.lua's MEDLEY_EVERY must say the same
SKY_SHRINK = 1                      # and divide their size by this. 1 and 1: the PC's show exactly, 25 MB cooked.
# That is far more than fits in memory, and it does not have to: the GameCube Sky.lua STREAMS the
# frames (see patch_from_pc.py), holding half a megabyte of them at a time. Before that, the sky
# had to live in about 3 MB whole: half size was blurry, a quarter of the frames did not read as
# motion, and 6 MB crashed. If the disc cannot keep up on hardware, raise SKY_EVERY first.


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


def hud():
    """THE HUD, all of it: the PC's art, font and effects, made by the PC's own scripts.

    What differs is size. The PC scales its pixel art up four times and keeps it uncompressed
    (4.5 MB of textures and a 2 MB font atlas); this machine has about 1.8 MB to spare. So the art
    goes in at the size it was drawn, and NOT flagged to stay uncompressed: the engine's cook then
    stores anything with soft alpha as RGB5A3, 16 bits a texel with 3 of alpha, which keeps the
    soft edges CMPR's single bit would chew. The font's atlas is always uncompressed, so it is
    made small instead: the glyphs the game actually prints, at half the size."""
    sys.path.insert(0, os.path.join(PC, "native"))
    import gen_ui_assets as pc_ui
    import gen_ui_font as pc_font
    import gen_fx_assets as pc_fx

    pc_ui.TEX = os.path.join(PROJ, "Assets", "Textures", "UI")
    pc_ui.SCALE_ART, pc_ui.FORCE_HQ = False, False
    pc_ui.main()

    pc_font.OUT = os.path.join(PROJ, "Assets", "Textures", "UI", "F_SonicUI.oct")
    pc_font.LOOK = os.path.join(HERE, "..", "F_SonicUI_atlas_gc.png")
    pc_font.SIZE = 30
    pc_font.ATLAS_W, pc_font.ATLAS_H = 256, 256
    pc_font.OUTLINE, pc_font.SHADOW = 1, (2, 2)
    pc_font.PAD = pc_font.OUTLINE + 2
    pc_font.ONLY = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!"     # numbers, COOL !, TOO BAD !, the banners
    pc_font.main()
    os.remove(pc_font.LOOK)

    pc_fx.OUT = os.path.join(PROJ, "Assets", "Stage", "FX")
    pc_fx.LOOK = os.path.join(PROJ, "Assets", "Stage", "FX")        # its look-at PNGs: removed again below
    pc_fx.main()
    for name in os.listdir(pc_fx.OUT):
        if name.endswith(".png"):
            os.remove(os.path.join(pc_fx.OUT, name))


if __name__ == "__main__":
    sonic()
    sounds()
    hud()
    sky()
