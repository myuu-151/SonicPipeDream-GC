-- FROM the PC repo, by native/patch_from_pc.py. Change it there.
-- GameOptions.lua
-- The player's settings, changed from OPTIONS on the title menu (OptionsPrompt.lua) and kept with
-- the save: one letter each after the seven emeralds in StageSelect.lua's save text, so a save made
-- before there were options still reads (as all of them off).
--
--     GameOptions.muteStageMusic   the stages' and the marathon's music is not played
--                                  (SpecialStageMusic.lua); the menus' is

GameOptions = GameOptions or { muteStageMusic = false, touched = false }

-- The letters after the emeralds.
function GameOptions.Encode()
    return GameOptions.muteStageMusic and "M" or "-"
end

-- From a save's text. A setting changed this session and not saved yet stays as the player set it
-- (the menus read the save again every time they are built, on the GameCube); LOAD clears
-- `touched` first, so a save loaded on purpose does bring its settings.
function GameOptions.Decode(text)
    if (GameOptions.touched) then return end
    GameOptions.muteStageMusic = (text ~= nil and text:sub(8, 8) == "M")
end
