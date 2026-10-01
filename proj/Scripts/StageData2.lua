-- Written by native/export_gc.py from the PC repo's Stage2_seed1.json. Do not edit by hand.
-- (split by native/split_stage_data.py)
StageData2 = {
  name = "Stage2_seed1",
  stage = 2,
  step = 5.0201,
  frames = 1585,
  pipe_radius = 10,
  hover = 1.9,
  angle_00_side = -1,
  arch = {
    rings = 9,
    reach = 11.6,
    from_deg = 12,
    ring_scale = 1.03,
    toward_player = 0.72,
    steps_per_second = 8,
  },
  sky = 4,
  palette = 2,
  palette_skies = {0,4,6,3,5,2,1},
  pieces = {},
  sections = {},
  path = {},
}
for i = 1, 7 do Script.Run("StageData2_" .. i) end     -- its lists, in pieces
