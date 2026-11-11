"""
limits.py - limit switches for J2 and J3: the two switch boards and the printed bracket
that carries them on the turret, plus the checks that the fingers work them.

Builds cad/limits.FCStd and the print file
  limit_plate.stl/.step - bracket on the turret plate between the cheeks. Print flat, no
                          supports (PLA-CF or PETG).
Needs upper_arm.FCStd (and the files it uses) in the same folder; endstop_dims.py holds the
board's dimensions and the installation numbers, read that first.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/limits.py --pass cad/limits.FCStd

Layout (turret frame, shoulder axis along Y at z = shoulder_z): both boards lie flat, parts up,
24 mm under the axis - below everything that turns there. J2's board is behind the J1 axis with
its lever edge to +y; the fingers on the J2-side plate (y 9..12) pass 1.5 mm from that edge.
J3's board is the same thing turned half a turn: in front, lever edge to -y, worked by the fingers
on the crank's root ring (y -20.5..-25.5). One switch per joint trips at both ends of travel.

Fitting:
  1. Take out the two hub screws at the front (x = +-13, y = -7.5), put the bracket down between
     the cheeks and put the screws back as M3x25 (the M3x20 ones are 1.5 mm short now). The third
     hub screw and the wedge screw stay as they are; the wedge screw can still be reached.
  2. An M3 nut into each of the four channels under the board seats, the boards on top with
     2x M3x6 each (M3x8 bottoms out), loose.
  3. Arm on. Push a finger of the plate / the crank over the lever by hand and slide the board
     towards it until its LED comes on, then about 1 mm more; the lever must still have a little
     travel left when the finger is over it. Tighten.
  4. Leave 0.5 mm between the crank and the J3 cheek when clamping the crank: the fingers pass
     0.9 mm from the board seats.
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
tur, ua = App.getDocument("turret"), App.getDocument("upper_arm")
doc = App.newDocument("Limits")
doc.saveAs(out)
V = App.Vector

tp = tur.getObject("Params")
SH_Z = tp.shoulder_z.Value            # shoulder axis
TOP = tp.plate_top.Value              # turret plate top
CHEEK = tp.cheek_in.Value             # cheek inner faces |y|
HUB_R = tp.hub_scr_r.Value
PCB_TOP = SH_Z - ES.PCB_DEPTH
SEAT = PCB_TOP - ES.BOARD_T           # the boards rest on this
BASE_T, POCKET = 2.5, 1.0             # bracket floor; depth of the pockets under the two hub screw heads
CH_W, CH_H = 6.6, 2.9                 # nut channel: the nut's corners (6.35) ride its walls
SLOT_W = 3.3
X_END = ES.TIP_END + ES.BOARD_L       # the boards' connector end, |x|
Y2 = ES.J2_FACE - ES.STANDOFF         # J2 board's lever edge
Y3 = ES.J3_FACE + ES.STANDOFF         # J3 board's lever edge
MIRROR_Y = Y2 + Y3                    # the J3 side is the J2 side turned half a turn about (0, MIRROR_Y / 2)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def show(name, shape, label):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.Label = label
    return o


# ------------------------------------------------------------ the board ---
# built in the photo's frame: x along the board, lever edge at y = 0 with the board at y < 0, z up
def board_parts():
    L, W = ES.BOARD_L, ES.BOARD_W
    pcb = box(0, L, -W, 0, -ES.BOARD_T, 0)
    for hx, hy in ES.HOLES + ((2.0, 2.7), (2.0, W - 2.7)):
        pcb = pcb.cut(cyl(ES.HOLE_D / 2, hx, -hy, -ES.BOARD_T - 1, 1))
    x0, x1, y0, y1, h = ES.SW
    sw = box(x0, x1, -y1, -y0, 0, h)
    n = math.hypot(ES.LEV_TIP_X - ES.LEV_HINGE_X, ES.LEV_TIP_OUT - ES.LEV_HINGE_OUT)
    lever = box(0, n, 0, 0.3, ES.LEV_Z0, ES.LEV_Z1)
    lever.rotate(V(0, 0, 0), V(0, 0, 1),
                 math.degrees(math.atan2(ES.LEV_TIP_OUT - ES.LEV_HINGE_OUT, ES.LEV_TIP_X - ES.LEV_HINGE_X)))
    lever.translate(V(ES.LEV_HINGE_X, ES.LEV_HINGE_OUT, 0))
    cx0, cx1, cy0, cy1, ch = ES.CONN
    conn = box(cx0, cx1, -cy1, -cy0, 0, ch)
    # keep-outs for the checks only: the plug with its lead, the solder joints underneath
    plug = box(cx0, cx1, -cy1, -cy0, ch, ES.PLUG_H)
    solder = box(x0, x1, -ES.TERM_Y - 3, -ES.TERM_Y, -ES.BOARD_T - ES.SOLDER, -ES.BOARD_T).fuse(
        box(cx0, cx1, -cy1, -cy0, -ES.BOARD_T - ES.SOLDER, -ES.BOARD_T))
    # the part of the free lever that a finger has to be over for the switch to have clicked
    probe = box(ES.LEV_HINGE_X + ES.LEV_PRESS, ES.LEV_TIP_X, ES.STANDOFF, ES.LEV_TIP_OUT,
                (ES.LEV_Z0 + ES.LEV_Z1) / 2 - 0.5, (ES.LEV_Z0 + ES.LEV_Z1) / 2 + 0.5)
    return {"pcb": pcb, "sw": sw, "lever": lever, "conn": conn, "plug": plug, "solder": solder, "probe": probe}


def place(shape, j3):
    s = shape.copy()
    if j3:   # half a turn about Z
        s.rotate(V(0, 0, 0), V(0, 0, 1), 180)
        s.translate(V(X_END, Y3, PCB_TOP))
    else:
        s.translate(V(-X_END, Y2, PCB_TOP))
    return s


bp = board_parts()
boards = {}
for tag, j3 in (("J2", False), ("J3", True)):
    boards[tag] = {k: place(v, j3) for k, v in bp.items()}
    o = show(f"Endstop{tag}", Part.makeCompound([boards[tag][k] for k in ("pcb", "sw", "lever", "conn")]),
             f"{tag} limit switch board (bought)")

# ---------------------------------------------------------- the bracket ---
def half(sgn):
    """Seat block, nut channels, slots and the rest pad of the J2 board (sgn = 1); the J3 side
    is that turned half a turn."""
    def bx(x0, x1, y0, y1, z0, z1):
        if sgn > 0:
            return box(x0, x1, y0, y1, z0, z1)
        return box(-x1, -x0, MIRROR_Y - y1, MIRROR_Y - y0, z0, z1)

    xb = lambda x: x - X_END              # board x -> turret x  # noqa: E731
    yb = lambda y: Y2 - y                 # board y -> turret y  # noqa: E731
    block = bx(xb(13.0), xb(ES.BOARD_L), yb(ES.TERM_Y - 0.7), yb(-0.6), TOP + BASE_T - 0.01, SEAT)
    pad = bx(xb(0.3), xb(2.8), yb(ES.BOARD_W - 1.0), yb(1.0), TOP + BASE_T - 0.01, SEAT)
    cuts = []
    for hx, hy in ES.HOLES:
        cuts.append(bx(xb(hx) - CH_W / 2, xb(hx) + CH_W / 2, yb(ES.TERM_Y - 0.7) - 1, yb(-0.6) + 1,
                       TOP + BASE_T, TOP + BASE_T + CH_H))
        # slot: the screw can move ADJ[0] towards the finger (-y on the board) and ADJ[1] away
        cuts.append(bx(xb(hx) - SLOT_W / 2, xb(hx) + SLOT_W / 2, yb(hy + ES.ADJ[1]) - SLOT_W / 2,
                       yb(hy + ES.ADJ[0]) + SLOT_W / 2, TOP + BASE_T + CH_H - 1, SEAT + 1))
    return [block, pad], cuts


z0, z1 = TOP, TOP + BASE_T
solids = [box(-20, 20, -CHEEK + 0.2, CHEEK - 0.2, z0, z1),                    # between the cheeks: locates it in y
          box(-X_END - 0.6, -20 + 0.01, Y2 - ES.BOARD_W - 0.6, Y2 + 0.6, z0, z1),          # tongue under the J2 board
          box(20 - 0.01, X_END + 0.6, Y3 - 0.6, Y3 + ES.BOARD_W + 0.6, z0, z1)]  # tongue under the J3 board
cuts = [cyl(4.5, 0, 0, z0 - 1, z1 + 1)]                                        # wedge screw + its washers
for k in range(3):
    a = math.radians(90 + 120 * k)
    x, y = HUB_R * math.cos(a), HUB_R * math.sin(a)
    if y > 0:
        cuts.append(cyl(4.5, x, y, z0 - 1, z1 + 1))                            # this hub screw stays on the turret
    else:
        cuts += [cyl(1.7, x, y, z0 - 1, z1 + 1), cyl(3.5, x, y, z1 - POCKET, z1 + 1)]
for sgn in (1, -1):
    s, c = half(sgn)
    solids += s
    cuts += c
plate = solids[0].fuse(solids[1:]).removeSplitter()
plate = plate.cut(cuts[0].fuse(cuts[1:])).removeSplitter()
lp = show("LimitPlate", plate, "Limit switch bracket (print)")

# ------------------------------------------------------------ context ---
ctx = doc.addObject("App::DocumentObjectGroup", "Context")
for d, n in ((tur, "TurretBody"), (tur, "J1HubScrews"), (ua, "UpperArm"), (ua, "Crank")):
    lk = doc.addObject("App::Link", "Ctx_" + n)
    lk.LinkedObject = d.getObject(n)
    lk.LinkTransform = True
    ctx.addObject(lk)
doc.recompute()
doc.save()

s = plate.copy()
s.translate(V(0, 0, -s.BoundBox.ZMin))
Import.export([Part.show(s, "limit_plate")], os.path.join(here, "limit_plate.step"))
m = Mesh.Mesh()
m.addFacets(s.tessellate(0.05))
m.write(os.path.join(here, "limit_plate.stl"))
doc.removeObject("limit_plate")
print(f"LimitPlate vol {plate.Volume / 1000:.2f} cm3 valid {plate.isValid()} solids {len(plate.Solids)}")

# -------------------------------------------------------------- checks ---
def posed(shape, ang):
    r = shape.copy()
    r.rotate(V(0, 0, 0), V(0, 1, 0), -ang)
    r.translate(V(0, 0, SH_Z))
    return r


arm = Part.makeCompound([ua.getObject(n).Shape for n in ("UpperArmJ2", "UpperArmJ3", "Spacer0", "Spacer1", "Spacer2")])
crank = ua.getObject("J3Crank").Shape
static = {"LimitPlate": plate, "TurretBody": tur.getObject("TurretBody").Shape,
          "J1HubScrews": tur.getObject("J1HubScrews").Shape}
for tag in boards:
    static[f"Endstop{tag}"] = Part.makeCompound([boards[tag][k] for k in ("pcb", "sw", "conn", "plug", "solder")])

print("static fit:")
bad = 0
# (the bracket against the hub screws is left out: the model still has the two M3x20 with their heads
# on the turret, where the bracket's screw seats now are)
for a, b in (("LimitPlate", "TurretBody"), ("EndstopJ2", "LimitPlate"),
             ("EndstopJ3", "LimitPlate"), ("EndstopJ2", "J1HubScrews"), ("EndstopJ3", "J1HubScrews"),
             ("EndstopJ2", "EndstopJ3")):
    v = static[a].common(static[b]).Volume
    if v > 0.01:
        bad += 1
        print(f"  overlap {a} x {b}: {v:.1f} mm3")
if not bad:
    print("  none")

# the joints, 1.5 deg past the trip points; the crank and the arm don't meet the static parts together
worst, pressed = {}, {"J2": [], "J3": []}
STEP = 0.5
for tag, shape, lo, hi, off in (("J2", arm, ES.J2_LIM[0] - 3, ES.J2_LIM[1] + 3, 0),
                                ("J3", crank, ES.J3_LIM[0] - 3, ES.J3_LIM[1] + 3, 180)):
    n = int(round((hi - lo) / STEP))
    for i in range(n + 1):
        ang = lo + i * STEP
        mv = posed(shape, ang + off)
        if i % 4 == 0:   # every 2 deg is plenty for the solids
            for sn, st in static.items():
                if sn == "TurretBody":
                    continue   # upper_arm.py checks that one, over the working range
                v = mv.common(st).Volume
                if v > 0.01 and v > worst.get((tag, sn), (0, 0))[0]:
                    worst[(tag, sn)] = (v, ang)
        for bt in boards:
            if mv.common(boards[bt]["probe"]).Volume > 0.05:
                pressed[tag].append((bt, ang))
print("interference sweep (arm and crank against the boards, the bracket, the hub screws):")
if not worst:
    print("  none")
for (tag, sn), (v, ang) in worst.items():
    print(f"  {tag} parts x {sn}: {v:.1f} mm3 at {tag}={ang}")
print("switch pressed (finger over the working part of the lever):")
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
          + (f"   !! also presses the other board at {other}" if other else ""))
