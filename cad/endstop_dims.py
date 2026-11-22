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
arm's plane. One switch has to stop its joint at both ends, so a finger reaches it from one
side at one end and from the other side at the other - and a finger that meets the lever from
its free end jams into it end-on (the user caught that on the printed bracket). So the fingers
never touch the lever: a printed slider sits in a channel in the bracket across the lever edge,
its back on the middle of the lever, its nose - a V with a flat top - in the fingers' path. A
finger coming from either side runs up the V, pushes the slider in and with it the lever, and
just runs on along the flat top if the joint overshoots. The finger's face is STANDOFF from the
lever edge; the lever's free end stays well short of it.
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



def lever_out(x):
    """how far the free lever stands out past the lever edge at board x"""
    return LEV_HINGE_OUT + (x - LEV_HINGE_X) * (LEV_TIP_OUT - LEV_HINGE_OUT) / (LEV_TIP_X - LEV_HINGE_X)


# ---- the slider between the fingers and the lever (board frame; limit_slider.stl, one per switch) ----
SL_XC = 30.65             # its middle, where its rib presses the lever: 9.55 from the hinge; with the flat it puts
                          # the trip points where the fingers were made for (J2_LIM etc.)
SL_REST = 3.2             # rib's back from the lever edge with nothing on the nose: its shoulders stop it there
SL_PRESSED = 1.3          # with a finger on the nose (the switch clicks at about 1.9, bottoms out at about 0.5)
SL_RIB, SL_RIB_W = 1.0, 1.6       # the rib that touches the lever: only there, the lever rises towards its free end
SL_BODY = 2.0                     # body behind the nose
SL_NOSE, SL_FLAT, SL_ANG = 2.4, 1.4, 35.0   # V nose: depth, flat top, flanks this far off the finger's path
SL_Z0, SL_ZN, SL_Z1 = 0.6, 4.3, 5.7        # underside, top of the nose, top of the rest (above the PCB; the lever
                                            # strip is at 1.2..4.6). Printed on its flat underside
SL_SHOULDER = (0.6, 1.0)  # shoulders behind the body: this long, standing out this far each side; they stop it
                          # against the step in the channel, so it can't come out towards the fingers
# the cover: a flat plate over the switch and the back of the slider (a finger drags the slider up on one
# side), held by the board's own screw in hole 17 (M3x16) through a boss down to the PCB - no screw or nut of
# its own. It stops short of hole 36: over the J3 board the J3-side arm plate's and the crank's rings
# (r 19.2 round the shoulder axis) pass 16.5 under the axis there; hole 36 keeps its M3x8 on the PCB
COVER_Z = (6.0, 7.5)      # above the PCB: clear of the switch body (5.8); the slider stops 0.3 under it
COVER_X = (14.0, 31.6)
COVER_Y0 = -5.7           # back edge over the PCB (the LED and the solder side stay uncovered)
COVER_BOSS_D = 6.0
SL_HW = SL_FLAT / 2 + SL_NOSE / math.tan(math.radians(SL_ANG))   # half width of the body
STANDOFF = SL_PRESSED + SL_RIB + SL_BODY + SL_NOSE   # finger face to the board's lever edge
# the lever was taken as clicked when held down to 1.5 out at LEV_PRESS from the hinge; same angle at SL_XC
_CLICK_RAD = (lever_out(LEV_HINGE_X + LEV_PRESS) - 1.5) / LEV_PRESS


def sl_click(xc):
    """push on the nose that clicks the switch, for a slider at board x xc"""
    return SL_REST - (lever_out(xc) - _CLICK_RAD * (xc - LEV_HINGE_X))


SL_CLICK = sl_click(SL_XC)

# ---- where the boards sit (turret frame, relative to the shoulder axis) ----
PCB_DEPTH = 24.0        # PCB top face below the shoulder axis
J3_SHIFT = -1.5         # the J3 board sits this much further in (towards the J1 axis) than the J2 board's mirror
                        # image: the hub screw at (13, -7.5) needs the room beside its hole-36 nut. Its slider is
                        # where the J2 one is mirrored (the crank's fingers are made for that), so on the J3
                        # board it presses the lever 1.5 mm nearer the hinge
TIP_END = 4.0           # the board's switch end from the J1 axis (clear of the turret's centre hole)
ADJ = (-0.5, 1.0)       # slots: towards the finger / away from it
J2_FACE, J2_FINGER_T = 9.0, 3.0     # J2 fingers: on the +y plate, y 9..12 (its inner face works the lever)
J3_FACE, J3_FINGER_T = -20.5, 5.0   # J3 fingers: on the crank's root ring, y -20.5..-25.5
FINGER_R, FINGER_W, FINGER_CH = 29.0, 6.0, 1.2
# trip points: 1.5 deg outside the working range the kinematics allow (J2 35..150, J3 -70..35)
J2_LIM = (33.5, 151.5)
J3_LIM = (-71.5, 36.5)

# ---- J1 (base frame: table z = 0, J1 = Z) ----
# The board stands upright on a collar clamped round the base housing, in front of the J1 axis: parts
# outward, lever edge up and level. A flag under an arm of the J2/J3 bracket (so it turns with the
# turret, behind the J1 axis when the arm points forward) passes STANDOFF above that edge. It gets to
# the board from either side after a little under half a turn, so the one switch stops J1 both ways.
J1_PCB_X = 59.1           # PCB top (component) face: its back sits on a flat 1.5 mm proud of the collar
J1_FLAG_Z0 = 100.0        # the flag's underside (the flag passes STANDOFF over the lever edge)
J1_EDGE = J1_FLAG_Z0 - STANDOFF   # lever edge above the table
J1_HINGE_Y = -(LEV_TIP_X - LEV_HINGE_X + LEV_PRESS) / 2   # lever placed so both trip points are the same angle
J1_FLAG_R = (57.0, 68.0)  # flag, radially: the lever strip is at 60.3..64.4
J1_FLAG_W = 15.0          # and along its path
J1_COLLAR_T, J1_COLLAR_H = 4.0, 40.0   # collar round the base housing, z 44..84: it carries the SKR Pico too
J1_COLLAR_SCR_Z = (77.0, 50.0)          # the two M3 per side that pull its halves together
# SKR Pico board on the collar's rear half (electronics.py builds the plate and the board)
SKR_PAD_X, SKR_PAD_W = 62.0, 20.0       # pad's flat face at x = -SKR_PAD_X, |y| <= SKR_PAD_W
SKR_PAD_Z1 = 56.0                       # pad from the collar's bottom up to here; its nut slots open on top
SKR_SCR_Y, SKR_SCR_Z = 12.0, 50.0       # plate screws, M3x12 into nuts in the pad

J1_LIM = (-171.0, 171.0)  # where limits.py finds the J1 switch pressed

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
    print("slider: standoff", STANDOFF, "half width", round(SL_HW, 2), "click after", round(SL_CLICK, 2),
          "of", SL_REST - SL_PRESSED, "lever at its rib", round(lever_out(SL_XC), 2), "J1 edge", J1_EDGE)
    print("J2 fingers (arm frame):", [round(a, 1) for a in J2_FINGERS])
    print("J3 fingers (crank frame):", [round(a % 360, 1) for a in J3_FINGERS])
    for n, lim in (("J1", J1_LIM), ("J2", J2_LIM), ("J3", J3_LIM)):
        print(n, "trips", lim, "working range", working_range(lim), "max travel", max_travel(lim))
