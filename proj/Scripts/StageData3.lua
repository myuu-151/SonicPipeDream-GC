-- Written by native/export_gc.py from the PC repo's Stage3_seed1.json. Do not edit by hand.
-- (split by native/split_stage_data.py)
StageData3 = {
  name = "Stage3_seed1",
  stage = 3,
  step = 5.0201,
  frames = 1937,
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
  sky = 6,
  palette = 3,
  palette_skies = {0,4,6,3,5,2,1},
  pieces = {},
  sections = {},
  path = {},
}
for i = 1, 8 do Script.Run("StageData3_" .. i) end     -- its lists, in pieces
