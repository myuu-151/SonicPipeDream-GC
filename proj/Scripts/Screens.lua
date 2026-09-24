-- Screens.lua (GAMECUBE ONLY: this file is not made from the PC repo)
--
-- How the game gets from the menus to a stage and back, on a machine with 24 MB.
--
-- The PC's Sky.lua keeps all three screens in one world at once -- the menu, the stage select,
-- and the stage -- and only HIDES the ones not in use. Here that does not fit: the menus' art,
-- the stage select's clip and a stage's pipe, emerald and sky are more than there is. So the
-- menus and a stage are never loaded together. Choosing a stage:
--
--     1. the loading screen goes up (Loading.lua), and is drawn once
--     2. the menus are DESTROYED, and what they held is let go
--     3. the stage's data is read, its sky set, and every asset it needs is asked for IN THE
--        BACKGROUND (AsyncLoadAsset), so the loading screen keeps moving
--     4. once all of it has arrived the PC's own StartSpecialStage runs, and finds it in memory
--     5. the loading screen comes down on the stage's first frame
--
-- and leaving the stage (EXIT from the pause menu, or its emerald taken) is the same the other
-- way: the stage's pipe and data are let go and the menus built again, at the stage select,
-- with that stage under the cursor.
--
-- MARATHON goes the same way, with its first zone BUILT behind the loading screen (MarathonGen.lua,
-- a slice a frame, after the pipe has arrived) and every piece of track loaded, not just the
-- first zone's: the zones after it are made as it is played. Leaving it goes back to the title
-- menu, and the generator and its kit are let go of.
--
-- The sky is not changed on the way back: the PC leaves the last stage's sky up behind the
-- menus too, and here it saves loading a sky's 4 MB of stars twice.
--
-- Sky.lua requires this at its end, so these replace the PC's own Sky:ShowMenu and wrap its
-- Tick. The PC's Sky:StartSpecialStage is used as it is.

Script.Require("PadInput")
Script.Require("GameOptions")   -- the marathon's and the time attack's settings; which one is next
Script.Require("GcTest")        -- switches for testing in Dolphin; all off unless set there
Script.Require("SaveInfo")      -- the save's name and icon on the memory card screen

-- Every save written from here on carries them (engine: System_Dolphin.cpp, SYS_WriteSave).
if (System.SetSaveInfo ~= nil and SaveInfo ~= nil) then
    System.SetSaveInfo(SaveInfo.title, SaveInfo.description, SaveInfo.icon, SaveInfo.banner)
end

-- The pipe (and the rings) are vertex-coloured and unlit: kept as position and colour alone they
-- take a third of the memory -- 1.5 MB a stage instead of 4.2 -- and that headroom is what keeps
-- the big pieces loading after many changes of stage. (Engine: GxUtils.cpp, BindStaticMesh.)
if (Renderer.SetCompactUnlitMeshes ~= nil) then Renderer.SetCompactUnlitMeshes(true) end

local STAGES = 7
local WAIT_AT_MOST = 30.0           -- seconds: a stage starts even if something never arrives,
                                    -- rather than leaving the loading screen up for ever
local MARATHON_BUILD_MS = 30        -- a marathon's first zone: milliseconds of building a frame,
                                    -- behind the loading screen (it keeps moving)
local MARATHON_BREATH = 40          -- MarathonGen.BREATH here: its work between yields

-- Everything SpecialStage:Build loads, the first time a stage is played. Asked for with the
-- stage's own assets, so that first time is no slower to leave the loading screen.
local function BuildAssets()
    local names = { "SM_Ring", "SM_Bomb", "SM_PlayerBall", "SM_FxQuad", "SM_FxQuadBoom", "M_Explosion",
                    "SM_FxQuadRazor", "SM_FxQuadPuff", "SM_FxTrace", "SW_SpinRev", "SW_SpinRelease",
                    -- every effect a stage plays, loaded at boot with the rest: the checkpoint and the
                    -- emerald, the biggest, were loaded the first time each played and in a marathon's
                    -- cut-up heap that could fail -- and then they were silent all run
                    "SW_Ring", "SW_Jump", "SW_Checkpoint", "SW_GetEmerald", "SW_Fail", "SW_LoseRings",
                    "SW_Explosion", "SW_ExitStage",
                    "SM_Shadow", "SM_Sonic_Idle_00", "SM_Emerald",
                    "T_UI_Emblem", "T_UI_EmblemRed", "T_UI_Flag", "T_UI_FlagLeft", "T_UI_SonicRings",
                    "T_UI_Thumb", "T_UI_ThumbDown", "T_UI_Total", "T_UI_Lives" }
    for i = 0, 11 do names[#names + 1] = string.format("SM_Ring_%02d", i) end
    for i = 0, 2 do names[#names + 1] = "T_Explosion_" .. i end
    for i = 0, 15 do
        names[#names + 1] = string.format("SM_Sonic_Run_%02d", i)
        names[#names + 1] = string.format("SM_Sonic_Thumbs_%02d", i)
    end
    for i = 1, 5 do names[#names + 1] = "T_UI_Start_" .. i end
    return names
end

local function Sweep()
    collectgarbage()
    RefSweep()
end

-- One stage's table at a time: StageData7 alone is about half a megabyte once read. Script.Run,
-- not Require: Require reads a file once in the life of the game, and a stage let go of has to
-- be readable again.
function LoadStageData(n)
    for k = 1, STAGES do
        if (k ~= n) then _G["StageData" .. k] = nil end
    end
    if (_G["StageData" .. n] == nil) then Script.Run("StageData" .. n) end
    return _G["StageData" .. n]
end

-- ------------------------------------------------------------------ the menus
function Sky:ShowMenu()
    -- What every stage uses -- Sonic, the HUD's art, the rings, the bomb, the effects -- is loaded
    -- ONCE, here at boot, before anything else, and kept for the whole session (the stage's NODES
    -- are still torn down between stages; see TeardownStage). Loaded first it sits together at
    -- the bottom of the heap, out of the way; loaded and freed with each stage it was 3 MB more
    -- of the churn that cut the heap up.
    self.kept = {}
    for _, name in ipairs(BuildAssets()) do self.kept[#self.kept + 1] = LoadAsset(name) end
    self:SpawnLoading()
    self:SpawnMenus(nil)
end

function Sky:SpawnLoading()
    if (self.loadingNode ~= nil) then return end
    local world = self:GetWorld()
    self.loadingNode = world:SpawnNode("Canvas")
    self.loadingNode:SetName("Loading")
    self.loadingNode:SetScript("Loading")
end

-- The menu and the stage select, built afresh. `selectAt` opens the stage select straight
-- away with that stage under the cursor (coming back from it); nil opens the menu.
function Sky:SpawnMenus(selectAt)
    local world = self:GetWorld()
    self.menuNode = world:SpawnNode("Canvas")
    self.menuNode:SetName("Menu")
    self.menuNode:SetScript("Menu")
    self.selectNode = world:SpawnNode("Canvas")
    self.selectNode:SetName("StageSelect")
    self.selectNode:SetScript("StageSelect")
    self.saveNode = world:SpawnNode("Canvas")
    self.saveNode:SetName("SavePrompt")
    self.saveNode:SetScript("SavePrompt")
    self.optionsNode = world:SpawnNode("Canvas")
    self.optionsNode:SetName("OptionsPrompt")
    self.optionsNode:SetScript("OptionsPrompt")

    -- TheMenu, TheStageSelect and TheSavePrompt are set by each script's Create, which has run.
    TheStageSelect:Close()
    TheStageSelect.onChoose = function(stage) self:GoToStage(stage) end
    TheStageSelect.onBack = function()
        TheStageSelect:Close()
        TheMenu:Open()
    end
    TheMenu.onChoose = function(key)
        if (key == "main_game") then
            TheMenu:Close()
            TheStageSelect:Open()
        elseif (key == "options") then
            TheMenu.busy = true
            TheOptions.onStart = nil
            TheOptions:Open()
        elseif (key == "save" or key == "load") then
            -- the memory card prompt, over the menu; the menu keeps still until it closes
            TheMenu.busy = true
            TheSavePrompt:Open(key)
        elseif (key == "marathon" or key == "time_attack") then
            -- its setup first (OptionsPrompt.lua); START there begins the run. A time attack is
            -- the same run against the clock (SpecialStage.lua: data.timeAttack).
            local run = (key == "time_attack") and "timeAttack" or "marathon"
            TheMenu.busy = true
            TheOptions.onStart = function()
                TheOptions.onStart = nil
                self:GoToMarathon(run)
            end
            TheOptions:Open(run)
        end
    end
    TheSavePrompt.onClose = function() TheMenu.busy = false end
    TheOptions.onClose = function() TheMenu.busy = false end
    if (selectAt ~= nil) then
        TheMenu:Close()
        TheStageSelect.index = selectAt
        TheStageSelect:Open()
        -- the PC's test hooks (S2_MENU_CHOOSE, S2_SELECT_PICK, S2_SELECT_AT) are for the first
        -- time through: built again, the menus would otherwise pick again, for ever
        TheMenu.autoChoose, TheStageSelect.autoPick, TheStageSelect.autoAt = false, false, false
    end
end

-- Gone, and everything they held let go: their art, the stage select's clip.
function Sky:DropMenus()
    if (self.menuNode ~= nil) then self.menuNode:Destruct() end
    if (self.selectNode ~= nil) then self.selectNode:Destruct() end
    if (self.saveNode ~= nil) then self.saveNode:Destruct() end
    if (self.optionsNode ~= nil) then self.optionsNode:Destruct() end
    self.menuNode, self.selectNode, self.saveNode, self.optionsNode = nil, nil, nil, nil
    TheMenu, TheStageSelect, TheSavePrompt, TheOptions = nil, nil, nil, nil
    Sweep()
end

-- ------------------------------------------------------------------ into a stage
function Sky:GoToStage(stage)
    TheStageSelect:Close()
    local won = TheStageSelect.won ~= nil and TheStageSelect.won[stage]
    TheLoading:Show(stage, won)
    self.going = { stage = stage, step = 0, clock = 0.0 }
end

-- The marathon's run: its seed now, and from the seed its first colours (as SpecialStage's
-- JoinZone draws them: keep the two alike), so its sky and pipe can be loaded before the zone is
-- built. Every run is new: the time of day and the milliseconds since the game started.
local MARATHON_PIECES = { "Straight", "CornerLeft", "CornerRight", "Drop", "Rise" }
local ARCH_RINGS = 9                -- the rainbow arch's rings, in every stage and the marathon

local function MarathonFirstPalette(seed)
    local rng = math.floor((seed * 1103515245 + 12345) % 2147483648)
    return math.floor((rng // 65536) % 7) + 1
end

function Sky:GoToMarathon(run)
    GameOptions.run = run or "marathon"
    TheMenu:Close()
    TheLoading:Show((GameOptions.run == "timeAttack") and "time_attack" or "marathon")
    local seed = 12345
    if (os ~= nil and os.time ~= nil) then seed = math.floor(os.time()) * 1000 end
    if (System.GetClockMs ~= nil) then seed = seed + System.GetClockMs() end
    seed = math.floor(seed % 2147483647)
    self.going = { stage = "Marathon", step = 0, clock = 0.0, seed = seed, palette = MarathonFirstPalette(seed) }
end

-- The stage started, the loading screen still up over it.
function Sky:StartGoing(g)
    self:StartSpecialStage(g.stage)
    -- Built NOW, not on its own first tick next frame: Build spawns the HUD, and the
    -- loading screen has to be moved back over it in the same frame, or the HUD shows
    -- through it for a frame.
    if (not TheSpecialStage.built) then TheSpecialStage:Build() end
    self.loadingNode:Attach(self:GetWorld():GetRootNode(), false)
    if (g.stage == "Marathon") then
        TheSpecialStage.onExit = function() self:BackToSelect(nil) end
        TheSpecialStage.onFinished = function() self:BackToSelect(nil) end
        -- The recolour's staging buffers, taken NOW, behind the loading screen, and kept for the run
        -- (StaticMesh:StageColorsFrom): taken mid-game, at a change of colours, they made the
        -- picture flash with garbage for as long as they were held.
        -- (every piece, not just the first zone's: a later zone may bring one in)
        for _, piece in ipairs(MARATHON_PIECES) do
            TheSpecialStage:PieceMesh("SM_Piece_" .. piece .. "_P", g.palette)
            TheSpecialStage:PieceMesh("SM_Piece_" .. piece .. "_Gloss_P", g.palette)
        end
        for full, mesh in pairs(TheSpecialStage.pieceMeshes or {}) do
            if (mesh and mesh.StageColorsFrom ~= nil) then mesh:StageColorsFrom(full, 0, 0) end
        end
    else
        TheSpecialStage.onExit = function() self:BackToSelect(nil) end
        TheSpecialStage.onFinished = function(won) self:BackToSelect(won) end
    end
    g.step = 3
end

function Sky:TickGoing(deltaTime)
    local g = self.going
    g.clock = g.clock + deltaTime
    if (g.step == 0) then
        g.step = 1                              -- the loading screen is drawn this frame
    elseif (g.step == 1) then
        self:DropMenus()
        local data
        if (g.stage == "Marathon") then
            -- not built yet: its sky is known from the seed (see GoToMarathon)
            data = { sky = ({ 0, 4, 6, 3, 5, 2, 1 })[g.palette] }     -- stage_palettes.py SKY
        else
            data = LoadStageData(g.stage)
            if (data == nil) then
                Log.Error("Screens: no StageData" .. g.stage)
                g.stage, data = 1, LoadStageData(1)
            end
        end
        -- The stage's sky, changed NOW and before anything of the stage's is asked for: the last
        -- sky's stars go (4 MB, in eight 512 KB frames) and the new ones are first in the queue.
        -- Left to UpdateSky's next tick, the stage's pieces were queued ahead of them, took the
        -- big free blocks, and some star frames never found room: the new sky then twinkled
        -- between its own frames and the old sky's.
        if (data.sky ~= nil and data.sky ~= self.shownSky) then
            self.sky = data.sky
            self:LoadSky(data.sky)
            self.fellBack = (self.shownSky ~= data.sky) and data.sky or nil
        end
        g.step = 15                             -- the stars first, alone: see step 15
    elseif (g.step == 15) then
        -- THE ORDER THINGS COME IN IS THE DIFFERENCE BETWEEN FITTING AND NOT. The heap has
        -- megabytes free at this point, but in pieces; a star frame needs 512 KB in one block
        -- (and briefly twice that as it is read), a drop or rise a few blocks of up to 640 KB.
        -- Asked for together with everything else, the small things landed in the big holes
        -- first and some star frames never found room (the sky then twinkled half old, half
        -- new). So: the stars alone, into the heap as the menus left it; then the stage, its
        -- biggest pieces first. (Nothing else is loading meanwhile: Sky:Tick holds the sky still,
        -- and its streaming with it, while the loading screen is up.)
        if (not self:StarsReady() and g.clock < WAIT_AT_MOST) then return end
        local names, seen = {}, {}
        local function Want(name)
            if (not seen[name]) then
                seen[name] = true
                names[#names + 1] = name
            end
        end
        if (g.stage == "Marathon") then
            -- every piece: the zones to come are not made yet, and could use any of them
            for _, piece in ipairs(MARATHON_PIECES) do
                Want("SM_Piece_" .. piece .. "_P" .. g.palette)
                Want("SM_Piece_" .. piece .. "_Gloss_P" .. g.palette)
            end
            Want("SM_Emerald_1")
            for i = 0, ARCH_RINGS - 1 do Want("SM_RingRainbow_" .. i) end
        else
            local data = _G["StageData" .. g.stage]
            for _, piece in ipairs(data.pieces) do
                Want(piece.mesh .. data.palette)
                Want(piece.gloss .. data.palette)
            end
            Want("SM_Emerald_" .. g.stage)
            for i = 0, data.arch.rings - 1 do Want("SM_RingRainbow_" .. i) end
        end
        if (TheSpecialStage == nil or not TheSpecialStage.built) then
            for _, name in ipairs(BuildAssets()) do Want(name) end
        end
        local function Rank(name)
            if (name:find("Drop") or name:find("Rise")) then return 0 end
            if (name:find("Corner")) then return 1 end
            if (name:find("SM_Piece")) then return 2 end
            return 3
        end
        for i, name in ipairs(names) do names[i] = { name = name, rank = Rank(name), at = i } end
        table.sort(names, function(a, b)
            if (a.rank ~= b.rank) then return a.rank < b.rank end
            return a.at < b.at
        end)
        g.asked = {}
        for _, n in ipairs(names) do g.asked[#g.asked + 1] = AsyncLoadAsset(n.name) end
        g.step, g.clock = 2, 0.0
    elseif (g.step == 2) then
        local ready = self:StarsReady()
        for _, a in ipairs(g.asked) do
            if (not a:IsLoaded()) then ready = false end
        end
        if (ready or g.clock > WAIT_AT_MOST) then
            if (not ready) then Log.Warning("Screens: a stage asset never arrived; starting anyway") end
            if (g.stage == "Marathon") then
                g.step = 25                     -- its first zone, built now the pipe is in
            else
                self:StartGoing(g)
            end
        end
    elseif (g.step == 25) then
        -- The generator and its kit (read in this tick: the loading screen stands still for it),
        -- then the first zone, a slice a frame.
        if (MarathonGen == nil) then Script.Run("MarathonGen") end
        -- Yielding ten times as often as on the PC: a slice there is a few milliseconds' work, and
        -- here it took forty. And the collector kept close behind: a zone's building makes some
        -- 10 MB of short-lived tables, and left to Lua's usual pace that garbage filled the heap
        -- until the engine's own allocations failed. (Lua 5.3 has no generational mode.)
        MarathonGen.BREATH = MARATHON_BREATH
        collectgarbage("setpause", 110)
        collectgarbage("setstepmul", 400)
        local seed = g.seed
        g.gen = coroutine.create(function() return MarathonGen.BuildZone(seed, 1) end)
        g.genClock, g.step = 0.0, 26
    elseif (g.step == 26) then
        g.genClock = g.genClock + deltaTime
        local t0 = System.GetClockMs and System.GetClockMs() or nil
        repeat
            local ok, zone = coroutine.resume(g.gen)
            if (not ok or coroutine.status(g.gen) == "dead") then
                if (not ok) then Log.Error("MarathonGen: " .. tostring(zone)) end
                self.zone1Seconds = g.genClock
                MarathonFirstZone, MarathonSeed = ok and zone or nil, g.seed
                g.gen = nil
                self:StartGoing(g)
                return
            end
        until (t0 == nil or System.GetClockMs() - t0 >= MARATHON_BUILD_MS)
    elseif (g.step == 3) then
        -- up once the stage has built itself and drawn a frame
        -- ...and the new sky's first diamond frame is up (the sky runs again from here, and until
        -- a frame of its own arrives the material still has the last sky's)
        local s = TheSpecialStage
        local skyUp = (not self.medley) or self.medleyShown ~= nil or g.clock > WAIT_AT_MOST
        if (s ~= nil and s.built and s.data ~= nil and s.stage == g.stage and skyUp) then
            g.step = 4
        end
    else
        TheLoading:Hide()
        self.going = nil                        -- and the handles with it: the stage holds its own
    end
end

-- ------------------------------------------------------------------ and back out
-- The stage has already put itself away (SpecialStage:Leave): its pieces are destroyed and its
-- music stopped. On the PC what it keeps between stages -- Sonic, the HUD, the ring and bomb
-- nodes, the music -- stays, hidden, for next time.
--
-- HERE THE NODES ALL GO, and the stage's own pipe, data and emerald with them; the assets every
-- stage shares stay loaded (Sky:ShowMenu keeps them, loaded at boot). What must not happen is
-- the heap being cut up between stages: see ShowMenu, Sky.lua's LoadSky (the stars are refilled
-- in place) and the engine's BigBlockCache_Dolphin.cpp.
function Sky:TeardownStage()
    local s = TheSpecialStage
    if (s ~= nil) then
        local function Kill(node)
            if (node ~= nil) then node:Destruct() end
        end
        if (TheSpecialStageMusic ~= nil) then TheSpecialStageMusic:Stop() end
        s:ClearStage()
        for _, pair in ipairs(s.pool or {}) do
            Kill(pair.node)
            Kill(pair.shadow)
        end
        for _, nodes in pairs(s.fxPool or {}) do
            for _, node in ipairs(nodes) do Kill(node) end
        end
        for _, fx in ipairs(s.fx or {}) do Kill(fx.node) end
        for _, node in ipairs(s.tubeNodes or {}) do Kill(node) end      -- the spin dash's traced tube
        Kill(s.tubeCap)
        Kill(s.traceNode)
        for _, node in ipairs({ s.player, s.playerShadow, s.uiNode, s.debugNode }) do Kill(node) end
        local world = self:GetWorld()
        Kill(world:FindNode("SpecialStageMusic"))
        Kill(world:FindNode("StageSun"))
        s:Destruct()                                -- the stage's own node
    end
    TheSpecialStage, TheSpecialStageUI, TheSpecialStageMusic = nil, nil, nil
    self.startedSpecialStage = false                -- so StartSpecialStage builds it afresh
    for k = 1, STAGES do _G["StageData" .. k] = nil end
    MarathonGen, MarathonKit, MarathonFirstZone, MarathonSeed = nil, nil, nil, nil
    collectgarbage("setpause", 200)                 -- Lua's own pace again (see TickGoing, step 25)
    collectgarbage("setstepmul", 200)
    Sweep()
end

function Sky:BackToSelect(won)
    local stage = TheSpecialStage and TheSpecialStage.stage or 1
    TheLoading:Show(nil)
    self.returning = { stage = stage, won = won, step = 0 }
end

function Sky:TickReturning(deltaTime)
    local r = self.returning
    if (r.step == 0) then
        r.step = 1                              -- the loading screen is drawn this frame
    elseif (r.step == 1) then
        self:TeardownStage()
        self:SpawnMenus((r.stage ~= "Marathon") and r.stage or nil)     -- a marathon: the title menu
        -- An emerald taken is remembered, on the memory card (StageSelect:SetWon); all seven
        -- light MARATHON up, which the stage select checks as it builds.
        if (r.won ~= nil) then TheStageSelect:SetWon(r.won, true) end
        r.step = 2
    elseif (r.step == 2) then
        if (TheStageSelect ~= nil and TheStageSelect.built) then r.step = 3 end
    else
        TheLoading:Hide()
        self.returning = nil
    end
end

-- ------------------------------------------------------------------ the sky's stars
-- Sky.lua (patched) asks for a sky's 8 star frames in the background; these read them back.
-- Nothing until ALL EIGHT have arrived: a twinkle through some of the new sky's frames and
-- some of the old's (the material keeps the last one it was given) is the two skies clashing.
function Sky:StarFrame(i)
    if (not self.starsHeld) then return nil end
    return self.starFrames[i]
end

-- Take each star frame in hand (LoadAsset) THE TICK IT ARRIVES, before anything else in the
-- tick runs. What AsyncLoadAsset hands back does not keep the asset alive, and the sky's own
-- streaming sweeps unheld assets several times a second (Sky.lua's medley): a frame that
-- arrived and was swept before it was taken was simply gone, and its handle never said
-- loaded again -- 3 of the 8 went missing like that, and the sky twinkled between its own
-- frames and the last sky's. A frame still missing after a while is asked for again.
local STAR_ASK_AGAIN = 1.5          -- seconds
function Sky:HoldStars(deltaTime)
    local w = self.starSwap
    if (w ~= nil) then
        -- A marathon's change of sky under way: the frames are being written, so the twinkle
        -- stays still (starsHeld false) until the last is in. (Left to the code below, it found
        -- all eight "loaded", held them again at once, and went on showing frames half written
        -- -- the sky dome's texture torn mid-read flashed over the whole picture.)
        if (w.switched) then
            if (w.k <= #w.order) then self:StarSwapPiece(w) end
            if (w.k > #w.order) then
                self.starSwap, self.starsHeld = nil, true
                self.frame = -1
            end
        end
        return
    end
    if (self.starRefill ~= nil) then
        -- a change of sky: the eight textures refilled in place, one a tick (see Sky.lua's LoadSky)
        local r = self.starRefill
        if (self.starFrames[r.next]:ReloadFrom(self.starName(r.sky, r.next))) then
            r.next = r.next + 1
            if (r.next > #self.starFrames) then
                self.starRefill, self.starsHeld = nil, true
                self.frame = -1                 -- the new stars go up on this tick
            end
        else
            -- could not (the engine refuses a different size or format): load them afresh
            Log.Warning("Sky: star frames not refilled in place; loading them")
            self.starRefill = nil
            self.starFrames, self.starAsked = {}, {}
            collectgarbage()
            RefSweep()
            for i = 1, 8 do self.starAsked[i] = AsyncLoadAsset(self.starName(r.sky, i)) end
        end
        return
    end
    if (self.starsHeld or self.starAsked == nil) then return end
    self.starWait = (self.starWait or 0.0) + deltaTime
    local all = true
    for k, asked in pairs(self.starAsked) do
        if (self.starFrames[k] == nil) then
            if (asked:IsLoaded()) then
                self.starFrames[k] = LoadAsset(self.starName(self.shownSky, k))
            elseif (self.starWait >= STAR_ASK_AGAIN) then
                self.starAsked[k] = AsyncLoadAsset(self.starName(self.shownSky, k))
            end
        end
        if (self.starFrames[k] == nil) then all = false end
    end
    if (self.starWait >= STAR_ASK_AGAIN) then self.starWait = 0.0 end
    self.starsHeld = all
    if (all) then self.frame = -1 end           -- the new stars go up on this tick
end

-- ------------------------------------------------------------------ a marathon's change of sky
-- The hold between two zones changes the sky, and not behind a loading screen: Sonic runs on.
-- The eight star frames (which carry the sky's colours too) are refilled in place, as a change of
-- stage does, but A PIECE AT A TIME (Texture:ReloadPart) through the hold, not a frame a tick --
-- 512 KB read in one go stops the game for a moment. The twinkle holds still meanwhile, on the
-- frame it was showing, which is refilled last: all the others first, then at the switch (the pipe
-- recoloured in the same frame, see SpecialStage:ApplyRecolour) a refilled one goes up, and the
-- last one is read in behind it.
local STAR_PIECE = 32 * 1024

function Sky:BeginStarSwap(sky)
    self.starSwap = nil
    if (not self.starsHeld or sky == self.shownSky or self.starFrames[8] == nil
            or self.starFrames[1].ReloadPart == nil) then
        return                                  -- then the sky changes the ordinary way
    end
    local shown = (self.frame ~= nil and self.frame >= 0) and (self.frame + 1) or 1
    local order = {}
    for i = 1, 8 do
        if (i ~= shown) then order[#order + 1] = i end
    end
    order[#order + 1] = shown
    self.starSwap = { sky = sky, order = order, k = 1, at = 0, before = 7 }
    self.starsHeld = false                      -- the twinkle holds still (Sky:StarFrame)
end

function Sky:StarSwapPiece(w)
    local i = w.order[w.k]
    local nextAt, total = self.starFrames[i]:ReloadPart(self.starName(w.sky, i), w.at, STAR_PIECE)
    if (nextAt < 0) then
        Log.Warning("Sky: star frame " .. i .. " not refilled")
        w.k, w.at = w.k + 1, 0
    elseif (nextAt >= total) then
        w.k, w.at = w.k + 1, 0
    else
        w.at = nextAt
    end
end

-- One piece; true once every frame but the one on show holds the new sky.
function Sky:StepStarSwap()
    local w = self.starSwap
    if (w == nil or w.switched) then return true end
    if (w.k <= w.before) then self:StarSwapPiece(w) end
    return w.k > w.before
end

-- The switch: a refilled frame up at once. The stage sets `sky` after this; LoadSky then leaves
-- the stars alone (patch_from_pc.py) and Sky:HoldStars reads the last frame in.
function Sky:SwitchStars()
    local w = self.starSwap
    if (w == nil) then return end
    w.switched = true
    if (self.skyMat ~= nil) then self.skyMat:SetTexture(1, self.starFrames[w.order[1]]) end
end

-- Left part way (the run ended in the hold): the frames are some of each sky, so all eight are
-- read again for the sky that is up, the ordinary way.
function Sky:CancelStarSwap()
    local w = self.starSwap
    if (w == nil) then return end
    self.starSwap = nil
    self.starsHeld = true
    local sky = w.switched and w.sky or self.shownSky
    self.shownSky = -1                          -- so UpdateSky loads it: all eight refilled in place
    self.sky = sky
end

-- All of the sky on show has arrived.
function Sky:StarsReady()
    if (self.sky ~= self.shownSky and not (self.shownSky == 0 and self.fellBack == math.floor(self.sky))) then
        return false                            -- asked for, not yet taken up by UpdateSky
    end
    return self.starsHeld
end

-- ------------------------------------------------------------------ testing
-- For testing without a pad. On the PC runtime, in the style of the PC's S2_TEST_* hooks,
-- S2_TEST_EXIT=<seconds> leaves the stage that long after it starts, as EXIT from the pause menu
-- does; on the console, where there is no environment, GcTest.lua's switches do the same.
function Sky:TestExit(deltaTime)
    if (self.testExit == nil) then
        self.testExit = (os ~= nil and os.getenv ~= nil and tonumber(os.getenv("S2_TEST_EXIT") or ""))
                        or (GcTest ~= nil and GcTest.exit) or false
    end
    local s = TheSpecialStage
    if (not self.testExit or s == nil or not s.built or s.active == false or self.going ~= nil) then
        self.inStageFor = 0.0
        return
    end
    self.inStageFor = (self.inStageFor or 0.0) + deltaTime
    if (self.inStageFor >= self.testExit) then
        self.inStageFor = 0.0
        s:Leave()
        if (s.onExit ~= nil) then s.onExit() end
    end
end

-- GcTest.pick: the stage select chooses by itself, after showing for GcTest.wait seconds.
function Sky:TestPick(deltaTime)
    if (GcTest == nil or GcTest.pick == nil or self.going ~= nil or self.returning ~= nil) then return end
    if (GcTest.thenMarathon and self.picked) then return end
    local select = TheStageSelect
    if (select == nil or not select.built) then
        self.pickIn = GcTest.wait or 3.0
        return
    end
    if (TheMenu ~= nil and TheMenu.open) then
        TheMenu:Close()
        select:Open()
    end
    self.pickIn = (self.pickIn or GcTest.wait or 3.0) - deltaTime
    if (self.pickIn > 0.0) then return end
    local stage = GcTest.pick
    if (stage == 0) then
        self.cycle = (self.cycle or 0) % STAGES + 1
        stage = self.cycle
    end
    select.index = stage
    select:PlaceSelection()
    select:Refresh()
    self.picked = true
    self:GoToStage(stage)
end

-- GcTest.marathon: the title menu chooses MARATHON by itself, after GcTest.wait seconds.
-- GcTest.hold = seconds: in a marathon, a change of colours that often, as a zone's hold makes.
function Sky:TestMarathon(deltaTime)
    if (GcTest == nil) then return end
    if (GcTest.marathon and self.going == nil and self.returning == nil and TheMenu ~= nil
            and TheMenu.built and TheMenu.open and not TheMenu.busy) then
        self.marathonIn = (self.marathonIn or GcTest.wait or 3.0) - deltaTime
        if (self.marathonIn <= 0.0) then
            self.marathonIn = nil
            self:GoToMarathon(GcTest.timeAttack and "timeAttack" or "marathon")
        end
    end
    -- GcTest.thenMarathon: after `pick`'s one stage, back on the stage select, a marathon
    if (GcTest.thenMarathon and self.picked and self.going == nil and self.returning == nil
            and TheStageSelect ~= nil and TheStageSelect.built and TheStageSelect.open) then
        self.marathonIn = (self.marathonIn or GcTest.wait or 3.0) - deltaTime
        if (self.marathonIn <= 0.0) then
            self.marathonIn = nil
            TheStageSelect:Close()
            self:GoToMarathon(GcTest.timeAttack and "timeAttack" or "marathon")
        end
    end
    local s = TheSpecialStage
    if (GcTest.hold and s ~= nil and s.built and s.data ~= nil and s.data.marathon and self.going == nil
            and s.holding == nil) then
        self.holdIn = (self.holdIn or GcTest.hold) - deltaTime
        if (self.holdIn <= 0.0) then
            self.holdIn = nil
            s.holding = { clock = 0.0, to = GcTest.holdTo or (s.palette % 7 + 1) }
        end
    end
end

-- GcTest.free: free memory in the corner of every screen, drawn over everything.
function Sky:TestFree()
    if (GcTest == nil or not GcTest.free or System.GetFreeMemory == nil) then return end
    if (self.freeText == nil) then
        local canvas = self:GetWorld():SpawnNode("Canvas")
        canvas:SetAnchorMode(AnchorMode.TopLeft)
        canvas:SetPosition(0.0, 0.0)
        canvas:SetDimensions(640.0, 480.0)
        self.freeNode = canvas
        self.freeText = canvas:CreateChild("Text")
        self.freeText:SetAnchorMode(AnchorMode.TopLeft)
        self.freeText:SetPosition(470.0, 22.0)
        self.freeText:SetTextSize(14.0)
        self.freeText:SetColor(Vec(0.3, 0.9, 1.0, 1.0))
    end
    local free = System.GetFreeMemory() // 1024
    local s = TheSpecialStage
    if (s ~= nil and s.data ~= nil and s.data.marathon) then
        -- a marathon: the zones built, how long the next is taking, the first one's time, and the
        -- milliseconds a frame its building and the whole stage's tick take (measured here)
        if (s.timedBy ~= self and System.GetClockMs ~= nil) then
            s.timedBy = self
            local gen, tick = s.TickMarathonGen, s.Tick
            s.TickMarathonGen = function(me)
                local t = System.GetClockMs()
                gen(me)
                self.genMs = (self.genMs or 0) + System.GetClockMs() - t
            end
            s.Tick = function(me, dt)
                local t = System.GetClockMs()
                tick(me, dt)
                self.tickMs = (self.tickMs or 0) + System.GetClockMs() - t
                self.ticks = (self.ticks or 0) + 1
            end
        end
        if ((self.ticks or 0) >= 30) then
            self.genAvg, self.tickAvg = self.genMs / self.ticks, self.tickMs / self.ticks
            self.genMs, self.tickMs, self.ticks = 0, 0, 0
        end
        if (s.gen ~= nil) then
            self.genFor = (self.genFor or 0.0) + (self.lastTick or 0.0)
        elseif (self.genFor ~= nil) then
            self.lastGen, self.genFor = self.genFor, nil
        end
        self.freeText:SetText(string.format("free %d KB  zones %d  gen %.1f  last %.1f  z1 %.1f  pal %d%s\n"
                                            .. "tick %.1f ms  gen %.1f ms  frame %d  lua %d KB  %s", free,
                                            s.zonesBuilt or 0, self.genFor or 0.0, self.lastGen or 0.0,
                                            self.zone1Seconds or 0.0, s.palette or 0,
                                            (s.holding ~= nil) and "  HOLD" or "",
                                            self.tickAvg or 0.0, self.genAvg or 0.0, math.floor(s.frame or 0),
                                            math.floor(collectgarbage("count")), s.genError or ""))
        self.freeText:SetPosition(28.0, 340.0)
    elseif (s ~= nil and s.sounds ~= nil) then
        -- a stage: which of its sounds have been asked for, and any that would not load
        local got, failed = {}, {}
        for name, snd in pairs(s.sounds) do
            if (snd) then got[#got + 1] = name else failed[#failed + 1] = name end
        end
        self.freeText:SetText(string.format("free %d KB  sounds %s\nFAILED %s", free, table.concat(got, " "),
                                            table.concat(failed, " ")))
        self.freeText:SetPosition(28.0, 340.0)
    else
        self.freeText:SetText(string.format("free %d KB", free))
        self.freeText:SetPosition(470.0, 22.0)
    end
    -- and on the loading screen, which covers this: how far the loading has got
    if (TheLoading ~= nil) then
        local line = string.format("free %d KB", free)
        local g = self.going
        if (g ~= nil and g.asked ~= nil) then
            local n = 0
            for _, a in ipairs(g.asked) do if (a:IsLoaded()) then n = n + 1 end end
            local stars = 0
            for _, a in pairs(self.starAsked or {}) do if (a:IsLoaded()) then stars = stars + 1 end end
            line = string.format("step %d  %d of %d  stars %d  sky %s/%s  %.1f s  %s", g.step, n, #g.asked, stars,
                                 tostring(self.sky), tostring(self.shownSky), g.clock, line)
        end
        TheLoading:SetDebug(line)
    end
    self.freeNode:Attach(self:GetWorld():GetRootNode(), false)
end

local pcTick = Sky.Tick
function Sky:Tick(deltaTime)
    self:HoldStars(deltaTime)                   -- first: see HoldStars
    -- The sky stands still under the loading screen (it cannot be seen): its diamond show
    -- streams frames in and out all the time, and in the middle of a load those small blocks
    -- were cutting up the big holes the stage's pieces and the new stars need.
    local loading = (self.going ~= nil and (self.going.step < 3 or self.going.step >= 25)) or self.returning ~= nil
    if (not loading) then pcTick(self, deltaTime) end
    if (loading and MenuMusic ~= nil) then MenuMusic.Tick(deltaTime) end   -- (pcTick ticks it otherwise)
    if (self.going ~= nil) then self:TickGoing(deltaTime) end
    if (self.returning ~= nil) then self:TickReturning(deltaTime) end
    self:TestExit(deltaTime)
    self:TestPick(deltaTime)
    self:TestMarathon(deltaTime)
    self.lastTick = deltaTime
    self:TestFree()
end
