"""
endstop_dims.py - the limit switch board and where the J2/J3 switches sit (plain numbers,
no FreeCAD), shared by upper_arm.py (cam fingers) and limits.py (boards + bracket).

The board is the red "Mech Endstop v1.2" clone (arduino.ua TDC103): a subminiature lever
switch lying on its side on a 39.4 x 16.4 PCB, 3-pin lead on a JST-XH header, LED that
lights when the lever is pressed. Only the PCB outline was measured (by the user); the
rest is scaled off the shop's top-view photo against that outline and the board's known
19 mm hole pitch, so treat every other number as +-0.5 mm. The bracket takes that up:
each board slides across its lever edge on two slotted screws.

Board frame: x along the board from the connector end, y across it from the lever edge,
z up from the PCB's top face.

How a switch is worked: the board lies flat under the shoulder, lever edge along the
arm's plane. A finger on the rotating part sweeps past that edge at STANDOFF and pushes
the lever flat against the switch - it comes in along the lever, never straight at it,
and simply runs on past if the joint overshoots. The fingers are deep enough to be level
with the lever before they reach its free end or the 3 mm of it next to the hinge.
"""
import math

# ---- the board ----
BOARD_L, BOARD_W, BOARD_T = 39.4, 16.4, 1.6   # measured
HOLE_D = 3.0
HOLES = ((17.0, 2.7), (36.0, 2.7))            # the pair 19 mm apart, either side of the switch
SW = (20.3, 32.9, -0.2, 6.3, 5.8)             # switch body: x0, x1, y0, y1, height
LEV_HINGE_X, LEV_TIP_X = 21.1, 33.1           # lever: hinged at the connector side, free end at the board's end
LEV_HINGE_OUT, LEV_TIP_OUT = 0.3, 4.2         # how far it stands out past the lever edge (free)
LEV_Z0, LEV_Z1 = 1.2, 4.6                     # the lever strip's width, above the PCB
LEV_PRESS = 6.9                               # the switch has clicked once the lever is held down this far from the hinge
CONN = (3.6, 10.4, 1.9, 14.5, 7.0)            # JST-XH header: x0, x1, y0, y1, height
PLUG_H = 18.0                                 # plug + lead bend above the PCB
SOLDER = 2.0                                  # solder joints under the PCB
TERM_Y = 6.7                                  # switch terminals' solder starts here

# ---- where the boards sit (turret frame, relative to the shoulder axis) ----
PCB_DEPTH = 24.0        # PCB top face below the shoulder axis
TIP_END = 4.0           # the board's switch end from the J1 axis (clear of the wedge screw's washers)
STANDOFF = 1.5          # finger face to the board's lever edge
ADJ = (-0.5, 1.0)       # slots: towards the finger / away from it
J2_FACE, J2_FINGER_T = 9.0, 3.0     # J2 fingers: on the +y plate, y 9..12 (its inner face works the lever)
J3_FACE, J3_FINGER_T = -20.5, 5.0   # J3 fingers: on the crank's root ring, y -20.5..-25.5
FINGER_R, FINGER_W, FINGER_CH = 29.0, 6.0, 1.2
# trip points: 1.5 deg outside the working range the kinematics allow (J2 35..150, J3 -70..35)
J2_LIM = (33.5, 151.5)
J3_LIM = (-71.5, 36.5)

LEV_DEPTH = PCB_DEPTH - (LEV_Z0 + LEV_Z1) / 2        # lever centre below the axis
LEV_TIP = TIP_END + BOARD_L - LEV_TIP_X              # |x| of the lever's free end
LEV_HINGE = TIP_END + BOARD_L - LEV_HINGE_X          # |x| of its hinge


def _finger(contact_x, joint_at_trip, from_low_angles):
    """Centreline angle (deg, in the rotating part's frame) of a radial bar FINGER_W wide whose
    leading flank is at (contact_x, -LEV_DEPTH) when the joint is at joint_at_trip."""
    r = math.hypot(contact_x, LEV_DEPTH)
    a = math.degrees(math.atan2(-LEV_DEPTH, contact_x)) % 360
    off = math.degrees(math.asin(FINGER_W / 2 / r))
    return (a - off if from_low_angles else a + off) - joint_at_trip


# J2 board behind the axis, lever edge to +y: the low-limit finger comes over the lever's free
# end, the high-limit one over its hinge. J3 board is the same thing turned half round (in front).
J2_FINGERS = (_finger(-(LEV_TIP + 0.3), J2_LIM[0], False),             # low limit
              _finger(-(LEV_HINGE - LEV_PRESS), J2_LIM[1], True))      # high limit
J3_FINGERS = (_finger(LEV_HINGE - LEV_PRESS, J3_LIM[0] + 180, False),  # low limit (crank frame: arm at 0)
              _finger(LEV_TIP + 0.3, J3_LIM[1] + 180, True))           # high limit

if __name__ == "__main__":
    print("lever: tip", LEV_TIP, "hinge", LEV_HINGE, "depth", LEV_DEPTH)
    print("J2 fingers (arm frame):", [round(a, 1) for a in J2_FINGERS])
    print("J3 fingers (crank frame):", [round(a % 360, 1) for a in J3_FINGERS])
