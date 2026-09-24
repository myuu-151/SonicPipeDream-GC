-- GcTest.lua (GAMECUBE ONLY)
--
-- Switches for testing a build in Dolphin without touching the pad (keys sent to Dolphin can land
-- in whatever window has the focus). The PC's S2_* environment variables cannot reach a console,
-- so these stand in for them. ALL OFF in anything shipped: GcTest = {}.
--
--     pick = n          on the stage select, choose stage n by itself (0: 1 to 7, then round again)
--     exit = seconds    leave a stage that long after it starts, as EXIT from the pause menu does
--     free = true       free memory, in KB, in the corner of every screen
--     wait = seconds    how long the stage select shows before `pick` chooses (default 3)
--     marathon = true   on the title menu, choose MARATHON by itself (after `wait`)
--     hold = seconds    in a marathon, change its colours that often, as a zone's hold does
--     holdTo = n        ...always to palette n (else the next one round)
--     autoplay = true   the stage plays itself (the PC's S2_AUTOPLAY)
--     spin = seconds    a spin dash that long into a stage, and every 8 s after (S2_TEST_SPIN)

GcTest = {}
