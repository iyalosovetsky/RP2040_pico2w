"""
endstop_dims.py - the limit switches and where they sit (plain numbers, no FreeCAD), shared by
upper_arm.py (the cams), limits.py (switches + bracket + J1 collar and flag) and the viewer export.

The switch is a bare subminiature roller-lever microswitch, KW11-3Z-5A style (the user's photo,
2026-11-27): body 20 long, 6.4 thick (user's numbers), about 10.2 high, two 2.35 holes 9.5 apart
for M2, three solder terminals (COM at the hinge end, NO, NC), a hinged strip lever with a red
roller at its end. It is the Omron SS-5GL2 case, so the body, the holes and the roller's operating
height are taken from that data sheet (en-ss.pdf); the user's lever is longer than the Omron one
(the roller sits over the far end of the body), and its free height is scaled off the photo, so
treat the lever numbers as +-1 mm. The seats take that up: every switch slides +-1.5 mm towards
its cam on two slotted M2 screws.

Switch frame: x along the body from the hinge end, y out of the lever face (the body is at y < 0),
z up from the face it lies on (thickness).

How a switch is worked: a roller lever is made to be run over by a cam from either direction, so
there is nothing between the cam and the switch any more (the red boards with their printed pushers and
covers are gone). One switch still stops its joint at both ends: two cams per joint, one for each
end, pass over the same roller. A cam is a bar as thick as the part it is on, with a flat on its
working face and both flanks bevelled 45 deg for the whole height the free roller stands above
that flat: the roller meets the bevel, rolls up it onto the flat and off the other side if the
joint overshoots. The switch is set (slots) so that the flat holds the roller OVER past its click.
"""
import math

# ---- the switch ----
SW_L, SW_H, SW_T = 19.8, 10.2, 6.4     # body: along the lever, across it (hinge half; the far half is SW_STEP lower), thick
SW_STEP_X, SW_STEP = 9.5, 0.9          # the lever face steps down by SW_STEP from here to the far end (photo)
SW_HOLE_D = 2.35
SW_HOLES = ((5.1, -7.3), (14.6, -7.3))  # 9.5 apart, 2.9 from the terminal face
SW_TERM_X = (1.6, 10.4, 17.7)          # COM, NO, NC blades, in the middle of the thickness
SW_TERM_L, SW_WIRE = 4.0, 7.0          # blade length; room kept for the soldered leads beyond it
SW_PLUNGER_X = 8.5
LEV_HINGE = (4.0, 0.9)                 # the lever's hinge pin (photo: ~4 from the body end)
LEV_T, LEV_Z = 0.3, (1.05, 5.35)       # strip thickness, and its width across the body's thickness
ROLLER_D, ROLLER_W = 4.8, 3.2          # roller, in the middle of the thickness
ROLLER_X = 19.5                        # roller axis along the body with the roller on a cam's flat (photo: over the body end)
OP_TOP = 7.2                           # roller top above the lever face where the switch clicks: SS-5GL2 OP 14.5 +-0.8
                                       # from the hole line, which is 7.3 under the face
FREE_TOP, FREE_TOP_MAX = 11.5, 12.0    # ... with nothing on it (photo; SS-5GL2: 19.3 max from the hole line)
OVER = 0.6                             # a cam's flat holds the roller this far past the click (SS-5GL2 allows 1.2 at least)
PRESS_TOP = OP_TOP - OVER              # roller top above the lever face on a cam's flat: what the seats are made for
ADJ = 1.5                              # the slots: this much either way across the lever face
M2_NUT_AF, M2_NUT_T = 4.0, 1.6
M2_LEN = 12.0                          # M2x12: 6.4 of switch + 4.0 of plastic + the nut


def lever_turn(top):
    """lever's angle (deg) about its hinge, from where it lies on a cam's flat, with the roller's top at `top`
    above the lever face"""
    hx, hy = LEV_HINGE
    r = math.hypot(ROLLER_X - hx, PRESS_TOP - ROLLER_D / 2 - hy)
    ang = lambda t: math.degrees(math.asin((t - ROLLER_D / 2 - hy) / r))  # noqa: E731
    return ang(top) - ang(PRESS_TOP)


# ---- cams ----
CAM_FLAT = 4.0          # flat on the working face, along the cam's path
CAM_R = 28.0            # J2/J3 cams reach this far from the shoulder axis
TRIP_IN = math.sqrt((ROLLER_D / 2) ** 2 - (ROLLER_D / 2 - OVER) ** 2)   # roller axis this far outside the flat's edge
                                                                         # (on the flat's corner) when the switch clicks

# ---- J2/J3: where the switches sit (turret frame, relative to the shoulder axis) ----
# Both lie flat on the bracket between the cheeks, under the shoulder: J2's behind the J1 axis with its lever
# face to +y, worked by the cams on the J2-side plate (their working face is the plate's inner face); J3's is
# the same thing turned half a turn, in front, lever face to -y, worked by the cams on the crank's root ring.
ROLLER_DEPTH = 23.8     # roller's mid-height below the shoulder axis: the seat is 6.0 above the turret plate, which
                        # makes M2x12 end flush with a nut pulled up in its pocket under the bracket
ROLLER_XR = 3.35        # |x| of the roller's axis (on a flat): puts the bracket's two hub screws midway between
                        # each switch's M2 screws
J2_FACE, J2_CAM_T, J2_BEVEL = 9.0, 6.5, 5.5      # J2 cams: y 9..15.5 (the plate is 9..16; the lower levelling rod
                                                  # runs at 16.5), bevels from the inner face up
J3_FACE, J3_CAM_T, J3_BEVEL = -20.5, 5.0, 4.6    # J3 cams: y -25.5..-20.5, the crank arm's plane (the drive rod runs
                                                  # at -20.5..-16.5), bevels from the inner face
# trip points: 1.5 deg outside the working range the kinematics allow (J2 35..150, J3 -70..35)
J2_LIM = (33.5, 151.5)
J3_LIM = (-71.5, 36.5)

# ---- J1 (base frame: table z = 0, J1 = Z) ----
# The switch stands on a collar clamped round the base housing, in front of the J1 axis: flat against a riser,
# lever face up and level, roller on top. A flag under an arm of the J2/J3 bracket (so it turns with the turret,
# behind the J1 axis when the arm points forward) passes over it; it gets there from either side after a little
# under half a turn, so the one switch stops J1 both ways. The turret plate's underside (z 104) sweeps over the
# switch too, at +-90 deg: the free roller has to stay under it.
J1_SEAT_X = 59.3          # the riser's face the switch lies against; the roller's middle is SW_T / 2 further out
J1_FLAG_Z0 = 97.5         # the flag's underside: holds the roller PRESS_TOP above the lever face
J1_EDGE = J1_FLAG_Z0 - PRESS_TOP   # lever face above the table (free roller top at 102.9 at most)
J1_BEVEL = 6.0
J1_FLAG_R = (57.0, 68.0)  # flag, radially: the roller is at 60.9..64.1
J1_COLLAR_T, J1_COLLAR_H = 4.0, 40.0   # collar round the base housing, z 44..84: it carries the SKR Pico too
J1_COLLAR_SCR_Z = (77.0, 50.0)          # the two M3 per side that pull its halves together
# SKR Pico board on the collar's rear half (electronics.py builds the plate and the board)
SKR_PAD_X, SKR_PAD_W = 62.0, 20.0       # pad's flat face at x = -SKR_PAD_X, |y| <= SKR_PAD_W
SKR_PAD_Z1 = 56.0                       # pad from the collar's bottom up to here; its nut slots open on top
SKR_SCR_Y, SKR_SCR_Z = 12.0, 50.0       # plate screws, M3x12 into nuts in the pad

J1_LIM = (-171.0, 171.0)
J1_ROLLER_R = J1_SEAT_X + SW_T / 2
# flag width along its path: flat wide enough to click the switch at J1_LIM, plus the two bevels
J1_ROLLER_OFF = 0.145     # the roller is this much nearer the hinge at its click point than on the flat: the switch is
                          # moved over by it, so both ends trip at the same angle (limits.py's "trip points" line)
J1_FLAG_FLAT = 2 * (J1_ROLLER_R * math.sin(math.radians(180 - J1_LIM[1])) - TRIP_IN) - 0.36
J1_FLAG_W = J1_FLAG_FLAT + 2 * J1_BEVEL

# ---- homing (firmware defaults in CMakeLists.txt and arm_guard.c are copied from these) ----
# J2 and J3 home together towards their HIGH trip points (arm up and back, away from the table),
# J1 towards +. Machine zero of a joint is its high trip point, so joint angle = machine + *_LIM[1].
PULLOFF = 3.0      # $27: backs off the switch by this after homing; also kept clear of it by the soft limits
MARGIN = 1.5       # the working range stops this far short of the far trip point


def working_range(lim):
    """Joint range the soft limits allow once homed with hard limits on."""
    return lim[0] + MARGIN, lim[1] - PULLOFF


def max_travel(lim):
    """$130..$132 for that range."""
    return lim[1] - lim[0] + PULLOFF - MARGIN


def _cam(roller_x, joint_at_trip, from_low_angles, trim=0.0):
    """Centreline angle (deg, in the rotating part's frame) of a cam - a straight bar along a radius with a flat
    CAM_FLAT wide - that has the roller at (roller_x, -ROLLER_DEPTH) just clicked when the joint is at
    joint_at_trip. trim: correction (deg) from limits.py's sweep of the real solids (the bar's edge crosses the
    roller a little askew)."""
    r = math.hypot(roller_x, ROLLER_DEPTH)
    a = math.degrees(math.atan2(-ROLLER_DEPTH, roller_x)) % 360
    off = math.degrees(math.asin((CAM_FLAT / 2 + TRIP_IN) / r))
    return (a - off if from_low_angles else a + off) - joint_at_trip + trim


# J2 (arm frame: the link along 0 deg), J3 (crank frame: the crank arm along 0, the forearm at 180):
# (low-limit cam, high-limit cam). The trims come from limits.py's "switch pressed" lines.
J2_CAMS = (_cam(-ROLLER_XR, J2_LIM[0], False, -0.36), _cam(-ROLLER_XR, J2_LIM[1], True, -1.14))
J3_CAMS = (_cam(ROLLER_XR, J3_LIM[0] + 180, False, 1.14), _cam(ROLLER_XR, J3_LIM[1] + 180, True, 0.36))

if __name__ == "__main__":
    print("switch: press top", PRESS_TOP, "click", OP_TOP, "free", FREE_TOP, "lever turn free", round(lever_turn(FREE_TOP), 1),
          "click", round(lever_turn(OP_TOP), 2))
    print("J2 cams (arm frame):", [round(a % 360, 1) for a in J2_CAMS])
    print("J3 cams (crank frame):", [round(a % 360, 1) for a in J3_CAMS])
    print("J1: lever face", J1_EDGE, "flag flat", round(J1_FLAG_FLAT, 2), "width", round(J1_FLAG_W, 2))
    for n, lim in (("J1", J1_LIM), ("J2", J2_LIM), ("J3", J3_LIM)):
        print(n, "trips", lim, "working range", working_range(lim), "max travel", max_travel(lim))
