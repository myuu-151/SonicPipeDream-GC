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
    # -- fewer spin meshes: export_gc.py writes 6
    ("local RING_SPIN_FRAMES = 12 ", "local RING_SPIN_FRAMES = 6  "),
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
    # -- no UI art, font or music in the first test: an FPS readout instead
    ("""    local ui = world:SpawnNode("Canvas")
    ui:SetScript("SpecialStageUI")

    -- the music: its script only needs to be on some node, and nothing in the scene has it
    local music = world:SpawnNode("Node3D")
    music:SetName("SpecialStageMusic")
    music:SetScript("SpecialStageMusic")
""", """    -- THE FIRST TEST: no UI art, no font, no music. One line of text with what the test is for:
    -- the frame rate, and how much track is being drawn.
    local ui = world:SpawnNode("Canvas")
    ui:SetAnchorMode(AnchorMode.TopLeft)
    ui:SetPosition(0.0, 0.0)
    ui:SetDimensions(640.0, 480.0)
    self.readout = ui:CreateChild("Text")
    self.readout:SetAnchorMode(AnchorMode.TopLeft)
    self.readout:SetPosition(24.0, 24.0)
    self.readout:SetTextSize(22.0)
    self.readout:SetColor(Vec(1.0, 1.0, 0.2, 1.0))
    self.readout:SetText("...")
    self.fpsTime, self.fpsFrames, self.piecesShown = 0.0, 0, 0
"""),
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
    if (self.fpsTime >= 0.5) then
        self.readout:SetText(string.format("%.1f fps   %d pieces   %d objects", self.fpsFrames / self.fpsTime,
                                           self.piecesShown, self.objectsShown or 0))
        self.fpsTime, self.fpsFrames = 0.0, 0
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


def main():
    s = open(SRC, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    for n, (old, new) in enumerate(CHANGES):
        if old not in s:
            raise SystemExit("change %d no longer fits the PC script:\n%s" % (n + 1, old[:200]))
        s = s.replace(old, new, 1)
    open(OUT, "w", encoding="utf-8", newline="\n").write(s)
    print("wrote %s (%d changes)" % (OUT, len(CHANGES)))


if __name__ == "__main__":
    main()
