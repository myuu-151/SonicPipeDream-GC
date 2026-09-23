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
           ("Exit_SS.wav", "SW_ExitStage", 0x51C0FFEE0030001B),
           # the menus: the highlight moving, a menu going on to the next (and pausing), a stage chosen
           ("MenuButton.ogg", "SW_MenuMove", 0x51C0FFEE0030001C), ("Select.ogg", "SW_MenuSelect", 0x51C0FFEE0030001E),
           ("SpecialWarp.ogg", "SW_MenuWarp", 0x51C0FFEE0030001D)]
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


STAR_FRAMES = 8                     # Sky.lua's STAR_FRAMES must say the same
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
    # All EIGHT of the PC's star frames at full size: 4 MB cooked and held in memory. (Four were
    # tried for headroom; the twinkle was coarser and the full set was asked for back.)
    stars_of = pc_sky.gen_stars_frame
    pc_sky.STAR_FRAMES = STAR_FRAMES
    pc_sky.gen_stars_frame = lambda field, f, *a, **k: stars_of(field, f, frames=STAR_FRAMES)
    if os.path.isdir(textures):
        for name in os.listdir(textures):
            if name.startswith("T_S2Sky_Stars_"):
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
    # Drawn at the size it is SHOWN. At 30 px (a 256 x 256 atlas) the numbers, shown at about 36,
    # and COOL !, at about 52, were stretched up and came out blurry. 48 px fills a 512 x 256 atlas:
    # 512 KB, which is there to spend.
    pc_font.SIZE = 48
    pc_font.ATLAS_W, pc_font.ATLAS_H = 512, 256
    pc_font.OUTLINE, pc_font.SHADOW = 2, (3, 3)
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


# THE OTHER SEVEN SKIES. Each stage has its own (stage_palettes.py's SKY) and the menu sits over
# Noir. The classic sky above is the PC's generator run as it is, at full size, so the PC's own
# variant frames are exactly what running it here would make: they are copied. On the disc they
# are about 29 MB each once cooked; in memory, only the 8 star frames of the sky on show and the
# few medley frames Sky.lua is streaming.
SKY_NAMES = ["Midnight", "Dawn", "Pastel", "Sunset", "Aurora", "Inferno", "Noir"]


def skies():
    for name in SKY_NAMES:
        src = os.path.join(PC, "proj", "Assets", "Skies", name)
        dst = os.path.join(PROJ, "Assets", "Skies", name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print("sky %-9s %d files" % (name, len(os.listdir(dst))))


def emeralds():
    """The seven chaos emeralds, one a stage: the PC's export_emeralds.py, run as it is, but its
    two textures a gem left to the console's compressed cook. The PC keeps them uncompressed
    (256 x 256 RGBA, half a megabyte a gem); here that is 64 KB."""
    sys.path.insert(0, os.path.join(PC, "native"))
    import export_emeralds as pe
    write = pe.write_texture

    def compressed(*a, **k):
        k["force_hq"] = False
        return write(*a, **k)

    pe.write_texture = compressed
    pe.OUT = os.path.join(PROJ, "Assets", "Stage", "Emeralds")
    pe.main()


# THE MENU AND THE STAGE SELECT: the PC's gen_menu_assets.py, run as it is, with its textures
# made for a 640 x 480 television. The PC cooks the art as it was drawn, up to 4x the mockup
# and uncompressed: 2048-wide textures (more than this GPU takes at all) and megabytes of them.
# Here every piece is scaled to MENU_SCALE art pixels a mockup pixel -- the television shows the
# 522 x 386 mockup at about 1.23 -- and left to the console cook (RGB5A3 for soft edges, CMPR for
# the opaque photographs). MenuLayout.lua carries each texture's real size, so the layout is the
# PC's whatever size the art is.
MENU_SCALE = 1.25
MENU_FIT = {"T_Menu_Circles": 256}          # at most this, a side: the circles would pad to 512 x 512

# SAVE, the GameCube's own fifth item (it opens SavePrompt.lua), under the PC's four. The mockup
# spaced four rows 53 apart down to y 300, and the watermark runs along under them from 344; five
# at that spacing would run into it. So all five are spaced again, evenly, MENU_ROW_GAP apart
# centre to centre, from where the first row's centre is.
MENU_EXTRA_ITEMS = [("save", "item_save")]
MENU_FIRST_CENTRE = 120.0
MENU_ROW_GAP = 50.0


def menu():
    import json
    from PIL import Image
    sys.path.insert(0, os.path.join(PC, "native"))
    import gen_menu_assets as pm
    from gen_s2sky_assets import write_texture

    layout = json.load(open(os.path.join(pm.PARTS, "layout.json")))
    where = {p["name"]: p for p in layout["parts"]}

    pm.ITEMS = list(pm.ITEMS) + MENU_EXTRA_ITEMS
    for i, (_key, part) in enumerate(pm.ITEMS):
        row = where.get(part) or where[pm.ROW_OF.get(part, "item_options")]
        h = Image.open(os.path.join(pm.PARTS, part + ".png")).height
        pm.ROW_AT[part] = (row["x"], int(round(MENU_FIRST_CENTRE + i * MENU_ROW_GAP - h * 0.5)))
    pm.ROW_OF.setdefault("item_save", "item_options")
    mock = {}                                   # texture name -> its size on the mockup
    for name, part in pm.PIECES:
        if part in pm.DERIVED:
            mock[name] = pm.DERIVED[part][1:]
        elif part == "bg_scanlines_full":
            mock[name] = (None, layout["reference_size"][1] - layout["panel_top"])
        else:
            mock[name] = (where[part]["w"], where[part]["h"])
    for i, (_key, part) in enumerate(pm.ITEMS):
        size = Image.open(os.path.join(pm.PARTS, part + ".png")).size
        mock["T_Menu_Item%d" % (i + 1)] = mock["T_Menu_Item%d_Off" % (i + 1)] = size

    def mockup_size(name):
        if name in mock:
            return mock[name]
        part = where["preview_picture"] if name.startswith("T_Menu_Preview") else where["emerald"]
        return part["w"], part["h"]

    # The PC numbers its textures' UUIDs in the order it cooks them, items included, so an item
    # added here would move every texture cooked after it onto another's number. The added items
    # take numbers of their own, well clear, and the rest keep the PC's.
    first_added = len(pm.PIECES) + 2 * (len(pm.ITEMS) - len(MENU_EXTRA_ITEMS))
    added = 2 * len(MENU_EXTRA_ITEMS)

    def uuid_index(index):
        if index < first_added:
            return index
        if index < first_added + added:
            return 0x100 + (index - first_added)
        return index - added

    def save(name, img, index):
        index = uuid_index(index)
        mw, mh = mockup_size(name)
        scale = MENU_SCALE
        if name in MENU_FIT:
            scale = min(scale, MENU_FIT[name] / float(max(mw, mh)))
        w = img.width if mw is None else min(img.width, int(round(mw * scale)))    # never enlarged
        h = min(img.height, int(round(mh * scale)))
        if (w, h) != img.size:
            # weighted by opacity, or the transparent black round the art bleeds into its edge
            img = img.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
        canvas = Image.new("RGBA", (pm.pot(img.width), pm.pot(img.height)), (0, 0, 0, 0))
        canvas.alpha_composite(img, (0, 0))
        write_texture(os.path.join(pm.TEX, name + ".oct"), name, pm.UUID_MENU + index,
                      canvas.width, canvas.height, canvas.tobytes(), wrap=0, force_hq=False, quiet=True)
        return canvas.size, img.size

    pm.TEX = os.path.join(PROJ, "Assets", "Textures", "UI")
    pm.LUA = os.path.join(PROJ, "Scripts", "MenuLayout.lua")
    pm.save = save
    pm.main()


if __name__ == "__main__":
    # python native/export_assets_gc.py [part ...]   -- all of them, or only those named
    parts = {"sonic": sonic, "sounds": sounds, "hud": hud, "sky": sky, "skies": skies,
             "emeralds": emeralds, "menu": menu}
    for name in (sys.argv[1:] or list(parts)):
        parts[name]()
