"""Turn the PC repo's SpecialStage.lua into the GameCube one.

    python native/patch_from_pc.py

Reads ../Sonic2Special3D/proj/Scripts/SpecialStage.lua, applies the GameCube changes below and
writes proj/Scripts/SpecialStage.lua. The gameplay is the PC's, line for line; only what the
machine forces is different. Doing it as a list of changes, and not as a copy edited by hand,
means a gameplay fix on the PC arrives here by running this again -- and if the PC script has
moved so far that a change no longer fits, this stops and says which one.
"""

import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "Sonic2Special3D", "proj", "Scripts", "SpecialStage.lua"))
OUT = os.path.abspath(os.path.join(HERE, "..", "proj", "Scripts", "SpecialStage.lua"))

CHANGES = [
    # SONIC'S BALL DOES NOT ROLL HERE: its gloss is painted into its vertices (export_gc.py,
    # write_ball), lit from above and ahead, so the ball keeps the track's up and forward. The PC's
    # ball is a plain lit sphere, whose roll was never visible anyway.
    ("""        self.player:SetWorldRotationQuat(FacingQuat(Turn(fwdHere), Turn(upHere)))""",
     """        self.player:SetWorldRotationQuat(FacingQuat(fwdHere, upHere))      -- GAMECUBE: no roll (painted gloss)"""),
    ("local BALL_ROLLS = true ", "local BALL_ROLLS = false"),    # (the same: the curled ball on the pipe)
    # -- the header says which script this is
    ("""-- SpecialStage.lua
-- A basic playable special stage.
--
--     A / D      steer left and right round the inside of the pipe
--     Space      jump; again in the air to drop straight back down
--     Escape     pause: CONTINUE, or EXIT to the stage select
--     R          start again
""", """-- SpecialStage.lua (GAMECUBE). Made from the PC repo's script by native/patch_from_pc.py:
-- change the gameplay THERE and run that again; change only GameCube matters here, in that file.
-- A basic playable special stage.
--
--     stick / d-pad   steer left and right round the inside of the pipe     (A / D on a keyboard)
--     A button        jump; again in the air to drop straight back down     (Space)
--     Start           pause: CONTINUE, or EXIT to the stage select          (Escape)
--
-- The pad reaches the PC's keys through PadInput.lua; only the steering is given the stick here.
"""),
    # -- less of everything alive at once
    ("local SEE_AHEAD, SEE_BEHIND = 110, 6 ", """local PIECES_AHEAD, PIECES_BEHIND = 72, 12   -- frames of TRACK shown round the player. The PC shows all
                                        -- 121 pieces and lets the engine cull; here a piece is up to
                                        -- 21,000 triangles and the far ones are not worth a draw call
local SEE_AHEAD, SEE_BEHIND = 72, 6 """),
    ("    self.camera:SetFar(6000.0)\n", "    self.camera:SetFar(1200.0)\n"),
    # -- each piece node remembers the frames it covers (in LoadStage, and in a marathon's AppendZone)
    ("            self.pieceNodes[#self.pieceNodes + 1] = { node = node, name = name, frame = piece.first_frame }\n",
     "            self.pieceNodes[#self.pieceNodes + 1] = { node = node, name = name, frame = piece.first_frame,\n"
     "                                                      first = piece.first_frame, last = piece.last_frame }\n", 2),
    # ...and so does each straight of the lead-in laid behind the start: straight k back covers
    # frames -8k to -8k + 8 (a straight is eight frames)
    ("""            node:SetWorldRotationQuat(Vec(first.quat[1], first.quat[2], first.quat[3], first.quat[4]))
            self.pieceNodes[#self.pieceNodes + 1] = { node = node, name = name }
""", """            node:SetWorldRotationQuat(Vec(first.quat[1], first.quat[2], first.quat[3], first.quat[4]))
            self.pieceNodes[#self.pieceNodes + 1] = { node = node, name = name, first = -8 * k, last = -8 * k + 8 }
"""),
    # -- ONE stage's data in memory at a time (Screens.lua's LoadStageData), and the pipe's meshes
    # let go with its nodes, so that the menus have the room back
    ("""        Script.Require("StageData" .. n)
        self.data = _G["StageData" .. n]
""", """        self.data = LoadStageData(n)
"""),
    ("""    for _, p in ipairs(self.pieceNodes or {}) do p.node:Destruct() end
    self.pieceNodes = {}
""", """    for _, p in ipairs(self.pieceNodes or {}) do p.node:Destruct() end
    self.pieceNodes = {}
    self.pieceMeshes = {}
    self.emeraldMeshes = nil                    -- (a marathon's: see BuildMarathon)
"""),
    # -- the readout goes and comes back with the stage (in Leave, then in Enter)
    ("{ self.player, self.playerShadow, self.uiNode }",
     "{ self.player, self.playerShadow, self.uiNode, self.debugNode }", 2),
    # -- the HUD is the PC's (SpecialStageUI.lua, copied below). Beside it, FOR TESTING ONLY
    # (GcTest.readout), one small line of text at the BOTTOM of the screen for the numbers a console
    # build lives by: frame rate, the worst frame of the last half second, how much track is drawn,
    # and free memory. Off, it is not made at all: text redrawn twice a second is memory churned.
    ("""    local ui = world:SpawnNode("Canvas")
    ui:SetScript("SpecialStageUI")
""", """    local ui = world:SpawnNode("Canvas")
    ui:SetScript("SpecialStageUI")
    self.fpsTime, self.fpsFrames, self.piecesShown = 0.0, 0, 0
    if (GcTest ~= nil and GcTest.readout) then
    local debug = world:SpawnNode("Canvas")
    self.debugNode = debug
    debug:SetAnchorMode(AnchorMode.TopLeft)
    debug:SetPosition(0.0, 0.0)
    debug:SetDimensions(640.0, 480.0)
    self.readout = debug:CreateChild("Text")
    self.readout:SetAnchorMode(AnchorMode.TopLeft)
    self.readout:SetPosition(28.0, 440.0)
    self.readout:SetTextSize(14.0)
    self.readout:SetColor(Vec(1.0, 1.0, 0.2, 1.0))
    self.readout:SetText("...")
    -- where the frame went (System.GetPerfReport): the average, and the worst frame, in ms
    self.perfLines = {}
    for i = 1, 2 do
        local line = debug:CreateChild("Text")
        line:SetAnchorMode(AnchorMode.TopLeft)
        line:SetPosition(28.0, 396.0 + 14.0 * i)
        line:SetTextSize(12.0)
        line:SetColor(Vec(1.0, 1.0, 0.2, 1.0))
        line:SetText("")
        self.perfLines[i] = line
    end
    end
"""),
    # (The light is the PC's, untouched. It was stronger here for a while, to give the arch spheres
    # some shape without the specular highlight the GameCube renderer lacks; now export_gc.py
    # PAINTS that highlight onto them, so the two machines are lit alike.)
    # (The pad's steering, and PadInput.lua for its buttons, are the PC's own now.)
    # (Jumping on A, and pausing on Start, need nothing here: PadInput.lua gives the pad's A to
    # the PC's Space and its Start to Escape. Start restarted the stage before there was a pause
    # menu; there is no restart on the pad now, as there is none on the PC's menus.)
    # -- show only the track near the player, and keep the readout
    ("    self:UpdateObjects()\n", """    self:UpdateObjects()
    self:UpdatePieces()
    self.fpsTime, self.fpsFrames = self.fpsTime + deltaTime, self.fpsFrames + 1
    self.worstFrame = math.max(self.worstFrame or 0.0, deltaTime)      -- an average hides a spike; this does not
    if (self.readout ~= nil and self.fpsTime >= 0.5) then
        local round = self.data.sections[math.min(self.section, #self.data.sections)]
        -- free memory, in KB: THE number on a 24 MB machine. (0 where the engine cannot tell.)
        local free = (System.GetFreeMemory ~= nil) and (System.GetFreeMemory() // 1024) or 0
        -- how the SD card is read: dma27 is the fast one, and needs a semi-passive adapter
        local sd = (System.GetStorageMode ~= nil) and System.GetStorageMode() or ""
        self.readout:SetText(string.format("%.1f fps  worst %d ms  %d pieces  free %d KB  %s",
                                           self.fpsFrames / self.fpsTime, math.floor(self.worstFrame * 1000.0 + 0.5),
                                           self.piecesShown, free, sd))
        if (System.GetPerfReport ~= nil) then
            local average, worst = System.GetPerfReport()
            self.perfLines[1]:SetText(average)
            self.perfLines[2]:SetText(worst)
        end
        self.fpsTime, self.fpsFrames, self.worstFrame = 0.0, 0, 0.0
    end
"""),
    # -- the stage plays itself: the PC's S2_AUTOPLAY, and GcTest.autoplay here (no environment)
    ("""    self.autoplay = (os ~= nil and os.getenv ~= nil and os.getenv("S2_AUTOPLAY") ~= nil)
""", """    self.autoplay = (os ~= nil and os.getenv ~= nil and os.getenv("S2_AUTOPLAY") ~= nil)
                    or (GcTest ~= nil and GcTest.autoplay == true)
"""),
    # -- the spin dash's test: GcTest.spin here (no environment)
    ("""    self.testSpin = (os ~= nil and os.getenv ~= nil and tonumber(os.getenv("S2_TEST_SPIN") or "")) or nil
""", """    self.testSpin = (os ~= nil and os.getenv ~= nil and tonumber(os.getenv("S2_TEST_SPIN") or "")) or nil
    if (self.testSpin == nil and GcTest ~= nil) then self.testSpin = GcTest.spin end
"""),
    # -- THE MARATHON'S COLOURS. On the PC a change of colours swaps every piece to another palette's
    # meshes (SM_Piece_Drop_P3 for _P5), all seven palettes loaded as they come. Here two sets do not
    # fit (2.8 MB each), and loading and freeing them each zone cut the heap up. The palettes are the
    # same meshes painted differently, so here the meshes the run started with stay, and a change of
    # colours RECOLOURS them in place, from a table of the pipe's colours in all seven palettes
    # (PipePalettes.lua, native/make_pipe_palettes.py; engine: StaticMesh:SetPaletteColors) -- at
    # once, with nothing read off the disc. The new sky's stars are read in by a background thread
    # (Screens.lua's Sky:BeginStarSwap) and go up when they are in.
    ("""    local full = name .. palette
""", """    local full = name .. (self.meshPalette or palette)  -- GAMECUBE: the meshes the stage began with
"""),
    ("""    self.palette = self.data.palette
""", """    self.palette = self.data.palette
    self.meshPalette = self.palette     -- GAMECUBE: the meshes' own colours; later ones are a recolour
"""),
    ("""function SpecialStage:SetPalette(n)
    if (n == self.palette or self:PieceMesh(self.pieceNodes[1].name, n) == nil) then return end
    self.palette = n
    for _, p in ipairs(self.pieceNodes) do p.node:SetStaticMesh(self:PieceMesh(p.name, n)) end
    if (TheSky ~= nil) then TheSky.sky = self.data.palette_skies[n] end
end
""", """function SpecialStage:SetPalette(n)
    -- GAMECUBE: the pipe at once, from the palettes' table; the sky the ordinary way
    if (n == self.palette or self.pieceMeshes == nil) then return end
    self:RecolourPipe(n)
    if (TheSky ~= nil) then TheSky.sky = self.data.palette_skies[n] end
end

-- GAMECUBE: the pipe in palette n, every piece mesh recoloured in place from the palettes' table
-- (PipePalettes.lua, read with the run: Screens.lua). It was the new palette's meshes read off the
-- disc for their colours, ~2 MB, and on a console's SD card a change of zone crawled for half a
-- minute at 7 frames a second.
function SpecialStage:RecolourPipe(n)
    if (PipePalettes == nil) then Script.Run("PipePalettes") end
    self.palette = n
    if (PipePalettes == nil or PipePalettes.index == nil) then
        Log.Warning("SpecialStage: no PipePalettes; the pipe keeps its colours")
        return
    end
    local own = tostring(self.meshPalette)
    for full, mesh in pairs(self.pieceMeshes) do
        -- SM_Piece_Drop_P3 is SM_Piece_Drop in the table
        local index = mesh and PipePalettes.index[full:sub(1, #full - #own - 2)]
        if (index == nil or not mesh:SetPaletteColors(index, PipePalettes.table, PipePalettes.palettes, n)) then
            Log.Warning("SpecialStage: no palette " .. n .. " colours for " .. full)
        end
    end
end

-- GAMECUBE: a change of colours, as a job: the new sky's star frames, read in by a background
-- thread (Screens.lua's Sky:BeginStarSwap).
function SpecialStage:RecolourJob(n)
    return { to = n, sky = self.data.palette_skies[n] }
end

-- True once the new sky's frames are in (all but the one on show: see Sky:StepStarSwap). ONE
-- CHANGE OF SKY AT A TIME: an earlier zone's may still be reading (the card is slow), and one
-- begun over it found its frames half the one sky, half the other, and the sky reloaded all eight
-- afresh (4 MB) under it. So an earlier one is let finish -- put up now, if its frames are in and
-- its own hold is gone -- and this one begins after.
function SpecialStage:StepRecolour(job)
    if (TheSky == nil or TheSky.BeginStarSwap == nil) then return true end
    if (job.swap == nil) then
        local w = TheSky.starSwap
        if (w ~= nil) then
            if (not w.switched and TheSky:StepStarSwap()) then
                TheSky:SwitchStars()
                TheSky.sky = w.sky
            end
            return false
        end
        -- its stars still being stashed in ARAM: wait for them (the twinkle carries on)
        if (TheSky.StashPending ~= nil and TheSky:StashPending(job.sky)) then return false end
        TheSky:BeginStarSwap(job.sky)
        job.swap = TheSky.starSwap or false         -- (false: nothing to read -- the same sky)
    end
    return TheSky:StepStarSwap()
end

-- Only a sky whose stars were read in goes up. The sky's other way to change (LoadSky: all eight
-- frames loaded afresh, 4 MB at once) is for behind a loading screen; in the middle of a run on a
-- console it ran the memory out, and the stage's own script failing for want of it stopped the game.
-- A change that could not be read (a frame of the stars never arrived) leaves the sky as it is.
function SpecialStage:SwitchSky(job)
    if (TheSky ~= nil and job.swap) then
        TheSky:SwitchStars()
        TheSky.sky = job.sky
    end
end
"""),
    ("""function SpecialStage:TickFade(dt)
    local h = self.holding
    if (h == nil) then return end
    h.clock = h.clock + dt
    if (h.clock >= SWITCH_AT) then
        self:SetPalette(h.to)
        self.holding = nil
    end
end

function SpecialStage:EndFade()
    self.holding = nil
end
""", """function SpecialStage:TickFade(dt)
    local h = self.holding
    if (h == nil) then return end
    h.clock = h.clock + dt
    -- GAMECUBE: the pipe changes ON THE EMERALD (SWITCH_AT), whatever the sky is doing; the sky
    -- with it when its stars are in, which they are when they were stashed in ARAM during the zone
    -- (Screens.lua's Sky:StashSky), and a moment later when they have to be read now. (Waiting for
    -- the sky before changing the pipe held the whole change of zone for twenty seconds of SD card.)
    if (h.job == nil) then
        if (h.to == self.palette) then
            self.holding = nil
            return
        end
        h.job = self:RecolourJob(h.to)
    end
    local ready = self:StepRecolour(h.job)
    if (h.clock >= SWITCH_AT and not h.piped) then
        self:RecolourPipe(h.to)
        h.piped = true
    end
    if (ready and h.piped) then
        self:SwitchSky(h.job)
        self.holding = nil
    end
end

function SpecialStage:EndFade()
    -- GAMECUBE: a change of sky part read is put right (the stars would be half one sky, half another)
    if (self.holding ~= nil and self.holding.job ~= nil and TheSky ~= nil and TheSky.CancelStarSwap ~= nil) then
        TheSky:CancelStarSwap()
    end
    self.holding = nil
end
"""),
    # -- a zone joined: its sky's stars stashed in ARAM while the zone before it is played
    ("""    self.zonesBuilt = self.zonesBuilt + 1
    print(string.format("MARATHON zone %d joined""", """    self.zonesBuilt = self.zonesBuilt + 1
    -- GAMECUBE: its sky's stars read into ARAM now, while the zone before it is played, so they are
    -- in at its hold (Screens.lua's Sky:StashSky)
    local nextSky = data.palette_skies[data.sections[s0 + 1].palette]
    if (TheSky ~= nil and TheSky.StashSky ~= nil and nextSky ~= nil) then TheSky:StashSky(nextSky) end
    print(string.format("MARATHON zone %d joined"""),
    # -- THE ZONE BUILD KEEPS TO ITS SLICE. It starts on the emerald, as the camera swings round
    # to Sonic's side, and at 4 ms a frame -- overrunning that, a piece of work at a time, with the
    # collector close behind it (Screens.lua) -- it dropped the game to 30 fps just then: the
    # camera's swing stepped, and Sonic seemed to be pulled back. Half the slice, and (Screens.lua)
    # half the work between yields: the build takes a second or two longer, and the frames hold.
    ("local GEN_SLICE_MS = 4 ", "local GEN_SLICE_MS = 2 "),
    # -- A ZONE IS JOINED A SLICE A FRAME, as it is built. Joined in one go it was a third of a second
    # in one frame -- its ~3000 frames of centre line turned into place, a table or more each, and
    # every piece spawned -- and the frame after it moved Sonic a third of a second at once: he
    # lurched forward as the hold handed him back. Run in the generator's coroutine, the join
    # yields every so often and TickMarathonGen gives it the same few milliseconds a frame. (Zone 1
    # is joined outside any coroutine, behind the loading screen, and so in one go as before.)
    ("""        if (coroutine.status(self.gen) == "dead") then
            self.gen = nil
            if (zone ~= nil) then
                self:AppendZone(zone)
            else
                self.genError = "zone " .. (self.zonesBuilt + 1) .. " could not be built"
            end
            return
        end""", """        if (coroutine.status(self.gen) == "dead") then
            self.gen = nil
            if (self.appending) then
                self.appending = nil                -- joined
            elseif (zone ~= nil) then
                self.appending = true               -- GAMECUBE: joined a slice a frame, from the next
                self.gen = coroutine.create(function() self:AppendZone(zone) end)
            else
                self.genError = "zone " .. (self.zonesBuilt + 1) .. " could not be built"
            end
            return
        end"""),
    ("""    self.zonesBuilt = 1
    self.gen = nil
""", """    self.zonesBuilt = 1
    self.gen = nil
    self.appending = nil
"""),
    ("""            data.path[#data.path + 1] = e
        end
    end
    for _, sec in ipairs(zone.sections) do""", """            data.path[#data.path + 1] = e
        end
        if (i % 128 == 0 and coroutine.isyieldable()) then coroutine.yield() end   -- GAMECUBE: a slice a frame
    end
    for _, sec in ipairs(zone.sections) do"""),
    ("""        end
    end
    for s = s0 + 1, #data.sections do""", """        end
        if (i % 4 == 0 and coroutine.isyieldable()) then coroutine.yield() end     -- GAMECUBE: a slice a frame
    end
    for s = s0 + 1, #data.sections do"""),
    ("""        self:SpawnArch(s)
""", """        self:SpawnArch(s)
        if (coroutine.isyieldable()) then coroutine.yield() end                    -- GAMECUBE: a slice a frame
"""),
    # -- A ZONE'S JOIN IS EVENLY SPACED. The centre line is sampled a step (5.02) at a time, and a
    # zone's length is never a whole number of steps: its last sample, its very end, lies a fraction
    # of a step past the one before (0.02 of one, in one zone). So for that one frame of track Sonic
    # all but stopped, the camera (3.2 frames behind) closed in, then stopped there in turn as he
    # went on -- a rubber band just after every hold, where the next zone joins (never at a check,
    # where nothing is joined). The samples round the join are spaced out evenly again: the track
    # is straight there (the hold's straights), so it is only their spacing that changes.
    ("""    for i, e in ipairs(zone.path) do
""", """    local joinAt = #data.path                   -- GAMECUBE: the last zone's end (see below)
    for i, e in ipairs(zone.path) do
"""),
    ("""        if (i % 128 == 0 and coroutine.isyieldable()) then coroutine.yield() end   -- GAMECUBE: a slice a frame
    end
    for _, sec in ipairs(zone.sections) do""", """        if (i % 128 == 0 and coroutine.isyieldable()) then coroutine.yield() end   -- GAMECUBE: a slice a frame
    end
    -- GAMECUBE: the frames round the join, a whole step apart again on average (see above)
    local a, b = joinAt - 4, joinAt + 4
    if (joinAt > 0 and a >= 1 and b <= #data.path) then
        local path, cum = data.path, { 0.0 }
        for k = a + 1, b do
            local p, q = path[k - 1], path[k]
            cum[#cum + 1] = cum[#cum] + math.sqrt((q[1] - p[1]) ^ 2 + (q[2] - p[2]) ^ 2 + (q[3] - p[3]) ^ 2)
        end
        local placed, seg = {}, 1
        for k = a + 1, b - 1 do
            local want = cum[#cum] * (k - a) / (b - a)
            while (seg < #cum - 1 and cum[seg + 1] < want) do seg = seg + 1 end
            local span = cum[seg + 1] - cum[seg]
            local t = (span > 0.0) and (want - cum[seg]) / span or 0.0
            local p, q = path[a + seg - 1], path[a + seg]
            local e = {}
            for c = 1, 9 do e[c] = p[c] + (q[c] - p[c]) * t end
            placed[k] = e
        end
        for k = a + 1, b - 1 do path[k] = placed[k] end
    end
    for _, sec in ipairs(zone.sections) do"""),
    # -- THE RUN-OUT GOES ON A WHOLE STEP A FRAME, and he may run on down it. It was stepped by the
    # centre line's LAST step -- and a zone's last sample is its very end, a fraction of a step past
    # the one before (see the join, above) -- so the run-out barely went anywhere: its pieces, laid
    # a step x 8 apart, were all but on top of each other (the flickering, doubled pipe at a run's
    # end), and he was held at the old end anyway (data.frames), so the run seemed cut short.
    ("""    local e, d = path[n], path[n - 1]
    local sx, sy, sz = e[1] - d[1], e[2] - d[2], e[3] - d[3]
    for i = 1, want do
        path[n + i] = { e[1] + sx * i, e[2] + sy * i, e[3] + sz * i, e[4], e[5], e[6], e[7], e[8], e[9] }
    end
""", """    local e, d, c = path[n], path[n - 1], path[n - 2]
    local sx, sy, sz = d[1] - c[1], d[2] - c[2], d[3] - c[3]          -- GAMECUBE: a whole step (see above)
    for i = 1, want do
        path[n + i] = { e[1] + sx * i, e[2] + sy * i, e[3] + sz * i, e[4], e[5], e[6], e[7], e[8], e[9] }
    end
    data.frames = math.max(data.frames or 0, (data.pathBase or 0) + #path - 1)   -- GAMECUBE: he runs on down it
"""),
    # -- THE RUN'S CENTRE LINE HOLDS ONLY WHAT IS NEAR HIM AND AHEAD. The PC's keeps every frame of
    # the run in one table, a slot a frame, for as long as the run goes on; past 8192 frames (the
    # fourth zone or so) Lua wanted that table's slots in one 128 KB block, which a console's heap, in
    # pieces by then, did not have. The next zone could not be joined, was built again, failed again,
    # every second and a half ("not enough memory"), and the run stopped at the end of its track.
    # So the frames passed are taken out and the rest moved down: data.pathBase is the first frame
    # the table holds, and the frames asked for are counted from it.
    ("""
    local f = math.max(0.0, math.min(frame, #path - 1.001))
""", """
    local f = math.max(0.0, math.min(frame - (self.data.pathBase or 0), #path - 1.001))    -- GAMECUBE: see TrimBehind
"""),
    ("""
        local f = math.max(0.0, math.min(frame, #path - 1.001))
""", """
        local f = math.max(0.0, math.min(frame - (self.data.pathBase or 0), #path - 1.001))    -- GAMECUBE: see TrimBehind
"""),
    ("""    local want = math.ceil(self.frame + seconds * SPEED) + 16 - (#path - 1)
""", """    local want = math.ceil(self.frame + seconds * SPEED) + 16 - (#path - 1 + (data.pathBase or 0))   -- GAMECUBE: see TrimBehind
"""),
    ("""    -- and the run's own table: the centre line and the rings of what is long gone (a zone's path
    -- is a table a frame, and a run can go on for as long as the player does). The frames gone all
    -- share the oldest one kept -- not nil, which would leave #path, and so the next zone's join,
    -- to chance.
    local data = self.data
    local upTo = math.min(math.floor(limit) - 100, #data.path - 1)
    if (upTo > (self.trimmedTo or 0)) then
        local oldest = data.path[upTo + 1]
        for f = (self.trimmedTo or 0) + 1, upTo do data.path[f] = oldest end
        self.trimmedTo = upTo
    end
""", """    -- and the run's own table: the centre line and the rings of what is long gone (a zone's path
    -- is a table a frame, and a run can go on for as long as the player does). GAMECUBE: the
    -- frames gone are TAKEN OUT, and the rest moved down to the start of the table, which so
    -- never holds more than two zones or so (a table a frame of the whole run wanted, past 8192
    -- frames, one 128 KB block the heap did not have). data.pathBase: the frame it starts at.
    local data = self.data
    local path, base = data.path, data.pathBase or 0
    local drop = math.min(math.floor(limit) - 100, base + #path - 1) - base
    if (drop > 0) then
        local n = #path
        table.move(path, drop + 1, n, 1)
        for i = n - drop + 1, n do path[i] = nil end
        data.pathBase = base + drop
    end
    -- and the pieces' places, of pieces long gone: nothing reads them after a piece is laid, and
    -- they were some 50 KB a zone, for good
    local pieces, gone = data.pieces, 0
    while (gone < #pieces - 1 and pieces[gone + 1].last_frame < limit - 100) do gone = gone + 1 end
    if (gone > 0) then
        local n = #pieces
        table.move(pieces, gone + 1, n, 1)
        for i = n - gone + 1, n do pieces[i] = nil end
    end
"""),
    # -- the first zone, and the run's seed, come from the loading screen (Screens.lua), which built
    # the zone while it was up; and the generator is let go of after a run (Script.Run, not Require)
    ("""    Script.Require("MarathonGen")
    local kit = MarathonKit
""", """    if (MarathonGen == nil) then Script.Run("MarathonGen") end     -- GAMECUBE: freed after a run
    -- GAMECUBE: every colour's emerald (each zone's item), loaded behind the loading screen (the
    -- marathon's list in Screens.lua) and held here for the run: loaded as its zone joined, it was
    -- a load off the disc in the middle of the run, a hitch, just as the heap is at its fullest.
    self.emeraldMeshes = self.emeraldMeshes or {}
    for n = 1, LAST_STAGE do
        self.emeraldMeshes[n] = self.emeraldMeshes[n] or LoadAsset("SM_Emerald_" .. n)
    end
    local kit = MarathonKit
"""),
    ("""    seed = math.floor(seed % 2147483647)
""", """    seed = math.floor(seed % 2147483647)
    if (MarathonSeed ~= nil) then seed = MarathonSeed end            -- GAMECUBE: Screens.lua's
"""),
    ("""    local zone = MarathonGen.BuildZone(seed, 1)
    if (zone == nil) then return nil end
""", """    local zone = MarathonFirstZone or MarathonGen.BuildZone(seed, 1)   -- GAMECUBE: built behind the loading screen
    MarathonFirstZone, MarathonSeed = nil, nil
    if (zone == nil) then return nil end
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
    "PadInput.lua": [],             # the controller, the PC's (which began as this build's own)
    "SavePrompt.lua": [],           # the PC's; it speaks of slot A here, of the Saves folder there
    "Loading.lua": [],              # the PC's (which began as this build's own); scaled, so the same here
    # A marathon's generator and what it builds from are the PC's. Both are let go of when a run
    # ends (Screens.lua's TeardownStage), so they are read with Script.Run: Require reads a file
    # only once in the life of the game.
    "MarathonGen.lua": [("""Script.Require("MarathonKit")
""", """if (MarathonKit == nil) then Script.Run("MarathonKit") end          -- GAMECUBE: freed after a run
""")],
    "MarathonKit.lua": [],
    "MenuMusic.lua": [],
    "GameOptions.lua": [],          # the settings, kept with the save on the card
    "OptionsPrompt.lua": [],        # OPTIONS on the title menu            # the menus' music: Screens.lua ticks it under its loading screen too
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
        # THE MENUS, THE LOADING SCREEN AND THE PAD: GameCube-only scripts, loaded at the end of
        # this one. Screens.lua replaces Sky:ShowMenu -- the menus and a stage are never in
        # memory together here -- and wraps Sky:Tick; it loads PadInput.lua.
        ("""function Sky:EditorTick(deltaTime)
    self:UpdateSky(deltaTime)
end
""", """function Sky:EditorTick(deltaTime)
    self:UpdateSky(deltaTime)
end

Script.Require("Screens")       -- GAMECUBE: the menus, the loading screen, the pad
"""),
        ("function Sky:Create()\n", "Sky.starName = StarName          -- for Screens.lua's Sky:StarFrame\n\nfunction Sky:Create()\n"),
        # A SKY'S STARS COME IN THE BACKGROUND, AND ONLY AFTER THE LAST SKY'S HAVE GONE. They are
        # eight 1024 x 1024 frames, 4 MB, held while the sky is up; two skies' worth do not fit.
        # So a change of sky first lets go of the old frames (the material keeps the one it is
        # drawing until the new one replaces it), sweeps them out, then asks for the new ones,
        # which Sky:StarFrame (Screens.lua) hands over as each arrives. The loading screen waits
        # for them (Sky:StarsReady).
        ("""    self.starFrames = {}
    for i = 1, STAR_FRAMES do
        self.starFrames[i] = LoadAsset(StarName(sky, i))
    end
""", """    -- The last sky's diamond frames let go of NOW (Asset:Release, then the sweep), not left in a
    -- dropped table until Lua's collector came round: that kept up to six 64 KB frames while the
    -- new sky's loaded on top of them. (The one on show is the material's until a new one goes up.)
    for _, w in pairs(self.window or {}) do
        if (w.asked ~= nil and w.asked.Release ~= nil) then
            w.asked:Release()
            if (w.tex ~= nil) then w.tex:Release() end
        end
    end
    self.window = {}
    RefSweep()
    self.medleyShown = nil          -- none of its diamond frames yet: the last sky's is not shown again
    if ((self.starSwap ~= nil and self.starSwap.switched and self.starSwap.sky == sky) or self.starsSky == sky) then
        -- a marathon's hold has read this sky's stars in already (Screens.lua's Sky:BeginStarSwap).
        -- (starsSky: the swap may be over already -- from ARAM it ends the tick it is switched --
        -- and without it this went on to refill all eight frames off the card, a frame a tick on
        -- the main thread: a console froze for six seconds and the twinkle stood still after.)
    elseif (self.starsHeld and self.starFrames[STAR_FRAMES] ~= nil and self.starFrames[1].ReloadFrom ~= nil) then
        -- THE SAME EIGHT TEXTURES, REFILLED: every sky's star frames are one size and format, so
        -- the new sky's texels go into the buffers already here (Texture:ReloadFrom, one frame a
        -- tick, Screens.lua's Sky:HoldStars). Freeing 4 MB of 512 KB frames and allocating 4 MB
        -- more at every change of stage cut the heap up until frames no longer fitted anywhere.
        self.starRefill = { sky = sky, next = 1 }
        self.starsHeld = false
        Log.Warning("Sky: refilling sky " .. sky .. "'s stars from the card")
    else
        -- the first sky: load it
        self.starFrames, self.starAsked, self.starRefill = {}, {}, nil
        self.starsHeld = false      -- not all eight in hand yet: see Sky:StarFrame
        collectgarbage()
        RefSweep()
        for i = 1, STAR_FRAMES do
            self.starAsked[i] = AsyncLoadAsset(StarName(sky, i))
        end
    end
"""),
        # Every sky is on the disc; finding out by LOADING a 512 KB star frame was churn.
        ("    if (sky < 0 or sky > #SKY_NAMES or LoadAsset(StarName(sky, 1)) == nil) then\n",
         "    if (sky < 0 or sky > #SKY_NAMES) then\n"),
        ("        local tex = self.starFrames[frame + 1]\n", "        local tex = self:StarFrame(frame + 1)\n"),
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
        -- frame when nothing refers to it, and a dropped handle goes on referring to it until
        -- Lua's collector has been round: asking the engine to unload one straight away is
        -- refused ("still has 1 refs"), every frame stays, and the memory runs out. So each
        -- frame's handles are RELEASED as it goes (Asset:Release), and the engine sweeps what
        -- is unheld. (It used to run a full collection every four frames instead: on hardware,
        -- now and then 30-40 ms in one frame, a hitch you could see.) An engine without Release
        -- still gets the collection.
        for i, w in pairs(self.window) do
            local behind = (cur + 1 - i) % MEDLEY_FRAMES
            if (behind > 1 and behind < MEDLEY_FRAMES - MEDLEY_AHEAD - 1) then
                if (w.asked ~= nil and w.asked.Release ~= nil) then
                    w.asked:Release()
                    if (w.tex ~= nil) then w.tex:Release() end
                    self.released = (self.released or 0) + 1
                else
                    self.dropped = (self.dropped or 0) + 1
                end
                self.window[i] = nil
            end
        end
        if ((self.released or 0) >= 2) then
            self.released = 0
            RefSweep()
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
    # The title menu is the PC's. Built with its stage select already open (coming back from a
    # stage, Screens.lua), it must start hidden: the PC's never needs to, as its menu is only
    # ever built at startup, open.
    "Menu.lua": [
        ("""    self.built = true
    self:Refresh()
    self:Layout()
end
""", """    self.built = true
    self:Refresh()
    self:Layout()
    self:Show(self.open)
end
"""),
        # (SAVE and LOAD, the PC's too, open SavePrompt.lua, which talks about slot A here. MARATHON
        # is open, as on the PC: its zones are built as it is played, see Screens.lua.)
    ],
    # The stage select is the PC's, but for its previews. Each is a clip of 16 frames, and the PC
    # loads all seven stages' clips at once: 112 pictures, 3.5 MB here. So only the stage under
    # the cursor has its clip in memory. Its still is there at once (all seven stills are held,
    # 32 KB each); the other frames are asked for in the background once the cursor has rested on
    # it for a moment -- not for every stage it passes on the way -- and the last stage's are let
    # go first. The clip plays as its frames arrive.
    "StageSelect.lua": [
        ("""    self.previewClip = {}
    local frames = (MenuLayout ~= nil and MenuLayout.preview_frames) or 1
    for i = 1, STAGES do
        self.previewClip[i] = { self.previewTex[i] }
        for k = 1, frames - 1 do
            local tex = LoadAsset(string.format("T_Menu_Preview%d_%02d", i, k))
            if (tex == nil) then break end
            self.previewClip[i][k + 1] = tex
        end
    end
""", """    self.clipOf, self.clip = nil, {}        -- GAMECUBE: one stage's clip at a time (PlayPreview)
"""),
        ("""function StageSelect:PlayPreview(deltaTime)
    self.previewClock = (self.previewClock or 0.0) + (deltaTime or 0.0)
    local clip = self.previewClip and self.previewClip[self.index]
    if (clip == nil or #clip == 0) then return end
    local fps = (MenuLayout ~= nil and MenuLayout.preview_fps) or 6
    local frame = math.floor(self.previewClock * fps) % #clip
    if (frame ~= self.previewFrame) then
        self.previewFrame = frame
        self.preview:SetTexture(clip[frame + 1])
    end
end
""", """local CLIP_REST = 0.3                    -- seconds on a stage before its clip is asked for

function StageSelect:PlayPreview(deltaTime)
    self.previewClock = (self.previewClock or 0.0) + (deltaTime or 0.0)
    local n = self.index
    local frames = (MenuLayout ~= nil and MenuLayout.preview_frames) or 1
    if (self.clipOf ~= n) then
        -- another stage: the last one's frames go now, this one's still goes up at once
        self.clipOf, self.clip, self.clipAsked = n, {}, false
        self.landedAt = self.previewClock
        self.previewFrame = -1
    end
    if (not self.clipAsked and self.previewClock - self.landedAt >= CLIP_REST) then
        self.clipAsked = true
        collectgarbage()
        RefSweep()
        for k = 1, frames - 1 do
            local name = string.format("T_Menu_Preview%d_%02d", n, k)
            self.clip[k] = { name = name, asked = AsyncLoadAsset(name) }
        end
    end
    local fps = (MenuLayout ~= nil and MenuLayout.preview_fps) or 6
    local frame = math.floor(self.previewClock * fps) % frames
    if (frame == self.previewFrame) then return end
    local tex = self.previewTex[n]
    if (frame > 0) then
        local c = self.clip[frame]
        if (c ~= nil and c.tex == nil and c.asked:IsLoaded()) then c.tex = LoadAsset(c.name) end
        tex = c and c.tex
        -- not here yet: the picture on screen stays (it is this stage's), and this is tried again
        if (tex == nil and self.previewFrame >= 0) then return end
        tex = tex or self.previewTex[n]
    end
    self.previewFrame = frame
    self.preview:SetTexture(tex)
end
"""),
    ],
}


def patch(name, text, changes):
    """Each change is (old, new) or (old, new, count): old must be there, count times."""
    for n, change in enumerate(changes):
        old, new = change[0], change[1]
        count = change[2] if len(change) > 2 else 1
        if text.count(old) < count:
            raise SystemExit("%s: change %d no longer fits the PC script:\n%s" % (name, n + 1, old[:300]))
        text = text.replace(old, new, count)
    return text


# THE MARATHON'S KIT IS READ IN SMALL FILES. As one 447 KB script it needed two blocks that size
# at once to load (the file read, then the engine's copy of it for Lua), and after one run the heap
# no longer had them: the second marathon of a session quit the game as the kit loaded. So its two
# big tables, the pieces and the flavours, go out entry by entry into MarathonKit_1.lua,
# MarathonKit_2.lua, ... of about KIT_PART bytes each, which MarathonKit.lua runs at its end; and
# the indentation, a third of the file, is dropped.
KIT_PART = 24 * 1024
KIT_SPLIT = ("pieces", "flavours")


def split_kit(text, scripts):
    for old in glob.glob(os.path.join(scripts, "MarathonKit_*.lua")):
        os.remove(old)
    lines = text.split("\n")
    main, parts, part = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        key = next((k for k in KIT_SPLIT if line == "  %s = {" % k), None)
        if key is None:
            main.append(line.strip())
            i += 1
            continue
        main.append("%s = {}," % key)
        i += 1
        while lines[i] != "  },":
            head = lines[i]
            assert head.startswith("    ") and head.endswith(" = {") and not head.startswith("     "), head
            name = head.strip()
            entry = ["MarathonKit.%s%s%s" % (key, "" if name.startswith("[") else ".", name)]
            i += 1
            while lines[i] != "    },":
                entry.append(lines[i].strip())
                i += 1
            entry.append("}")
            i += 1
            size = sum(len(l) + 1 for l in entry)
            if part and sum(len(l) + 1 for l in part) + size > KIT_PART:
                parts.append(part)
                part = []
            part += entry
        i += 1
    if part:
        parts.append(part)
    for n, part in enumerate(parts, 1):
        open(os.path.join(scripts, "MarathonKit_%d.lua" % n), "w", encoding="utf-8", newline="\n").write(
            "-- FROM the PC repo's MarathonKit.lua, by native/patch_from_pc.py (split_kit).\n" + "\n".join(part) + "\n")
    main.append('for i = 1, %d do Script.Run("MarathonKit_" .. i) end     -- the rest, in pieces: see split_kit' % len(parts))
    return "\n".join(main) + "\n"


def main():
    for name, changes in OTHERS.items():
        text = open(os.path.join(os.path.dirname(SRC), name), encoding="utf-8", newline="").read().replace("\r\n", "\n")
        text = patch(name, text, changes)
        if (name == "MarathonKit.lua"):
            text = split_kit(text, os.path.dirname(OUT))
        open(os.path.join(os.path.dirname(OUT), name), "w", encoding="utf-8", newline="\n").write(
            "-- FROM the PC repo, by native/patch_from_pc.py. Change it there.\n" + text)
    s = open(SRC, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    s = patch("SpecialStage.lua", s, CHANGES)
    open(OUT, "w", encoding="utf-8", newline="\n").write(s)
    print("wrote %s (%d changes) and %s" % (OUT, len(CHANGES), ", ".join(OTHERS)))


if __name__ == "__main__":
    main()
