"""
cable_dims.py - where the arm's cable bundle runs (plain numbers, no FreeCAD), shared by
upper_arm.py (hooks on the J2-side plate) and limits.py (the rail on the turret bracket).

The bundle: the J4 motor's lead (4 wires), the gripper servo's (3) and, for a spindle tool, two
power wires - about 8 mm across, in a braided sleeve or spiral wrap or just tied. Nothing is
enclosed: a plug has to pass everywhere, so it is open hooks, zip ties and free loops.

  forearm     two zip ties round the beam (nothing printed)
  elbow       a free loop, about 50 mm of slack, from the forearm to the first hook
  upper arm   three open hooks on the J2-side plate's lower edge (arm frame -z). Both rods - the
              drive rod and the lower levelling rod - run on the upper side of the arm at every
              pose; the lower edge is the one side nothing sweeps past. The hooks are part of the
              plate's outline, so they print flat with it; alternate ones open the other way.
  shoulder    the last hook sits on the plate's round end, 24 mm from the axis, so the loop from
              it to the turret needs only ~40 mm of slack over the whole J2 range
  turret      a rail on the limit switch bracket along the J2-side cheek: a tie block at its
              front end (where the loop lands), a fence that keeps the bundle out from under
              the J2 cams, and a tie block at its rear end, over the turret plate's rear edge.
              The J2/J3 motor leads and the switch leads join the bundle at the rear block.
  J1          from the rear block a free half loop down to the SKR Pico on the back of the base
              (about 250 mm: it wraps round the housing either way up to +-171 deg)
"""
BUNDLE_D = 8.0

# ---- hooks on the J2-side plate (arm frame: x along the link, z across it, the plate at y 9..16) ----
HOOK_W, HOOK_H = 10.0, 9.0      # pocket: along the edge, and down from it
HOOK_T = 3.0                    # wall
HOOK_GAP = 5.0                  # way in, between the lip and the plate's edge: one lead at a time goes through
HOOK_Y = 5.0                    # thickness, from the plate's inner face: 2 mm short of the outer face, so the hooks
                                # pass the bracket's fence with room
HOOKS = ((62.0, 1), (105.0, -1))   # on the straight lower edge: x of the pocket's middle, +1 = opens towards the elbow
HOOK_SHOULDER = 288.0           # the one on the round end: direction from the shoulder axis (deg, 270 = straight down
                                # across the link); clear of the low-limit cam at 237

# ---- rail on the limit switch bracket (turret frame) ----
RAIL_Y = (17.0, 25.6)           # along the J2-side cheek (inner face at 26), outside the cams' path (y <= 15.5)
RAIL_X = (-54.0, 48.0)          # from over the turret plate's rear edge (-50) to its front
FENCE_T, FENCE_H = 1.2, 6.5     # fence on the rail's inner edge, where the cams pass: |x| <= FENCE_X
FENCE_X = 29.0
TIE_L, TIE_H = 8.0, 4.4         # tie block: along the rail, and up from the bracket's floor
TIE_SLOT = (4.2, 2.2)           # zip tie slot through it, across the rail (takes ties up to 3.6 mm)
