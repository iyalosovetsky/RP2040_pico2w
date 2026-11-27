"""
limits.py - limit switches for J1, J2 and J3: three bare roller-lever microswitches (KW11-3Z-5A,
the Omron SS-5GL2 case), the printed bracket that carries two of them on the turret, the collar
that carries the third on the base, the J1 flag - plus the checks that the cams work them.

Builds cad/limits.FCStd and the print files
  limit_plate.stl/.step  - bracket on the turret plate between the cheeks: a seat for the J2 switch
                           behind the J1 axis and one for the J3 switch in front, and an arm out over
                           the plate's rear edge for the J1 flag. Print flat, no supports.
  limit_flag.stl/.step   - J1 flag: a saddle that slides onto the end of that arm, M3x12 + nut; its
                           underside is the J1 cam (flat + two 45 deg bevels). Print on its outer face.
  limit_collar_front.stl - half collar round the base housing with the riser the J1 switch stands on,
  limit_collar_rear.stl  - the other half with the pad for the SKR Pico's plate (electronics.py);
                           4x M3x20 + nuts pull them together. Print both as modelled.
Hardware for the switches: 6x M2x12 and 6 M2 nuts.
Needs upper_arm.FCStd (and the files it uses) in the same folder; endstop_dims.py holds the
switch's dimensions and the installation numbers, read that first.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/limits.py --pass cad/limits.FCStd

Layout (turret frame, shoulder axis along Y at z = shoulder_z): the J2 and J3 switches lie flat on
seats 6 mm above the turret plate, their rollers 23.8 mm under the shoulder axis and 3.35 mm either
side of the J1 axis. J2's is behind the axis, lever face to +y: the two cams on the J2-side plate
(y 9..15.5) pass over its roller. J3's is the same thing turned half a turn: in front, lever face
to -y, under the cams on the crank's root ring (y -25.5..-20.5). One switch per joint trips at both
ends of travel. J1's switch stands against a riser on a collar clamped round the base housing,
lever face up, roller on top; the flag hangs from the bracket's arm behind the turret and passes
over it from either side.
A cam's flat holds the roller 0.6 mm past the switch's click; each switch slides +-1.5 mm towards
its cam on two slotted M2 screws to get that right.

Fitting:
  1. Solder the leads to the switches first (COM and NC, or COM and NO - see the README).
  2. Take out the two hub screws at the front (x = +-13, y = -7.5). An M2 nut into each of the four
     slots in the bracket's underside (the turret plate keeps them in). Bracket down between the
     cheeks, the two screws back as M3x25, their heads down the two wells in the seats.
  3. A switch on each seat, lever towards the nearer cheek, its hinge end against the fence;
     2x M2x12 down through it into the nuts. Loose.
  4. Arm on. Turn the joint by hand until a cam's flat is over the roller. Slide the switch away
     from the cam until it clicks open, then towards it until it clicks, then 0.6 mm more;
     tighten. Turn the cam off the roller: the switch must click back (if not, it is too close).
  5. J1: flag onto the arm's end from behind (M3x12 down into the nut under the arm). The two
     collar halves round the housing with their tops 1 mm under its top edge, 4x M3x20 + nuts.
     Two M2 nuts down the channels in the riser, the switch against the riser's face, roller up,
     2x M2x12. Turn the collar until the roller is under the middle of the flag with the arm
     pointing where "straight ahead" should be backwards, set the switch's height the same way as
     in 4, tighten everything.
"""

import math
import os
import sys

import FreeCAD as App
import Part
import Import
import Mesh

out = os.path.abspath(next(a for a in sys.argv if a.endswith(".FCStd")))
here = os.path.dirname(out)
sys.path.insert(0, here)
import endstop_dims as ES  # noqa: E402

for f in ("pg27", "base", "turret", "upper_arm"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
tur, ua, bas = App.getDocument("turret"), App.getDocument("upper_arm"), App.getDocument("base")
doc = App.newDocument("Limits")
doc.saveAs(out)
V = App.Vector

tp = tur.getObject("Params")
SH_Z = tp.shoulder_z.Value            # shoulder axis
TOP = tp.plate_top.Value              # turret plate top
CHEEK = tp.cheek_in.Value             # cheek inner faces |y|
HUB_R = tp.hub_scr_r.Value
HR = bas.getObject("Params").body_od.Value / 2   # base housing radius
BODY_H = bas.getObject("Params").body_h.Value    # its top
Z_SEAT = SH_Z - ES.ROLLER_DEPTH - ES.SW_T / 2   # the J2/J3 switches lie on this
BASE_T = 2.5                          # bracket floor
HUB_SEAT = 2.8                        # the two hub screws' heads sit this high over the turret plate: above the
                                      # roofs of the M2 nut slots, which reach under them
NUT_W, NUT_C, NUT_TOP = ES.M2_NUT_AF + 0.3, 2.45, 2.0   # M2 nut slot: holds the nut by its flats; nut corner +
                                      # clearance along the slot; open underneath, this deep
NUT_CH = 2.0                          # J1: the nut channels' width along the screw
SLOT_W = 2.4
WALL = ES.M2_LEN - ES.SW_T - ES.M2_NUT_T   # plastic between a switch and its nut: the screw ends flush with the nut
X0 = -(ES.ROLLER_XR + ES.ROLLER_X)    # J2 switch's hinge end, x
Y2 = ES.J2_FACE - ES.PRESS_TOP        # J2 switch's lever face
Y3 = ES.J3_FACE + ES.PRESS_TOP        # J3 switch's lever face
MIRROR_Y = Y2 + Y3                    # the J3 side is the J2 side turned half a turn about (0, MIRROR_Y / 2)
L, H, T = ES.SW_L, ES.SW_H, ES.SW_T


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def show(name, shape, label):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.Label = label
    return o


# ----------------------------------------------------------- the switch ---
# switch frame: x along the body from the hinge end, lever face at y = 0 with the body at y < 0, z up from the
# face it lies on
def switch_body():
    b = box(0, L, -H, 0, 0, T).cut(box(ES.SW_STEP_X, L + 1, -ES.SW_STEP, 1, -1, T + 1))
    for hx, hy in ES.SW_HOLES:
        b = b.cut(cyl(ES.SW_HOLE_D / 2, hx, hy, -1, T + 1))
    hx, hy = ES.LEV_HINGE
    return b.fuse([box(ES.SW_PLUNGER_X - 0.9, ES.SW_PLUNGER_X + 0.9, -0.01, 0.5, T / 2 - 1.0, T / 2 + 1.0),   # plunger
                   box(hx - 1.5, hx + 1.5, -0.01, hy + 0.7, 0.4, ES.LEV_Z[0] - 0.05),                          # hinge
                   box(hx - 1.5, hx + 1.5, -0.01, hy + 0.7, ES.LEV_Z[1] + 0.05, T - 0.4)]).removeSplitter()    # bracket


def terminals():
    return Part.makeCompound([box(x - 0.25, x + 0.25, -H - ES.SW_TERM_L, -H, T / 2 - 1.6, T / 2 + 1.6)
                              for x in ES.SW_TERM_X])


def wires():
    """keep-out for the checks only: the soldered leads beyond the terminals"""
    return box(0.3, L - 0.3, -H - ES.SW_TERM_L - ES.SW_WIRE, -H - 0.5, 0.5, T - 0.5)


def lever(top):
    """the strip lever with its roller, the roller's top `top` above the lever face (ES.PRESS_TOP: on a cam's flat)"""
    hx, hy = ES.LEV_HINGE
    r = ES.ROLLER_D / 2
    cy = ES.PRESS_TOP - r                         # roller axis, on the flat
    z0, z1 = ES.LEV_Z
    s = box(hx - 1.0, ES.ROLLER_X + 1.3, hy - ES.LEV_T / 2, hy + ES.LEV_T / 2, z0, z1).fuse([
        box(ES.ROLLER_X - 1.3, ES.ROLLER_X + 1.3, hy, cy + 1.0, z0, z0 + ES.LEV_T),      # the fork that holds the roller
        box(ES.ROLLER_X - 1.3, ES.ROLLER_X + 1.3, hy, cy + 1.0, z1 - ES.LEV_T, z1),
        cyl(r, ES.ROLLER_X, cy, T / 2 - ES.ROLLER_W / 2, T / 2 + ES.ROLLER_W / 2)])
    s.rotate(V(hx, hy, 0), V(0, 0, 1), ES.lever_turn(top))
    return s


LOW = ES.PRESS_TOP - 0.2      # a cam that reaches a lever here has pushed the roller deeper than its flat should
SW = {"body": switch_body(), "term": terminals(), "wires": wires(), "lever": lever(ES.FREE_TOP),
      "lever_max": lever(ES.FREE_TOP_MAX), "lever_op": lever(ES.OP_TOP), "lever_low": lever(LOW)}


def place(shape, j3):
    s = shape.copy()
    if j3:   # half a turn about Z
        s.rotate(V(0, 0, 0), V(0, 0, 1), 180)
        s.translate(V(-X0, Y3, Z_SEAT))
    else:
        s.translate(V(X0, Y2, Z_SEAT))
    return s


switches = {tag: {k: place(v, j3) for k, v in SW.items()} for tag, j3 in (("J2", False), ("J3", True))}
# J1: switch upright in front of the J1 axis - switch x -> +y, its lever face up, its thickness out along +x.
# The roller is over y = 0 at its click point.
Y0_J1 = -ES.ROLLER_X + ES.J1_ROLLER_OFF
M_J1 = App.Matrix(0, 0, 1, ES.J1_SEAT_X, 1, 0, 0, Y0_J1, 0, 1, 0, ES.J1_EDGE, 0, 0, 0, 1)
switches["J1"] = {k: v.transformGeometry(M_J1) for k, v in SW.items()}
for tag in ("J1", "J2", "J3"):
    # (the viewer's export takes the lever as child 2 of this compound)
    show(f"Endstop{tag}", Part.makeCompound([switches[tag][k] for k in ("body", "term", "lever")]),
         f"{tag} limit switch, KW11-3Z-5A roller lever (bought)")

# ---------------------------------------------------------- the bracket ---
BLK_Y = (-H - ES.ADJ - 0.3, 0.3)      # a seat, across the lever face (switch frame)


def half(sgn):
    """Seat, fence, nut slots and screw slots of the J2 switch (sgn = 1); the J3 side is that turned half a
    turn. The nuts go into slots in the bracket's underside before it goes on the turret (the turret plate then
    holds them in); they slide along with the screw when the switch is set, and the flats stop them turning.
    M2x12 ends flush with a nut pulled up to its slot's roof, 0.4 mm over the turret plate."""
    def bx(x0, x1, y0, y1, z0, z1):
        if sgn > 0:
            return box(x0, x1, y0, y1, z0, z1)
        return box(-x1, -x0, MIRROR_Y - y1, MIRROR_Y - y0, z0, z1)

    xs = lambda x: x + X0                 # switch x -> turret x  # noqa: E731
    ys = lambda y: y + Y2                 # switch y -> turret y  # noqa: E731
    solids = [bx(xs(-0.6), xs(L + 0.6), ys(BLK_Y[0]), ys(BLK_Y[1]), TOP + BASE_T - 0.01, Z_SEAT),
              # fence at the hinge end: the switch slides along it, so it stays square to the cam's path
              bx(xs(-2.2), xs(-0.2), ys(BLK_Y[0]), ys(BLK_Y[1]), TOP + BASE_T - 0.01, Z_SEAT + 3.0)]
    cuts = []
    for hx, hy in ES.SW_HOLES:
        cuts += [bx(xs(hx) - NUT_W / 2, xs(hx) + NUT_W / 2, ys(hy) - ES.ADJ - NUT_C, ys(hy) + ES.ADJ + NUT_C,
                    TOP - 1, TOP + NUT_TOP),
                 bx(xs(hx) - SLOT_W / 2, xs(hx) + SLOT_W / 2, ys(hy) - ES.ADJ - SLOT_W / 2, ys(hy) + ES.ADJ + SLOT_W / 2,
                    TOP + NUT_TOP - 0.5, Z_SEAT + 1)]
    return solids, cuts


z0, z1 = TOP, TOP + BASE_T
solids = [box(-20, 20, -CHEEK + 0.2, CHEEK - 0.2, z0, z1),                    # between the cheeks: locates it in y
          box(X0 - 2.8, -20 + 0.01, Y2 + BLK_Y[0] - 0.6, Y2 + BLK_Y[1] + 0.6, z0, z1),          # tongue under the J2 seat
          box(20 - 0.01, -X0 + 2.8, MIRROR_Y - Y2 - BLK_Y[1] - 0.6, MIRROR_Y - Y2 - BLK_Y[0] + 0.6, z0, z1)]  # ... the J3 seat
cuts = [cyl(4.5, 0, 0, z0 - 1, Z_SEAT + 4)]                                    # over the turret's centre hole (old wedge screw)
for k in range(3):
    a = math.radians(90 + 120 * k)
    x, y = HUB_R * math.cos(a), HUB_R * math.sin(a)
    if y > 0:
        cuts.append(cyl(4.5, x, y, z0 - 1, z1 + 1))                            # this hub screw stays on the turret
    else:
        cuts += [cyl(1.7, x, y, z0 - 1, Z_SEAT + 4), cyl(3.3, x, y, z0 + HUB_SEAT, Z_SEAT + 4)]   # head: a well down the seat
for sgn in (1, -1):
    s, c = half(sgn)
    solids += s
    cuts += c
# J1: arm out over the rear edge of the turret plate; its thick end carries the flag
FR0, FR1 = ES.J1_FLAG_R
ARM_W, BOSS_T = 10.0, 5.0
solids += [box(-FR1, X0 - 2.8 + 0.01, -ARM_W / 2, ARM_W / 2, z0, z1), box(-FR1, -FR0, -ARM_W / 2, ARM_W / 2, z0, z0 + BOSS_T)]
FX = -(FR0 + FR1) / 2
cuts += [cyl(1.7, FX, 0, z0 - 1, z0 + BOSS_T + 1), box(FX - 2.85, FX + 2.85, -3.3, 3.3, z0 - 1, z0 + 2.8)]
plate = solids[0].fuse(solids[1:]).removeSplitter()
plate = plate.cut(cuts[0].fuse(cuts[1:])).removeSplitter()
lp = show("LimitPlate", plate, "Limit switch bracket (print)")

# ------------------------------------------------------------ J1 flag ---
# saddle over the arm's end: block from the roller up to above the arm, slot for the arm's end right
# through it, so it can only slide along the arm and the screw stops that. Its underside is the cam.
FZ0, FZ1 = ES.J1_FLAG_Z0, TOP + BOSS_T + 3.0
fw = ES.J1_FLAG_W / 2
flag = box(-FR1, -FR0, -fw, fw, FZ0, FZ1)
flag = flag.cut(box(-FR1 - 1, -FR0 + 1, -ARM_W / 2 - 0.15, ARM_W / 2 + 0.15, TOP - 0.5, TOP + BOSS_T + 0.2))
flag = flag.cut(cyl(1.7, FX, 0, TOP + BOSS_T, FZ1 + 1))
c = ES.J1_BEVEL
for sg in (1, -1):   # the two long bottom edges: the roller runs up them from either side
    w = Part.makePolygon([V(0, sg * fw, FZ0), V(0, sg * (fw - c), FZ0), V(0, sg * fw, FZ0 + c), V(0, sg * fw, FZ0)])
    flag = flag.cut(Part.Face(w).extrude(V(FR1 - FR0 + 2, 0, 0)).translated(V(-FR1 - 1, 0, 0)))
flag = flag.removeSplitter()
fl = show("LimitFlag", flag, "J1 limit flag (print, M3x12 + nut)")

# ---------------------------------------------------------- J1 collar ---
CT, CZ1 = ES.J1_COLLAR_T, BODY_H - 1.0
CZ0 = CZ1 - ES.J1_COLLAR_H
SEAT_X = ES.J1_SEAT_X                                   # the riser's face
RX0, RZ1 = HR, ES.J1_EDGE - 0.3                         # riser: from the housing's surface out to the face, up to the lever face
                                                        # (not further in: over the housing's top it would hang in the air)
RZ0 = (ES.J1_EDGE - H - ES.ADJ - 1.0) - (SEAT_X - RX0)  # its underside rises 45 deg outwards and is clear of the terminals
ring = Part.makeCylinder(HR + CT, CZ1 - CZ0, V(0, 0, CZ0))
ears = [box(-8, 8, sg * (HR + 2), sg * (HR + 15), CZ0, CZ1) if sg > 0 else box(-8, 8, -(HR + 15), -(HR + 2), CZ0, CZ1)
        for sg in (1, -1)]
_w = [V(RX0, 0, RZ0), V(SEAT_X, 0, RZ0 + SEAT_X - RX0), V(SEAT_X, 0, RZ1), V(RX0, 0, RZ1)]
riser = Part.Face(Part.makePolygon(_w + _w[:1])).extrude(V(0, L + 1.2, 0)).translated(V(0, Y0_J1 - 0.6, 0))
# the SKR Pico's pad at the back: electronics.py screws the board plate to its flat face
pad = box(-ES.SKR_PAD_X, -40, -ES.SKR_PAD_W, ES.SKR_PAD_W, CZ0, ES.SKR_PAD_Z1)
col = ring.fuse(ears + [riser, pad])
col = col.cut(Part.makeCylinder(HR, ES.J1_EDGE + 2 - CZ0 + 1, V(0, 0, CZ0 - 1)))    # the housing, and nothing over its edge
ccuts = [box(-0.5, 0.5, -HR - 20, HR + 20, CZ0 - 1, ES.J1_EDGE + 2)]                 # split into halves
for hx, hy in ES.SW_HOLES:
    y, z = Y0_J1 + hx, ES.J1_EDGE + hy
    ccuts += [box(SEAT_X - WALL - NUT_CH, SEAT_X - WALL, y - NUT_W / 2, y + NUT_W / 2, z - ES.ADJ - NUT_C, RZ1 + 1),   # nut channel, open on top
              box(RX0 - 1, SEAT_X + 1, y - SLOT_W / 2, y + SLOT_W / 2, z - ES.ADJ - SLOT_W / 2, z + ES.ADJ + SLOT_W / 2)]  # slot, right through
for sg in (1, -1):
    y = sg * (HR + 8.5)
    for z in ES.J1_COLLAR_SCR_Z:
        ccuts += [Part.makeCylinder(1.7, 20, V(-10, y, z), V(1, 0, 0)),
                  box(-9, -5.2, y - 2.85, y + 2.85, z - 3.3, z + 3.3)]   # nut pocket in the rear half
    y = sg * ES.SKR_SCR_Y
    ccuts += [Part.makeCylinder(1.7, ES.SKR_PAD_X - 48, V(-ES.SKR_PAD_X - 1, y, ES.SKR_SCR_Z), V(1, 0, 0)),
              box(-ES.SKR_PAD_X + 3.4, -ES.SKR_PAD_X + 6.0, y - 2.95, y + 2.95, ES.SKR_SCR_Z - 3.3, ES.SKR_PAD_Z1 + 1)]   # pad nut, from above
col = col.cut(ccuts[0].fuse(ccuts[1:])).removeSplitter()
halves = sorted(col.Solids, key=lambda h: -h.BoundBox.XMax)
if len(halves) != 2:
    sys.exit(f"collar: expected 2 solids, got {len(halves)}")
cf = show("LimitCollarFront", halves[0], "J1 collar, front half with the switch's riser (print)")
cr = show("LimitCollarRear", halves[1], "J1 collar, rear half (print)")

# ------------------------------------------------------------ context ---
ctx = doc.addObject("App::DocumentObjectGroup", "Context")
for d, n in ((tur, "TurretBody"), (tur, "J1HubScrews"), (ua, "UpperArm"), (ua, "Crank"), (bas, "BaseHousing")):
    lk = doc.addObject("App::Link", "Ctx_" + n)
    lk.LinkedObject = d.getObject(n)
    lk.LinkTransform = True
    ctx.addObject(lk)
doc.recompute()
doc.save()

def export(shape, stem, rot=None):
    s = shape.copy()
    if rot:
        s.rotate(V(0, 0, 0), rot[0], rot[1])
    s.translate(V(0, 0, -s.BoundBox.ZMin))
    Import.export([Part.show(s, stem)], os.path.join(here, stem + ".step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.05))
    m.write(os.path.join(here, stem + ".stl"))
    doc.removeObject(stem)


export(plate, "limit_plate")
export(flag, "limit_flag", (V(0, 1, 0), -90))     # outer face (the one away from the turret) on the bed
export(halves[0], "limit_collar_front")
export(halves[1], "limit_collar_rear")
for o in (fl, cf, cr):
    print(f"{o.Name} vol {o.Shape.Volume / 1000:.2f} cm3 valid {o.Shape.isValid()} solids {len(o.Shape.Solids)}")
print(f"LimitPlate vol {plate.Volume / 1000:.2f} cm3 valid {plate.isValid()} solids {len(plate.Solids)}")
print(f"switch screws J2/J3: M2x{ES.M2_LEN:g} from the switch's top ends {Z_SEAT + T - ES.M2_LEN - TOP:.1f} mm over the turret plate; "
      f"nut slot roof {NUT_TOP:.1f} mm over it, so the screw is {TOP + NUT_TOP - (Z_SEAT + T - ES.M2_LEN):.1f} mm into the nut")
print(f"switch screws J1: M2x{ES.M2_LEN:g} ends {WALL + NUT_CH - (ES.M2_LEN - T):.1f} mm short of the nut channel's far wall, "
      f"{ES.M2_LEN - T - WALL:.1f} mm into the nut")
rise = ES.FREE_TOP_MAX - ES.PRESS_TOP
print(f"bevels: the free roller stands up to {rise:.1f} mm over a cam's flat; bevels J1 {ES.J1_BEVEL} J2 {ES.J2_BEVEL} "
      f"J3 {ES.J3_BEVEL} mm (a roller up to {ES.ROLLER_D / 2 - 0.7:.1f} mm higher than a bevel still meets its edge at 45 deg or less)")

# -------------------------------------------------------------- checks ---
def posed(shape, ang):
    r = shape.copy()
    r.rotate(V(0, 0, 0), V(0, 1, 0), -ang)
    r.translate(V(0, 0, SH_Z))
    return r


arm = Part.makeCompound([ua.getObject(n).Shape
                         for n in ("UpperArmJ2", "UpperArmJ2Cap", "UpperArmJ3", "Spacer0", "Spacer1", "Spacer2")])
crank = Part.makeCompound([ua.getObject(n).Shape for n in ("J3Crank", "J3CrankCap")])
static = {"LimitPlate": plate, "TurretBody": tur.getObject("TurretBody").Shape,
          "J1HubScrews": tur.getObject("J1HubScrews").Shape}
for tag in switches:
    static[f"Endstop{tag}"] = Part.makeCompound([switches[tag][k] for k in ("body", "term", "wires")])
    static[f"Lever{tag}"] = switches[tag]["lever_max"]      # free, as high as it may stand
    static[f"LeverLow{tag}"] = switches[tag]["lever_low"]   # pushed past a cam's flat: no cam may reach it
static.update({"LimitFlag": flag, "LimitCollarFront": halves[0], "LimitCollarRear": halves[1],
               "BaseHousing": bas.getObject("BaseHousing").Shape})

print("static fit:")
bad = 0
# (the bracket against the hub screws is left out: the model still has the two M3x20 with their heads
# on the turret, where the bracket's screw seats now are)
pairs = [("LimitPlate", "TurretBody"), ("EndstopJ2", "EndstopJ3"), ("LimitFlag", "LimitPlate"), ("LimitFlag", "TurretBody"),
         ("LimitCollarFront", "BaseHousing"), ("LimitCollarRear", "BaseHousing"), ("LimitCollarFront", "LimitCollarRear"),
         ("EndstopJ1", "LimitCollarFront"), ("EndstopJ1", "BaseHousing"), ("LeverJ1", "LimitCollarFront"),
         ("LeverLowJ1", "LimitCollarFront"), ("LeverJ1", "BaseHousing")]
for t in ("J2", "J3"):
    pairs += [(f"Endstop{t}", "LimitPlate"), (f"Endstop{t}", "J1HubScrews"), (f"Endstop{t}", "TurretBody"),
              (f"Lever{t}", "LimitPlate"), (f"LeverLow{t}", "LimitPlate"), (f"Lever{t}", "TurretBody")]
pairs += [("LeverJ2", "EndstopJ3"), ("LeverJ3", "EndstopJ2")]
for a, b in pairs:
    v = static[a].common(static[b]).Volume
    if v > 0.01:
        bad += 1
        print(f"  overlap {a} x {b}: {v:.1f} mm3")
if not bad:
    print("  none")

# the joints, 6 deg past their trip points; the crank and the arm don't meet the static parts together.
# A free lever is there to be pushed, so it is not in the sweep; LeverLow* is: a cam must never push that far.
worst, pressed = {}, {"J2": [], "J3": []}
STEP = 0.5
for tag, shape, lo, hi, off in (("J2", arm, ES.J2_LIM[0] - 6, ES.J2_LIM[1] + 6, 0),
                                ("J3", crank, ES.J3_LIM[0] - 6, ES.J3_LIM[1] + 6, 180)):
    n = int(round((hi - lo) / STEP))
    for i in range(n + 1):
        ang = lo + i * STEP
        mv = posed(shape, ang + off)
        if i % 4 == 0 or min(abs(ang - lo), abs(ang - hi)) < 16:   # every 2 deg is plenty away from the cams' work
            for sn, st in static.items():
                if sn in ("TurretBody", "BaseHousing", "LimitCollarFront", "LimitCollarRear", "EndstopJ1",
                          "LeverJ1", "LeverLowJ1", "LeverJ2", "LeverJ3"):
                    continue   # the turret: upper_arm.py checks it; the rest belongs to J1, below
                v = mv.common(st).Volume
                if v > 0.01 and v > worst.get((tag, sn), (0, 0))[0]:
                    worst[(tag, sn)] = (v, ang)
        for bt in ("J2", "J3"):
            if mv.common(switches[bt]["lever_op"]).Volume > 0.001:
                pressed[tag].append((bt, ang))
# J1: everything on the turret against everything on the base, a full turn
pgd = App.getDocument("pg27")
onturret = [tur.getObject("TurretBody").Shape, plate, static["EndstopJ2"], static["EndstopJ3"],
            static["LeverJ2"], static["LeverJ3"]]
for n in ("J2_Motor", "J3_Motor"):
    body = pgd.getObject("Motor_NEMA17").Shape.fuse([pgd.getObject(k).Shape for k in ("Flange", "Gearbox")])
    body.Placement = tur.getObject(n).Placement.multiply(body.Placement)
    onturret.append(body)
onturret = Part.makeCompound(onturret)        # without the flag: nothing else may touch even the free lever
onbase = {k: static[k] for k in ("LimitCollarFront", "LimitCollarRear", "EndstopJ1", "LeverJ1", "LeverLowJ1")}
j1_pressed = []
for i in range(int(360 / STEP) + 1):
    ang = -180 + i * STEP
    if i % 8 == 0:
        mv = onturret.copy()
        mv.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        for sn, st in onbase.items():
            v = mv.common(st).Volume
            if v > 0.01 and v > worst.get(("J1", sn), (0, 0))[0]:
                worst[("J1", sn)] = (v, ang)
    fm = flag.copy()
    fm.rotate(V(0, 0, 0), V(0, 0, 1), ang)
    if i % 8 == 0 or abs(ang) > 150:
        for sn in ("LimitCollarFront", "LimitCollarRear", "EndstopJ1", "LeverLowJ1"):
            v = fm.common(onbase[sn]).Volume
            if v > 0.01 and v > worst.get(("J1 flag", sn), (0, 0))[0]:
                worst[("J1 flag", sn)] = (v, ang)
    if abs(ang) > 150 and fm.common(switches["J1"]["lever_op"]).Volume > 0.001:
        j1_pressed.append(ang)
print("interference sweep (arm and crank against the switches, the bracket, the hub screws; the turret a full turn over the J1 collar):")
if not worst:
    print("  none")
for (tag, sn), (v, ang) in worst.items():
    print(f"  {tag} parts x {sn}: {v:.1f} mm3 at {tag}={ang}")
print("switch pressed (a cam has the roller at its click point or deeper):")
for tag in ("J2", "J3"):
    own = sorted(a for b, a in pressed[tag] if b == tag)
    other = [a for b, a in pressed[tag] if b != tag]
    runs, start = [], None
    for k, a in enumerate(own):
        if start is None:
            start = a
        if k == len(own) - 1 or own[k + 1] - a > STEP * 1.5:
            runs.append((start, a))
            start = None
    print(f"  {tag}: " + (", ".join(f"{a:g}..{b:g}" for a, b in runs) or "never")
          + (f"   !! also presses the other switch at {other}" if other else ""))
neg, posv = [a for a in j1_pressed if a < 0], [a for a in j1_pressed if a > 0]
print("  J1: " + (f"-180..{max(neg):g}, {min(posv):g}..180" if neg and posv else f"!! {j1_pressed}"))


def trip(hit, a_out, a_in):
    """joint angle where the switch clicks, between a_out (not pressed) and a_in (pressed)"""
    for _ in range(9):
        m = (a_out + a_in) / 2
        a_out, a_in = (a_out, m) if hit(m) else (m, a_in)
    return (a_out + a_in) / 2


def flag_at(ang):
    fm = flag.copy()
    fm.rotate(V(0, 0, 0), V(0, 0, 1), ang)
    return fm


print("trip points (what endstop_dims.py's *_LIM and the cam trims are set from):")
for tag, shape, off, lim in (("J2", arm, 0, ES.J2_LIM), ("J3", crank, 180, ES.J3_LIM)):
    hit = lambda a: posed(shape, a + off).common(switches[tag]["lever_op"]).Volume > 0.001   # noqa: E731
    lo, hi = trip(hit, lim[0] + 3, lim[0] - 3), trip(hit, lim[1] - 3, lim[1] + 3)
    print(f"  {tag}: {lo:.2f} and {hi:.2f} (wanted {lim[0]:g} and {lim[1]:g}: off by {lo - lim[0]:+.2f} and {hi - lim[1]:+.2f})")
hit = lambda a: flag_at(a).common(switches["J1"]["lever_op"]).Volume > 0.001   # noqa: E731
lo, hi = trip(hit, ES.J1_LIM[0] + 3, ES.J1_LIM[0] - 3), trip(hit, ES.J1_LIM[1] - 3, ES.J1_LIM[1] + 3)
print(f"  J1: {lo:.2f} and {hi:.2f} (wanted {ES.J1_LIM[0]:g} and {ES.J1_LIM[1]:g})")
