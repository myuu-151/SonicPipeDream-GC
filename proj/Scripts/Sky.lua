-- Sky.lua (GameCube)
-- THE FIRST TEST HAS NO SKY. The scene still has the PC project's sky dome node with this
-- script on it, so this stub keeps the one job of that script the game cannot do without:
-- it starts the special stage when the game runs. The dome hides itself.
--
-- When the sky comes back it will be the 8-frame "clusters" sky that the PC repo's
-- gen_s2sky_assets.py already knows how to write (DIAMOND_MODE = "clusters"): the PC's
-- 384-frame medley is about 200 MB and this machine has 24.

Sky = {}

function Sky:Create()
    self.sky = 0
    self.startSpecialStage = true
    self.startedSpecialStage = false
    TheSky = self
end

function Sky:GatherProperties()
    return
    {
        { name = "sky", type = DatumType.Integer },
        { name = "startSpecialStage", type = DatumType.Bool },
    }
end

function Sky:Tick(deltaTime)
    if (self.startSpecialStage and not self.startedSpecialStage) then
        self.startedSpecialStage = true
        if (self.SetVisible ~= nil) then self:SetVisible(false) end
        local stage = self:GetWorld():SpawnNode("Node3D")
        stage:SetName("SpecialStage")
        stage:SetScript("SpecialStage")
    end
end
