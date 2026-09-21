-- FROM the PC repo, by native/patch_from_pc.py. Change it there.
-- Sky.lua
-- Sonic 2 special-stage sky: dome (SM_SkyDome) with M_Sky
-- (gradient + twinkling starfield, and the diamond show over them).
--
-- Keeps the dome on the camera, and animates it by swapping textures between
-- frames. Attach to the SkyDome StaticMesh3D node.
--
-- The animation is frames rather than anything clever with the material: stars
-- have to brighten independently of each other, and a single texture with a
-- colour or opacity applied to it can only pulse all of them together.
--
-- There are several skies. They share the dome and the material and differ only
-- in their textures, so changing sky is nothing more than which frames get
-- swapped in. `sky` picks one: 0 is the classic sky, 1-7 are the variants from
-- native/gen_sky_variants.py, in that script's order.

Sky = {}

-- Material texture slots, 1-based: the stars (with the sky gradient under them),
-- then the diamonds.
local STAR_SLOT = 1
local DIAMOND_SLOT = 2

local STAR_FRAMES = 4
local CLUSTER_FRAMES = 8

-- Keep in step with SKIES in native/gen_sky_variants.py.
local SKY_NAMES = { "Midnight", "Dawn", "Pastel", "Sunset", "Aurora", "Inferno", "Noir" }

local MEDLEY_EVERY = 1         -- every Nth frame of the PC's show is on the disc
local MEDLEY_FRAMES = 384 // MEDLEY_EVERY
local MEDLEY_AHEAD = 4         -- frames asked for ahead of the one on show
-- Loading every medley frame in one go stalls the scene for seconds, so they
-- come in a few per tick, in the order they will be shown.
local MEDLEY_LOADS_PER_TICK = 8

-- Asset names for a sky. The classic one keeps its original names.
local function StarName(sky, i)
    if (sky == 0) then
        return "T_S2Sky_Stars_" .. i
    end
    return "T_Sky" .. SKY_NAMES[sky] .. "_Stars_" .. i
end

local function MedleyName(sky, i)
    if (sky == 0) then
        return string.format("T_S2Sky_Medley_%03d", i)
    end
    return string.format("T_Sky%s_Medley_%03d", SKY_NAMES[sky], i)
end

function Sky:Create()
    -- Which sky: 0 classic, 1 Midnight, 2 Dawn, 3 Pastel, 4 Sunset, 5 Aurora,
    -- 6 Inferno, 7 Noir. Change it in the inspector or from a level script.
    self.sky = 7
    -- Frames a second, so a full twinkle is STAR_FRAMES / this.
    self.twinklesPerSecond = 12.0
    self.colourShiftsPerSecond = 2.0
    -- The preview ran at 70ms a frame, which is about 14.
    self.medleyFramesPerSecond = 14.0
    self.time = 0.0
    self.medleyTime = 0.0
    self.shownSky = -1
    -- Start the playable special stage when the game runs. The sky is the one node every
    -- scene of this project already has, so starting it from here means there is nothing to
    -- set up in the editor: SpecialStage.lua spawns the track, the rings, Sonic, the camera
    -- and the UI for itself. Untick it in the inspector to look at the sky alone.
    self.startSpecialStage = true
    TheSky = self                   -- so a stage can set `sky` to the one its palette names
    self.startedSpecialStage = false
end

function Sky:GatherProperties()
    return
    {
        { name = "sky", type = DatumType.Integer },
        { name = "startSpecialStage", type = DatumType.Bool },
        { name = "twinklesPerSecond", type = DatumType.Float },
        { name = "medleyFramesPerSecond", type = DatumType.Float },
        { name = "colourShiftsPerSecond", type = DatumType.Float },
    }
end

-- Point the frame tables at a sky. The show keeps its place: the medley clock is
-- not reset, so a change of sky is a change of colour, not a restart.
function Sky:LoadSky(sky)
    if (sky < 0 or sky > #SKY_NAMES or LoadAsset(StarName(sky, 1)) == nil) then
        Log.Warning("Sky: no sky " .. tostring(sky) .. "; using the classic one")
        sky = 0
    end
    self.shownSky = sky

    -- Held so the frames are not loaded and unloaded every time one comes back
    -- around.
    self.starFrames = {}
    for i = 1, STAR_FRAMES do
        self.starFrames[i] = LoadAsset(StarName(sky, i))
    end

    -- The diamond layer comes in two forms and the generator decides which: the
    -- medley, a long show that moves from one pattern to the next (384 frames),
    -- or, for the classic sky only, five static clusters (8 frames). If the
    -- medley's first frame exists, that is what plays.
    self.diamondFrames = {}
    local first = LoadAsset(MedleyName(sky, 1))
    self.medley = (first ~= nil)
    if (self.medley) then
        -- Load outward from wherever the show has got to, not from frame 1, so a
        -- change of sky shows its colours on the very next tick.
        self.window = {}                -- frame number -> the asset asked for (it may not be here yet)
    else
        for i = 1, CLUSTER_FRAMES do
            self.diamondFrames[i] = LoadAsset("T_S2Sky_Diamonds_" .. i)
        end
    end

    -- Force both layers to be set again on this tick.
    self.frame = -1
    self.diamondFrame = -1
end

function Sky:UpdateSky(deltaTime)
    if (self.skyMat == nil) then
        self.skyMat = LoadAsset("M_Sky")
        if (self.skyMat == nil) then
            Log.Error("Sky: M_Sky material not found")
            return
        end
        self:EnableCollision(false)
        self:EnableOverlaps(false)
    end

    local wanted = math.floor(self.sky)
    if (wanted ~= self.shownSky and not (self.shownSky == 0 and self.fellBack == wanted)) then
        self:LoadSky(wanted)
        -- Remember a sky that was asked for and is not there, or it would be
        -- looked for again on every tick.
        self.fellBack = (self.shownSky ~= wanted) and wanted or nil
    end

    self.time = self.time + deltaTime

    -- Swap the star texture only when the frame actually changes, rather than
    -- setting it every tick.
    local frame = math.floor(self.time * self.twinklesPerSecond * 0.5) % STAR_FRAMES
    if (frame ~= self.frame) then
        self.frame = frame
        local tex = self.starFrames[frame + 1]
        if (tex ~= nil) then
            self.skyMat:SetTexture(STAR_SLOT, tex)
        end
    end

    local dframe
    if (self.medley) then
        local fps = self.medleyFramesPerSecond / MEDLEY_EVERY
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
    else
        dframe = math.floor(self.time * self.colourShiftsPerSecond) % CLUSTER_FRAMES
    end

    if (dframe ~= self.diamondFrame) then
        local dtex = self.diamondFrames[dframe + 1]
        if (self.medley) then dtex = self.medleyShown end
        if (dtex ~= nil) then
            self.diamondFrame = dframe
            self.skyMat:SetTexture(DIAMOND_SLOT, dtex)
        end
    end

    -- Camera-anchored dome.
    local world = self:GetWorld()
    local cam = world and world:GetActiveCamera()
    if (cam ~= nil) then
        self:SetWorldPosition(cam:GetWorldPosition())
    end
end

function Sky:Tick(deltaTime)
    -- Tick is the GAME's; the editor calls EditorTick. So the stage never starts in the editor.
    if (self.startSpecialStage and not self.startedSpecialStage) then
        self.startedSpecialStage = true
        local stage = self:GetWorld():SpawnNode("Node3D")
        stage:SetName("SpecialStage")
        stage:SetScript("SpecialStage")
    end
    self:UpdateSky(deltaTime)
end

function Sky:EditorTick(deltaTime)
    self:UpdateSky(deltaTime)
end
