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
-- The sky is not changed on the way back: the PC leaves the last stage's sky up behind the
-- menus too, and here it saves loading a sky's 4 MB of stars twice.
--
-- Sky.lua requires this at its end, so these replace the PC's own Sky:ShowMenu and wrap its
-- Tick. The PC's Sky:StartSpecialStage is used as it is.

Script.Require("PadInput")
Script.Require("GcTest")        -- switches for testing in Dolphin; all off unless set there

local STAGES = 7
local WAIT_AT_MOST = 30.0           -- seconds: a stage starts even if something never arrives,
                                    -- rather than leaving the loading screen up for ever

-- Everything SpecialStage:Build loads, the first time a stage is played. Asked for with the
-- stage's own assets, so that first time is no slower to leave the loading screen.
local function BuildAssets()
    local names = { "SM_Ring", "SM_Bomb", "SM_PlayerBall", "SM_FxQuad", "SM_FxQuadBoom", "M_Explosion",
                    "SM_Shadow", "SM_Sonic_Idle_00", "SM_Emerald",
                    "T_UI_Emblem", "T_UI_EmblemRed", "T_UI_Flag", "T_UI_FlagLeft", "T_UI_SonicRings",
                    "T_UI_Thumb", "T_UI_ThumbDown", "T_UI_Total" }
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

    -- TheMenu and TheStageSelect are set by each script's Create, which has run by now.
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
        end
    end
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
    self.menuNode, self.selectNode = nil, nil
    TheMenu, TheStageSelect = nil, nil
    Sweep()
end

-- ------------------------------------------------------------------ into a stage
function Sky:GoToStage(stage)
    TheStageSelect:Close()
    local won = TheStageSelect.won ~= nil and TheStageSelect.won[stage]
    TheLoading:Show(stage, won)
    self.going = { stage = stage, step = 0, clock = 0.0 }
end

function Sky:TickGoing(deltaTime)
    local g = self.going
    g.clock = g.clock + deltaTime
    if (g.step == 0) then
        g.step = 1                              -- the loading screen is drawn this frame
    elseif (g.step == 1) then
        self:DropMenus()
        local data = LoadStageData(g.stage)
        if (data == nil) then
            Log.Error("Screens: no StageData" .. g.stage)
            g.stage, data = 1, LoadStageData(1)
        end
        -- the stage's sky: Sky:LoadSky lets the last one's stars go and asks for these
        if (data.sky ~= nil) then self.sky = data.sky end
        local names, seen = {}, {}
        local function Want(name)
            if (not seen[name]) then
                seen[name] = true
                names[#names + 1] = name
            end
        end
        for _, piece in ipairs(data.pieces) do
            Want(piece.mesh .. data.palette)
            Want(piece.gloss .. data.palette)
        end
        Want("SM_Emerald_" .. g.stage)
        for i = 0, data.arch.rings - 1 do Want("SM_RingRainbow_" .. i) end
        if (TheSpecialStage == nil or not TheSpecialStage.built) then
            for _, name in ipairs(BuildAssets()) do Want(name) end
        end
        g.asked = {}
        for _, name in ipairs(names) do g.asked[#g.asked + 1] = AsyncLoadAsset(name) end
        g.step, g.clock = 2, 0.0
    elseif (g.step == 2) then
        local ready = self:StarsReady()
        for _, a in ipairs(g.asked) do
            if (not a:IsLoaded()) then ready = false end
        end
        if (ready or g.clock > WAIT_AT_MOST) then
            if (not ready) then Log.Warning("Screens: a stage asset never arrived; starting anyway") end
            self:StartSpecialStage(g.stage)
            -- Built NOW, not on its own first tick next frame: Build spawns the HUD, and the
            -- loading screen has to be moved back over it in the same frame, or the HUD shows
            -- through it for a frame.
            if (not TheSpecialStage.built) then TheSpecialStage:Build() end
            self.loadingNode:Attach(self:GetWorld():GetRootNode(), false)
            TheSpecialStage.onExit = function() self:BackToSelect(nil) end
            TheSpecialStage.onFinished = function(won) self:BackToSelect(won) end
            g.step = 3
        end
    elseif (g.step == 3) then
        -- up once the stage has built itself and drawn a frame
        local s = TheSpecialStage
        if (s ~= nil and s.built and s.data ~= nil and s.stage == g.stage) then
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
-- HERE ALL OF IT GOES. Kept, it pinned itself in the middle of the heap: the stage select's art
-- then went into the holes the pipe left, and the next time into a stage the biggest pipe
-- pieces (a drop is 1.3 MB once loaded, in three blocks of up to 640 KB) found no block big
-- enough. Stage 7, entered a second time, died loading its drop. Torn down whole, every entry
-- into a stage starts from the heap the first one did, and the first one fits.
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
        for _, node in ipairs({ s.player, s.playerShadow, s.uiNode, s.debugNode }) do Kill(node) end
        local world = self:GetWorld()
        Kill(world:FindNode("SpecialStageMusic"))
        Kill(world:FindNode("StageSun"))
        s:Destruct()                                -- the stage's own node
    end
    TheSpecialStage, TheSpecialStageUI, TheSpecialStageMusic = nil, nil, nil
    self.startedSpecialStage = false                -- so StartSpecialStage builds it afresh
    for k = 1, STAGES do _G["StageData" .. k] = nil end
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
        self:SpawnMenus(r.stage)
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
function Sky:StarFrame(i)
    local tex = self.starFrames[i]
    if (tex == nil and self.starAsked ~= nil and self.starAsked[i] ~= nil and self.starAsked[i]:IsLoaded()) then
        tex = LoadAsset(self.starName(self.shownSky, i))
        self.starFrames[i] = tex
    end
    return tex
end

-- All of the sky on show has arrived (or it is not asking for anything).
function Sky:StarsReady()
    if (self.sky ~= self.shownSky and not (self.shownSky == 0 and self.fellBack == math.floor(self.sky))) then
        return false                            -- asked for, not yet taken up by UpdateSky
    end
    for _, a in pairs(self.starAsked or {}) do
        if (not a:IsLoaded()) then return false end
    end
    return true
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
    self:GoToStage(stage)
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
    self.freeText:SetText(string.format("free %d KB", free))
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
    pcTick(self, deltaTime)
    if (self.going ~= nil) then self:TickGoing(deltaTime) end
    if (self.returning ~= nil) then self:TickReturning(deltaTime) end
    self:TestExit(deltaTime)
    self:TestPick(deltaTime)
    self:TestFree()
end
