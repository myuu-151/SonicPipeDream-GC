-- PadInput.lua (GAMECUBE ONLY: this file is not made from the PC repo)
--
-- The PC game is played on a keyboard, and its scripts ask only about keys. Rather than change
-- every script that reads a key, the GameCube pad is folded INTO those keys here: asking whether
-- Enter is down answers yes while A is held. Every PC script then works with the pad as it
-- stands, and a gameplay fix on the PC needs nothing here.
--
--     d-pad / stick up, down     Up, Down (W, S)          the menus, the pause menu
--     A                          Enter, Space             choose; jump
--     B                          Backspace                back, on the stage select
--     Start                      Escape in a stage        pause, and continue
--                                Enter anywhere else      choose, on the menus
--     B, while paused            Escape                   continue
--
-- Steering is not here: patch_from_pc.py gives SpecialStage.lua the stick directly, so that
-- half a tilt steers half as hard.
--
-- Sky.lua requires this before anything else runs.

if (PadInputWrapped == nil) then
    PadInputWrapped = true

    local keyDown, keyJustDown = Input.IsKeyDown, Input.IsKeyJustDown
    local padDown, padJustDown = Input.IsGamepadButtonDown, Input.IsGamepadButtonJustDown

    -- A stage is on the screen (and not put away behind the menus).
    local function InStage()
        return TheSpecialStage ~= nil and TheSpecialStage.built and TheSpecialStage.active ~= false
    end

    -- The pad buttons that stand for a key, just now.
    local function ButtonsFor(key)
        if (key == Key.Up or key == Key.W) then return Gamepad.Up, Gamepad.LsUp end
        if (key == Key.Down or key == Key.S) then return Gamepad.Down, Gamepad.LsDown end
        if (key == Key.Space) then return Gamepad.A end
        if (key == Key.Enter) then
            if (InStage()) then return Gamepad.A end
            return Gamepad.A, Gamepad.Start
        end
        if (key == Key.Backspace) then return Gamepad.B end
        if (key == Key.Escape) then
            if (not InStage()) then return nil end
            if (TheSpecialStage.paused) then return Gamepad.Start, Gamepad.B end
            return Gamepad.Start
        end
        return nil
    end

    local function Any(test, a, b)
        if (a ~= nil and test(a)) then return true end
        if (b ~= nil and test(b)) then return true end
        return false
    end

    Input.IsKeyDown = function(key)
        return keyDown(key) or Any(padDown, ButtonsFor(key))
    end

    Input.IsKeyJustDown = function(key)
        return keyJustDown(key) or Any(padJustDown, ButtonsFor(key))
    end
end
