"""Turn the PC repo's SpecialStage.lua into the GameCube one.

    python native/patch_from_pc.py

Reads ../Sonic2Special3D/proj/Scripts/SpecialStage.lua, applies the GameCube changes below and
writes proj/Scripts/SpecialStage.lua. The gameplay is the PC's, line for line; only what the
machine forces is different. Doing it as a list of changes, and not as a copy edited by hand,
means a gameplay fix on the PC arrives here by running this again -- and if the PC script has
moved so far that a change no longer fits, this stops and says which one.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "Sonic2Special3D", "proj", "Scripts", "SpecialStage.lua"))
OUT = os.path.abspath(os.path.join(HERE, "..", "proj", "Scripts", "SpecialStage.lua"))

CHANGES = [
    # -- the header says which script this is
    ("""-- SpecialStage.lua
-- A basic playable special stage.
--
--     A / D      steer left and right round the inside of the pipe
--     Space      jump
--     R          start again
""", """-- SpecialStage.lua (GAMECUBE). Made from the PC repo's script by native/patch_from_pc.py:
-- change the gameplay THERE and run that again; change only GameCube matters here, in that file.
-- A basic playable special stage.
--
--     stick / d-pad   steer left and right round the inside of the pipe     (A / D on a keyboard)
--     A button        jump                                                  (Space)
--     Start           start again                                           (R)
"""),
    # -- less of everything alive at once
    ("local SEE_AHEAD, SEE_BEHIND = 110, 6 ", """local PIECES_AHEAD, PIECES_BEHIND = 72, 12   -- frames of TRACK shown round the player. The PC shows all
                                        -- 121 pieces and lets the engine cull; here a piece is up to
                                        -- 21,000 triangles and the far ones are not worth a draw call
local SEE_AHEAD, SEE_BEHIND = 72, 6 """),
    ("    self.camera:SetFar(6000.0)\n", "    self.camera:SetFar(1200.0)\n"),
    # -- each piece node remembers the frames it covers
    ("            self.pieceNodes[#self.pieceNodes + 1] = { node = node, name = name }\n",
     "            self.pieceNodes[#self.pieceNodes + 1] = { node = node, name = name,\n"
     "                                                      first = piece.first_frame, last = piece.last_frame }\n"),
    # -- the HUD is the PC's (SpecialStageUI.lua, copied below). Beside it, one small line of text at
    # the BOTTOM of the screen for the numbers a console build lives by: frame rate, the worst
    # frame of the last half second, how much track is drawn, and free memory.
    ("""    local ui = world:SpawnNode("Canvas")
    ui:SetScript("SpecialStageUI")
""", """    local ui = world:SpawnNode("Canvas")
    ui:SetScript("SpecialStageUI")
    local debug = world:SpawnNode("Canvas")
    debug:SetAnchorMode(AnchorMode.TopLeft)
    debug:SetPosition(0.0, 0.0)
    debug:SetDimensions(640.0, 480.0)
    self.readout = debug:CreateChild("Text")
    self.readout:SetAnchorMode(AnchorMode.TopLeft)
    self.readout:SetPosition(28.0, 440.0)
    self.readout:SetTextSize(14.0)
    self.readout:SetColor(Vec(1.0, 1.0, 0.2, 1.0))
    self.readout:SetText("...")
    self.fpsTime, self.fpsFrames, self.piecesShown = 0.0, 0, 0
"""),
    # (The light is the PC's, untouched. It was stronger here for a while, to give the arch spheres
    # some shape without the specular highlight the GameCube renderer lacks; now export_gc.py
    # PAINTS that highlight onto them, so the two machines are lit alike.)
    # -- a pad
    ("""        if (Input.IsKeyDown(Key.A)) then want = want + 1.0 end
        if (Input.IsKeyDown(Key.D)) then want = want - 1.0 end
""", """        if (Input.IsKeyDown(Key.A)) then want = want + 1.0 end
        if (Input.IsKeyDown(Key.D)) then want = want - 1.0 end
        local stick = Input.GetGamepadAxisValue(Gamepad.AxisLX)
        if (math.abs(stick) > 0.25) then want = want - stick end
        if (Input.IsGamepadButtonDown(Gamepad.Left)) then want = want + 1.0 end
        if (Input.IsGamepadButtonDown(Gamepad.Right)) then want = want - 1.0 end
        want = math.max(-1.0, math.min(1.0, want))
"""),
    ("    if (Input.IsKeyJustDown(Key.R)) then self:Restart() end\n",
     "    if (Input.IsKeyJustDown(Key.R) or Input.IsGamepadButtonJustDown(Gamepad.Start)) then self:Restart() end\n"),
    ("Input.IsKeyJustDown(Key.Space)) then\n        self.rise = JUMP",
     "(Input.IsKeyJustDown(Key.Space) or Input.IsGamepadButtonJustDown(Gamepad.A))) then\n        self.rise = JUMP"),
    # -- show only the track near the player, and keep the readout
    ("    self:UpdateObjects()\n", """    self:UpdateObjects()
    self:UpdatePieces()
    self.fpsTime, self.fpsFrames = self.fpsTime + deltaTime, self.fpsFrames + 1
    self.worstFrame = math.max(self.worstFrame or 0.0, deltaTime)      -- an average hides a spike; this does not
    if (self.fpsTime >= 0.5) then
        local round = self.data.sections[math.min(self.section, #self.data.sections)]
        -- free memory, in KB: THE number on a 24 MB machine. (0 where the engine cannot tell.)
        local free = (System.GetFreeMemory ~= nil) and (System.GetFreeMemory() // 1024) or 0
        -- how the SD card is read: dma27 is the fast one, and needs a semi-passive adapter
        local sd = (System.GetStorageMode ~= nil) and System.GetStorageMode() or ""
        self.readout:SetText(string.format("%.1f fps  worst %d ms  %d pieces  free %d KB  %s",
                                           self.fpsFrames / self.fpsTime, math.floor(self.worstFrame * 1000.0 + 0.5),
                                           self.piecesShown, free, sd))
        self.fpsTime, self.fpsFrames, self.worstFrame = 0.0, 0, 0.0
    end
"""),
    ("-- Keep alive only what is near the player.\n", """-- Show only the track near the player. (Two nodes a piece: the matte pipe and the glossy trim.)
function SpecialStage:UpdatePieces()
    local lo, hi = self.frame - PIECES_BEHIND, self.frame + PIECES_AHEAD
    local shown = 0
    for _, p in ipairs(self.pieceNodes) do
        local near = (p.last >= lo and p.first <= hi)
        if (near ~= p.shown) then
            p.node:SetVisible(near)
            p.shown = near
        end
        if (near) then shown = shown + 1 end
    end
    self.piecesShown = shown / 2
end

-- Keep alive only what is near the player.
"""),
]


# Scripts that are the PC's with a change or two (or none).
OTHERS = {
    "SpecialStageMusic.lua": [],
    # The HUD is the PC's. A television hides the outer few percent of the picture, so here it keeps
    # clear of the edges.
    "SpecialStageUI.lua": [("local SAFE_MARGIN = 0.0\n", "local SAFE_MARGIN = 0.04\n")],
    # THE SKY IS STREAMED. The PC loads all 384 frames of its show and keeps them: 25 MB cooked,
    # more than this machine has. Holding fewer, smaller frames was tried both ways and looked
    # bad both ways (half size is blurry; a quarter of the frames does not read as motion; and
    # anything past about 4 MB crashed). So here a frame is in memory only around the moment it
    # is shown: the next few are asked for IN THE BACKGROUND (AsyncLoadAsset), each is shown
    # when it has arrived, and the ones gone by are unloaded. About half a megabyte at any time,
    # whatever the size and number of frames -- which is what lets them be the PC's own.
    # MEDLEY_EVERY must match SKY_EVERY in export_assets_gc.py. The rate is scaled where it is
    # USED: medleyFramesPerSecond is a property, the scene file stores the PC's 14, and a stored
    # property beats a default set in Create().
    "Sky.lua": [
        ("local MEDLEY_FRAMES = 384\n",
         "local MEDLEY_EVERY = 1         -- every Nth frame of the PC's show is on the disc\n"
         "local MEDLEY_FRAMES = 384 // MEDLEY_EVERY\n"
         "local MEDLEY_AHEAD = 4         -- frames asked for ahead of the one on show\n"),
        ("""        local now = math.floor(self.medleyTime * self.medleyFramesPerSecond) % MEDLEY_FRAMES
        self.diamondFrames[1] = first
        self.medleyLoaded = 1
        self.medleyCursor = now
""", """        self.window = {}                -- frame number -> the asset asked for (it may not be here yet)
"""),
        ("""        -- Bring in a few more frames, working forward from the cursor and round.
        local budget = MEDLEY_LOADS_PER_TICK
        while (budget > 0 and self.medleyLoaded < MEDLEY_FRAMES) do
            local i = (self.medleyCursor % MEDLEY_FRAMES) + 1
            if (self.diamondFrames[i] == nil) then
                self.diamondFrames[i] = LoadAsset(MedleyName(self.shownSky, i))
                self.medleyLoaded = self.medleyLoaded + 1
                budget = budget - 1
            end
            self.medleyCursor = self.medleyCursor + 1
        end

        -- Its own clock, which only runs while the next frame is in memory:
        -- playback can catch the loader up, and waiting a tick is better than
        -- skipping ahead and showing a gap.
        local nextTime = self.medleyTime + deltaTime
        local nextFrame = math.floor(nextTime * self.medleyFramesPerSecond) % MEDLEY_FRAMES
        if (self.diamondFrames[nextFrame + 1] ~= nil) then
            self.medleyTime = nextTime
        end
        dframe = math.floor(self.medleyTime * self.medleyFramesPerSecond) % MEDLEY_FRAMES
""", """        local fps = self.medleyFramesPerSecond / MEDLEY_EVERY
        local cur = math.floor(self.medleyTime * fps) % MEDLEY_FRAMES

        -- Ask, in the background, for the frames coming up.
        for k = 0, MEDLEY_AHEAD do
            local i = (cur + k) % MEDLEY_FRAMES + 1
            if (self.window[i] == nil) then
                self.window[i] = { asked = AsyncLoadAsset(MedleyName(self.shownSky, i)) }
            end
        end

        -- A frame that has arrived. What AsyncLoadAsset hands back is a bare asset, which
        -- SetTexture will not take ("Expected Texture"); once it is in memory, LoadAsset gives
        -- the same frame as a texture, at once.
        local function Arrived(i)
            local w = self.window[i]
            if (w == nil) then return nil end
            if (w.tex == nil and w.asked:IsLoaded()) then
                w.tex = LoadAsset(MedleyName(self.shownSky, i))
            end
            return w.tex
        end

        -- Let go of the ones gone by: all but the frame on show and the one before it, which
        -- the material may still be drawing with. LETTING GO IS NOT FREEING. The engine frees a
        -- frame when nothing refers to it, and these tables' entries go on referring to it until
        -- Lua's collector has been round: asking the engine to unload one straight away is
        -- refused ("still has 1 refs"), every frame stays, and the memory runs out. So: drop
        -- them, and every few, run the collector and then have the engine sweep what is unheld.
        for i, _ in pairs(self.window) do
            local behind = (cur + 1 - i) % MEDLEY_FRAMES
            if (behind > 1 and behind < MEDLEY_FRAMES - MEDLEY_AHEAD - 1) then
                self.window[i] = nil
                self.dropped = (self.dropped or 0) + 1
            end
        end
        if ((self.dropped or 0) >= 4) then
            self.dropped = 0
            collectgarbage()
            RefSweep()
        end

        -- Its own clock, which only runs while the next frame has arrived: the show waits for
        -- the disc rather than skipping ahead and showing a gap.
        local nextTime = self.medleyTime + deltaTime
        local nextFrame = math.floor(nextTime * fps) % MEDLEY_FRAMES
        if (Arrived(nextFrame + 1) ~= nil) then
            self.medleyTime = nextTime
            self.waited = 0.0
        else
            -- A frame that NEVER comes: its read failed (the engine leaves such an asset unloaded,
            -- where it used to crash). Waiting for it would stop the sky for good, so after a
            -- moment it is skipped -- the picture holds for one frame -- and forgotten, so that it
            -- is asked for afresh the next time round.
            self.waited = (self.waited or 0.0) + deltaTime
            if (self.waited > 0.4) then
                self.window[nextFrame + 1] = nil
                self.medleyTime = nextTime
                self.waited = 0.0
            end
        end
        dframe = math.floor(self.medleyTime * fps) % MEDLEY_FRAMES
        self.medleyShown = Arrived(dframe + 1)
"""),
        ("""        local dtex = self.diamondFrames[dframe + 1]
        if (dtex ~= nil) then
""", """        local dtex = self.diamondFrames[dframe + 1]
        if (self.medley) then dtex = self.medleyShown end
        if (dtex ~= nil) then
"""),
    ],
}


def main():
    for name, changes in OTHERS.items():
        text = open(os.path.join(os.path.dirname(SRC), name), encoding="utf-8", newline="").read().replace("\r\n", "\n")
        for old, new in changes:
            if old not in text:
                raise SystemExit("%s: a change no longer fits the PC script:\n%s" % (name, old))
            text = text.replace(old, new, 1)
        open(os.path.join(os.path.dirname(OUT), name), "w", encoding="utf-8", newline="\n").write(
            "-- FROM the PC repo, by native/patch_from_pc.py. Change it there.\n" + text)
    s = open(SRC, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    for n, (old, new) in enumerate(CHANGES):
        if old not in s:
            raise SystemExit("change %d no longer fits the PC script:\n%s" % (n + 1, old[:200]))
        s = s.replace(old, new, 1)
    open(OUT, "w", encoding="utf-8", newline="\n").write(s)
    print("wrote %s (%d changes)" % (OUT, len(CHANGES)))


if __name__ == "__main__":
    main()
