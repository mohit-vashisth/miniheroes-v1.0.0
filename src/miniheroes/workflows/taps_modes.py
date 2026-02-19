# taps_modes.py
from __future__ import annotations

# mode 1-----------------------------------------------
PRE_EMAIL_TAPS = [
    (341, 573, 2),
    (545, 789, 3),
    (243, 510, 3),
]

POST_EMAIL_TAPS = [
    (533, 598, 3),
    (258, 600, 3),
]

MAIN_SEQUENCE = [
    (324, 703, 5),
    (324, 789, 14),
    (328, 837, 5),
    (328, 1012, 2),
    (338, 1012, 1),
    (338, 1012, 1),
    (338, 1012, 1),
    (542, 1146, 0.5),
    (538, 1201, 0.5),
    (564, 1206, 0.5),
    (559, 1216, 0.5),
    (557, 1216, 0.5),
    (557, 1216, 0.5),
    (557, 1216, 0.5),
    (557, 1216, 0.5),
    (557, 1218, 0.5),
    (550, 1198, 0.5),
    (547, 1201, 0.5),
    (547, 1201, 0.5)
]

# mode 1 End-----------------------------------------------

# mode 2--------this is currently incomplete, inn future i'll add 3 or more mods here---------------------------------------
MODE1_STEPS = (
    [("wait", 30)]
    + [("tap", x, y, wait_s) for x, y, wait_s in PRE_EMAIL_TAPS]
    + [("text", "__EMAIL__")]
    + [("tap", x, y, wait_s) for x, y, wait_s in POST_EMAIL_TAPS]
    + [("wait", 2)]
    + [("text", "__CODE__")]
    + [("tap", x, y, wait_s) for x, y, wait_s in MAIN_SEQUENCE]
)


# mode 2 ends-----------------------------------------------