-- SavePrompt.lua (GAMECUBE ONLY: this file is not made from the PC repo)
--
-- What SAVE on the title menu opens: the memory card in slot A, and whether the game can be
-- saved on it.
--
--     +--------------------------------------------+
--     |            MEMORY CARD  SLOT A             |
--     |                                            |
--     |      SAVE TO THE MEMORY CARD IN SLOT A     |
--     |   SAVING NEEDS 1 BLOCK     250 BLOCKS FREE  |
--     |                                            |
--     |            A  SAVE        B  BACK          |
--     +--------------------------------------------+
--
-- It says, as the case is: no card; not a memory card; damaged or not formatted; another
-- region's card; FULL (with the blocks it needs and the blocks free); or ready to save -- a new
-- file, or over the game's own. The card is looked at again every second while this is up, so
-- a card put in or taken out shows at once. Saving writes the emeralds won (StageSelect:SaveWon)
-- and says whether it worked.
--
-- The save is one block: the emeralds, and the name and icon the card's own screen shows
-- (SaveInfo.lua, handed to the engine by Screens.lua).
--
--     TheSavePrompt:Open()      over the menu, which keeps still until it closes
--     TheSavePrompt.onClose     called when it closes

SavePrompt = {}

local SAVE = "emeralds"                 -- StageSelect.lua's save
local SAVE_BYTES = 64                   -- the emeralds as written, rounded well up: still one block
local LOOK_EVERY = 1.0                  -- seconds between looks at the card

-- Blue and yellow on white: never red against green (the owner reads neither apart).
local WHITE = Vec(1.0, 1.0, 1.0, 1.0)
local YELLOW = Vec(1.0, 0.84, 0.18, 1.0)
local SKY = Vec(0.45, 0.78, 1.0, 1.0)
local DIM = Vec(0.0, 0.0, 0.0, 0.55)
local BOX = Vec(0.02, 0.10, 0.42, 0.94)
local EDGE = Vec(0.45, 0.78, 1.0, 1.0)

local BOX_W, BOX_H = 540.0, 214.0

local function Blocks(n)
    return n .. ((n == 1) and " BLOCK" or " BLOCKS")
end

local function MakeText(parent, font, size, colour)
    local t = parent:CreateChild("Text")
    if (font ~= nil) then t:SetFont(font) end
    t:SetAnchorMode(AnchorMode.TopLeft)
    t:SetTextSize(size)
    t:SetColor(colour or WHITE)
    t:SetText("")
    return t
end

local function MakeQuad(parent, colour)
    local q = parent:CreateChild("Quad")
    q:SetAnchorMode(AnchorMode.TopLeft)
    q:SetColor(colour)
    return q
end

function SavePrompt:Create()
    self.built = false
    self.shown = false
    TheSavePrompt = self
end

function SavePrompt:Build()
    local res = Renderer.GetScreenResolution()
    self.w, self.h = res.x, res.y
    self:SetAnchorMode(AnchorMode.TopLeft)
    self:SetPosition(0.0, 0.0)
    self:SetDimensions(self.w, self.h)

    self.dim = MakeQuad(self, DIM)
    self.dim:SetPosition(0.0, 0.0)
    self.dim:SetDimensions(self.w, self.h)
    local x, y = (self.w - BOX_W) * 0.5, (self.h - BOX_H) * 0.5
    self.edge = MakeQuad(self, EDGE)
    self.edge:SetPosition(x - 3.0, y - 3.0)
    self.edge:SetDimensions(BOX_W + 6.0, BOX_H + 6.0)
    self.box = MakeQuad(self, BOX)
    self.box:SetPosition(x, y)
    self.box:SetDimensions(BOX_W, BOX_H)

    local font = LoadAsset("F_SonicUI")
    self.title = MakeText(self, font, 22.0, YELLOW)
    self.title:SetText("MEMORY CARD  SLOT A")
    self.lines = {}
    for i = 1, 3 do self.lines[i] = MakeText(self, font, 15.0, WHITE) end
    self.buttons = MakeText(self, font, 16.0, SKY)

    self.built = true
    self:Show(false)
end

-- Text is centred by its measured width, known once drawn: so every tick while it shows.
function SavePrompt:Place()
    local top = (self.h - BOX_H) * 0.5
    local function Centre(t, y)
        local wide = (t.GetTextWidth ~= nil) and t:GetTextWidth() or 0.0
        t:SetPosition((self.w - wide) * 0.5, top + y)
    end
    Centre(self.title, 20.0)
    for i, t in ipairs(self.lines) do Centre(t, 66.0 + (i - 1) * 28.0) end
    Centre(self.buttons, BOX_H - 40.0)
end

function SavePrompt:Say(a, b, c, buttons)
    self.lines[1]:SetText(a or "")
    self.lines[2]:SetText(b or "")
    self.lines[3]:SetText(c or "")
    self.buttons:SetText(buttons or "")
end

-- Look at slot A, and say what is there. (No punctuation: the HUD font has letters, digits and
-- spaces, and none of . ? ' ( ).)
function SavePrompt:Look()
    local state, needed, free = "none", 0, 0
    if (System.GetSaveCard ~= nil) then state, needed, free = System.GetSaveCard(SAVE, SAVE_BYTES) end
    if (needed == nil or needed <= 0) then needed = 1 end      -- no card to ask: the save is one block
    self.state = state
    local need = "SAVING NEEDS " .. Blocks(needed)
    local space = need .. "     " .. Blocks(free) .. " FREE"
    local yesNo = "A  SAVE        B  BACK"
    local back = "B  BACK"
    if (state == "ready") then
        self:Say("SAVE TO THE MEMORY CARD IN SLOT A", space, nil, yesNo)
    elseif (state == "exists") then
        self:Say("SAVE OVER YOUR SONIC PIPE DREAM DATA", "ON THE MEMORY CARD IN SLOT A",
                 "IT USES " .. Blocks(needed), yesNo)
    elseif (state == "full") then
        local why = (free >= needed) and "IT HAS NO ROOM FOR ANOTHER FILE" or space
        self:Say("THE MEMORY CARD IN SLOT A IS FULL", why,
                 "MAKE ROOM ON IT FROM THE GAMECUBE MENU", back)
    elseif (state == "nocard") then
        self:Say("THERE IS NO MEMORY CARD IN SLOT A", "PUT ONE IN TO SAVE", need, back)
    elseif (state == "wrongdevice") then
        self:Say("THE DEVICE IN SLOT A IS NOT", "A MEMORY CARD", need, back)
    elseif (state == "damaged") then
        self:Say("THE MEMORY CARD IN SLOT A IS DAMAGED", "OR NOT FORMATTED",
                 "FORMAT IT FROM THE GAMECUBE MENU", back)
    elseif (state == "encoding") then
        self:Say("THE MEMORY CARD IN SLOT A IS", "FROM ANOTHER REGION", need, back)
    elseif (state == "none") then
        self:Say("THERE ARE NO MEMORY CARDS", "ON THIS MACHINE", nil, back)
    else
        self:Say("THE MEMORY CARD IN SLOT A", "CANNOT BE READ", need, back)
    end
    self.lookIn = LOOK_EVERY
end

function SavePrompt:CanSave()
    return self.state == "ready" or self.state == "exists"
end

function SavePrompt:Show(visible)
    self.shown = visible and true or false
    if (self.built) then self:SetVisible(self.shown) end
end

function SavePrompt:Open()
    if (not self.built) then self:Build() end
    self.step, self.armed = "look", false
    self:Show(true)
    self:Look()
    self:Place()
end

function SavePrompt:Close()
    self:Show(false)
    if (self.onClose ~= nil) then self.onClose() end
end

-- As the menus: not armed until the key that opened it is let go.
function SavePrompt:Armed()
    if (self.armed) then return true end
    if (not Input.IsKeyDown(Key.Enter) and not Input.IsKeyDown(Key.Space)
        and not Input.IsKeyDown(Key.Backspace)) then
        self.armed = true
    end
    return false
end

function SavePrompt:Tick(deltaTime)
    if (not self.built) then self:Build() end
    if (not self.shown) then return end
    -- over the menus, which were spawned before it: attached again, it draws last
    self:Attach(self:GetWorld():GetRootNode(), false)
    self:Place()

    if (self.step == "saving") then
        -- "SAVING" has been on the screen for a frame; now the write (it holds the game still)
        local ok = TheStageSelect ~= nil and TheStageSelect:SaveWon(true)
        self.step, self.armed = "done", false
        if (ok) then
            self:Say("SAVED", nil, nil, "A  OK")
            if (MenuSound ~= nil) then MenuSound("MenuSelect", 0.7) end
        else
            self:Say("THE SAVE DID NOT WORK", "CHECK THE MEMORY CARD IN SLOT A", "AND TRY AGAIN", "A  OK")
        end
        return
    end

    if (self.step == "look") then
        self.lookIn = (self.lookIn or LOOK_EVERY) - deltaTime
        if (self.lookIn <= 0.0) then self:Look() end
    end

    if (not self:Armed()) then return end
    local yes = Input.IsKeyJustDown(Key.Enter) or Input.IsKeyJustDown(Key.Space)
    local no = Input.IsKeyJustDown(Key.Backspace)
    if (self.step == "done") then
        if (yes or no) then self:Close() end
    elseif (no) then
        if (MenuSound ~= nil) then MenuSound("MenuBack") end
        self:Close()
    elseif (yes and self:CanSave()) then
        self:Say("SAVING", "DO NOT TOUCH THE MEMORY CARD", "OR THE POWER BUTTON", nil)
        self.step = "saving"
    end
end
