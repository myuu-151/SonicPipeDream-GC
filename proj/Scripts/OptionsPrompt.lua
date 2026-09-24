-- FROM the PC repo, by native/patch_from_pc.py. Change it there.
-- OptionsPrompt.lua
-- What OPTIONS on the title menu opens: a box over the menu, as SavePrompt.lua's, with a list of
-- pages and on each page its settings. For now one page, AUDIO, with one setting:
--
--     +--------------------------------------------+
--     |                   AUDIO                    |
--     |                                            |
--     |        MUTE IN-STAGE MUSIC      OFF        |
--     |                                            |
--     |           A  CHANGE        B  BACK         |
--     +--------------------------------------------+
--
-- Up and down pick a line; A opens a page or changes a setting (left and right change it too); B
-- goes back a page, and from the first closes. The settings are GameOptions.lua's: they take
-- effect at once, and are kept with the save.
--
--     TheOptions:Open()     over the menu, which keeps still until it closes
--     TheOptions.onClose    called when it closes

Script.Require("GameOptions")

OptionsPrompt = {}

-- Blue and yellow on white: never red against green (the owner reads neither apart).
local WHITE = Vec(1.0, 1.0, 1.0, 1.0)
local YELLOW = Vec(1.0, 0.84, 0.18, 1.0)
local SKY = Vec(0.45, 0.78, 1.0, 1.0)
local DIM = Vec(0.0, 0.0, 0.0, 0.55)
local BOX = Vec(0.02, 0.10, 0.42, 0.94)
local EDGE = Vec(0.45, 0.78, 1.0, 1.0)

-- Sized for a 480-line screen (the GameCube's), and scaled up with the window on the PC.
local REF_H = 480.0
local BOX_W, BOX_H = 540.0, 214.0
local LINES = 3

-- The pages. A line opens another page, or is a setting (GameOptions[option], on or off).
local PAGES = {
    options = { title = "OPTIONS", lines = { { label = "AUDIO", open = "audio" } } },
    audio = { title = "AUDIO", back = "options",
              lines = { { label = "MUTE IN-STAGE MUSIC", option = "muteStageMusic" } } },
}

local function MakeText(parent, font, colour)
    local t = parent:CreateChild("Text")
    if (font ~= nil) then t:SetFont(font) end
    t:SetAnchorMode(AnchorMode.TopLeft)
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

function OptionsPrompt:Create()
    self.built = false
    self.shown = false
    self.page, self.index = "options", 1
    TheOptions = self
end

function OptionsPrompt:Build()
    self.dim = MakeQuad(self, DIM)
    self.edge = MakeQuad(self, EDGE)
    self.box = MakeQuad(self, BOX)
    local font = LoadAsset("F_SonicUI")
    self.title = MakeText(self, font, YELLOW)
    self.lines = {}
    for i = 1, LINES do self.lines[i] = MakeText(self, font, WHITE) end
    self.buttons = MakeText(self, font, SKY)
    self.built = true
    self:Show(false)
end

-- Laid out every tick while it shows: text is centred by its measured width, known once drawn,
-- and on the PC the window can change size.
function OptionsPrompt:Place()
    local res = Renderer.GetScreenResolution()
    local w, h = res.x, res.y
    local k = h / REF_H
    self:SetAnchorMode(AnchorMode.TopLeft)
    self:SetPosition(0.0, 0.0)
    self:SetDimensions(w, h)
    self.dim:SetPosition(0.0, 0.0)
    self.dim:SetDimensions(w, h)
    local bw, bh = BOX_W * k, BOX_H * k
    local x, top = (w - bw) * 0.5, (h - bh) * 0.5
    self.edge:SetPosition(x - 3.0 * k, top - 3.0 * k)
    self.edge:SetDimensions(bw + 6.0 * k, bh + 6.0 * k)
    self.box:SetPosition(x, top)
    self.box:SetDimensions(bw, bh)
    self.title:SetTextSize(22.0 * k)
    for _, t in ipairs(self.lines) do t:SetTextSize(17.0 * k) end
    self.buttons:SetTextSize(16.0 * k)
    local function Centre(t, y)
        local wide = (t.GetTextWidth ~= nil) and t:GetTextWidth() or 0.0
        t:SetPosition((w - wide) * 0.5, top + y * k)
    end
    Centre(self.title, 20.0)
    for i, t in ipairs(self.lines) do Centre(t, 70.0 + (i - 1) * 30.0) end
    Centre(self.buttons, BOX_H - 40.0)
end

-- What the page says now: its lines, the chosen one in yellow, each setting with its state.
function OptionsPrompt:Refresh()
    local page = PAGES[self.page]
    self.title:SetText(page.title)
    for i = 1, LINES do
        local line = page.lines[i]
        local text = ""
        if (line ~= nil) then
            text = line.label
            if (line.option ~= nil) then
                text = text .. "     " .. (GameOptions[line.option] and "ON" or "OFF")
            end
        end
        self.lines[i]:SetText(text)
        self.lines[i]:SetColor((i == self.index) and YELLOW or WHITE)
    end
    local chosen = page.lines[self.index]
    local act = (chosen ~= nil and chosen.option ~= nil) and "A  CHANGE" or "A  SELECT"
    self.buttons:SetText(act .. "        B  BACK")
end

function OptionsPrompt:Show(visible)
    self.shown = visible and true or false
    if (self.built) then self:SetVisible(self.shown) end
end

function OptionsPrompt:Open()
    if (not self.built) then self:Build() end
    self.page, self.index, self.armed = "options", 1, false
    self:Show(true)
    self:Refresh()
    self:Place()
end

function OptionsPrompt:Close()
    self:Show(false)
    if (self.onClose ~= nil) then self.onClose() end
end

-- As the menus: not armed until the key that opened it is let go.
function OptionsPrompt:Armed()
    if (self.armed) then return true end
    if (not Input.IsKeyDown(Key.Enter) and not Input.IsKeyDown(Key.Space)
        and not Input.IsKeyDown(Key.Backspace)) then
        self.armed = true
    end
    return false
end

local function Sound(name)
    if (MenuSound ~= nil) then MenuSound(name) end
end

function OptionsPrompt:Tick(deltaTime)
    if (not self.built) then self:Build() end
    if (not self.shown) then return end
    -- over the menus, which were spawned before it: attached again, it draws last
    self:Attach(self:GetWorld():GetRootNode(), false)
    self:Place()
    if (not self:Armed()) then return end

    local page = PAGES[self.page]
    local up = Input.IsKeyJustDown(Key.Up) or Input.IsKeyJustDown(Key.W)
    local down = Input.IsKeyJustDown(Key.Down) or Input.IsKeyJustDown(Key.S)
    local side = Input.IsKeyJustDown(Key.Left) or Input.IsKeyJustDown(Key.Right)
                 or Input.IsKeyJustDown(Key.A) or Input.IsKeyJustDown(Key.D)
    local yes = Input.IsKeyJustDown(Key.Enter) or Input.IsKeyJustDown(Key.Space)
    local no = Input.IsKeyJustDown(Key.Backspace) or Input.IsKeyJustDown(Key.Escape)
    local line = page.lines[self.index]

    if (no) then
        Sound("MenuBack")
        if (page.back ~= nil) then
            -- back to the page this one was opened from, on the line that opened it
            local from = self.page
            self.page, self.index = page.back, 1
            for i, l in ipairs(PAGES[self.page].lines) do
                if (l.open == from) then self.index = i end
            end
            self:Refresh()
        else
            self:Close()
        end
    elseif (up or down) then
        local n = #page.lines
        if (n > 1) then
            self.index = (self.index - 1 + (down and 1 or -1)) % n + 1
            Sound("MenuMove")
            self:Refresh()
        end
    elseif (line ~= nil and line.open ~= nil and yes) then
        Sound("MenuSelect")
        self.page, self.index = line.open, 1
        self:Refresh()
    elseif (line ~= nil and line.option ~= nil and (yes or side)) then
        GameOptions[line.option] = not GameOptions[line.option]
        GameOptions.touched = true              -- kept with the save the next time it is written
        Sound("MenuMove")
        self:Refresh()
    end
end
