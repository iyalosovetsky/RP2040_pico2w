"""
electronics.py - mount for the BTT SKR Pico V1.0 control board on the base housing.

Builds cad/electronics.FCStd and the print files
  skr_collar_rear.stl/.step  - half collar round the base housing with a pad for the board plate
  skr_collar_front.stl/.step - the plain half; 2x M3x16 + nuts pull them together (as the J1 collar)
  skr_plate.stl/.step        - flat plate with four standoffs for the board; 2x M3x12 into nuts in
                               the pad. Print it back face down, standoffs up.
The collar halves print as modelled (bottom face on the bed).
Needs base, turret, limits and pg27 .FCStd in the same folder.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/electronics.py --pass cad/electronics.FCStd

The board: 85 x 56, holes on the Raspberry Pi pattern, 58 x 49 apart, 3.5 in from the edge with the
Pi header and from the edge with the motor plugs (BTT SKR Pico V1.0-SIZE.pdf), for M2.5. Plugs go in
sideways on all four edges: motors along one long edge, endstops and thermistors along the other,
fans and the Pi UART on the short edge next to the holes, USB-C and the screw terminals (power, HE,
HB) on the far short edge. So the board stands upright on the back of the housing (-x, opposite the
J1 switch), the motor edge up, the parts outward, with room for the plugs at every edge:
  - above: the motor plugs end 18 mm over the edge at z 98; the J1 flag that sweeps round the
    housing is at r 57..68, the board at r >= 71
  - below: the endstop plugs reach down to z 6, 1 mm over the table flange, clear of the gussets
  - the collar sits between the gussets' tops (z 35) and the J1 collar (z 70), its pad carries the plate
Turning the collar on the housing sets the board's angle; it only clamps by friction like the J1 one.

Fitting:
  1. M3 nuts into the pockets: two in the rear half's ears (from the back), two in the pad (from above).
  2. Collar halves round the housing, M3x16 from the front half into the ear nuts, loose; turn it so the
     pad faces straight back (the J1 cable window is at the front), tighten.
  3. Plate on the pad, 2x M3x12 cap heads from the front into the pad nuts.
  4. Board on the standoffs, motor plugs up, USB-C to the right seen from behind: 4x M2.5x8 straight
     into the 2.2 holes (self-tapping in PETG; don't over-tighten).
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
for f in ("pg27", "base", "turret", "upper_arm", "limits"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
pgd, bas, tur, lim = (App.getDocument(n) for n in ("pg27", "base", "turret", "limits"))
doc = App.newDocument("Electronics")
doc.saveAs(out)
V = App.Vector

bp = bas.getObject("Params")
HR = bp.body_od.Value / 2              # housing radius
FL_T = bp.fl_t.Value                   # table flange top
GUS_TOP = FL_T + bp.gus_h.Value        # gussets end here

# board (SKR Pico V1.0)
B_L, B_W, B_T = 85.0, 56.0, 1.6
HOLES = [(u, v) for u in (3.5, 61.5) for v in (3.5, 52.5)]   # from the Pi-header edge, from the motor edge
PARTS_H = 11.0                         # tallest parts (screw terminals, capacitors) over the PCB
PLUG = 18.0                            # plug + start of the wire's bend, past the edge
HEAD_OUT = 3.5                         # the headers stand this far past the PCB's edge

# placement (world = base frame): the PCB's back face at x = -PCB_X, centred on y = 0, z PCB_Z0..+56
COL_Z0, COL_Z1, COL_T = 44.0, 56.0, 4.0
PAD_X, PAD_W = 62.0, 20.0              # pad's flat face at x = -PAD_X, |y| <= PAD_W
PL_T, ST_H, ST_R = 4.0, 5.0, 3.5       # plate, standoffs
PCB_X = PAD_X + PL_T + ST_H            # 71
PCB_Z0 = 24.0
PCB_Z1 = PCB_Z0 + B_W
SCR_Y, SCR_Z = 12.0, (COL_Z0 + COL_Z1) / 2


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def cyl_x(r, x0, x1, y, z):
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def show(name, shape, label, vis=True):
    o = doc.addObject("Part::Feature", name)
    o.Shape, o.Label, o.Visibility = shape, label, vis
    return o


def uv(u, v):
    """Board drawing coordinates (u from the Pi-header edge, v from the motor edge) -> world y, z."""
    return B_L / 2 - u, PCB_Z1 - v


# ------------------------------------------------------------ the board ---
x_b, x_f = -PCB_X, -PCB_X - B_T           # back and front face of the PCB
pcb = box(x_f, x_b, -B_L / 2, B_L / 2, PCB_Z0, PCB_Z1)
for u, v in HOLES:
    y, z = uv(u, v)
    pcb = pcb.cut(cyl_x(1.375, x_f - 1, x_b + 1, y, z))
hdr = 7.0   # header height over the PCB
headers = [box(x_f - hdr, x_f, *sorted(uv(5.5, 0)[0:1] + uv(76.0, 0)[0:1]), PCB_Z1 - 6, PCB_Z1 + HEAD_OUT),   # motors
           box(x_f - hdr, x_f, *sorted(uv(7.0, 0)[0:1] + uv(62.0, 0)[0:1]), PCB_Z0 - HEAD_OUT, PCB_Z0 + 6),   # endstops, TH
           box(x_f - hdr, x_f, B_L / 2 - 6, B_L / 2 + HEAD_OUT, *sorted((uv(0, 5.0)[1], uv(0, 50.0)[1]))),     # Pi, fans
           box(x_f - hdr, x_f, -B_L / 2 - HEAD_OUT, -B_L / 2 + 8, *sorted((uv(0, 2.0)[1], uv(0, 25.0)[1])))]  # USB-C, laser
terms = box(x_f - 10, x_f, -B_L / 2 - 1, -B_L / 2 + 8, PCB_Z0 + 1, PCB_Z0 + 33)                               # HE, HB, power
caps = [cyl_x(3.15, x_f - 9, x_f, y, z) for y, z in (uv(u, 13.0) for u in (14.5, 29.5, 44.5, 59.5))]
board = Part.makeCompound([pcb] + headers + [terms] + caps)
show("SkrPico", board, "BTT SKR Pico V1.0 (bought), dummy")
# keep-out for the checks: the parts over the PCB, the plugs at all four edges, the solder under it
keep = Part.makeCompound([
    box(x_f - PARTS_H, x_f, -B_L / 2, B_L / 2, PCB_Z0, PCB_Z1),
    box(x_f - hdr - 1, x_f, *sorted(uv(5.5, 0)[0:1] + uv(76.0, 0)[0:1]), PCB_Z1, PCB_Z1 + PLUG),
    box(x_f - hdr - 1, x_f, *sorted(uv(7.0, 0)[0:1] + uv(62.0, 0)[0:1]), PCB_Z0 - PLUG, PCB_Z0),
    box(x_f - hdr - 1, x_f, B_L / 2, B_L / 2 + PLUG, *sorted((uv(0, 5.0)[1], uv(0, 50.0)[1]))),
    box(x_f - 10, x_f, -B_L / 2 - PLUG, -B_L / 2, PCB_Z0, PCB_Z1),
    box(x_b, x_b + 2.5, -B_L / 2, B_L / 2, PCB_Z0, PCB_Z1),
])
show("SkrKeepOut", keep, "SKR Pico: room for its parts, plugs and solder joints (check only)", vis=False)

# ---------------------------------------------------------------- collar ---
ring = cyl(HR + COL_T, 0, 0, COL_Z0, COL_Z1)
ears = [box(-8, 8, HR + 2, HR + 15, COL_Z0, COL_Z1), box(-8, 8, -HR - 15, -HR - 2, COL_Z0, COL_Z1)]
pad = box(-PAD_X, -40, -PAD_W, PAD_W, COL_Z0, COL_Z1)
col = ring.fuse(ears + [pad])
cuts = [cyl(HR, 0, 0, COL_Z0 - 1, COL_Z1 + 1), box(-0.5, 0.5, -HR - 20, HR + 20, COL_Z0 - 1, COL_Z1 + 1)]
for sg in (1, -1):
    y = sg * (HR + 8.5)
    cuts += [cyl_x(1.7, -10, 10, y, SCR_Z),
             box(-9, -5.2, y - 2.85, y + 2.85, SCR_Z - 3.3, SCR_Z + 3.3)]          # nut, from the back
    y = sg * SCR_Y
    cuts += [cyl_x(1.7, -PAD_X - 1, -48, y, SCR_Z),
             box(-PAD_X + 4.4, -PAD_X + 7.0, y - 2.95, y + 2.95, SCR_Z - 3.3, COL_Z1 + 1)]   # nut, from above
col = col.cut(cuts[0].fuse(cuts[1:])).removeSplitter()
halves = sorted(col.Solids, key=lambda h: h.BoundBox.XMin)
if len(halves) != 2:
    sys.exit(f"collar: expected 2 solids, got {len(halves)}")
cr = show("SkrCollarRear", halves[0], "SKR collar, rear half with the plate pad (print)")
cf = show("SkrCollarFront", halves[1], "SKR collar, front half (print)")

# ----------------------------------------------------------------- plate ---
PY0, PY1 = uv(B_L, 0)[0] + 17.5, B_L / 2      # under the hole pairs, clear of the terminals' solder
plate = box(-PAD_X - PL_T, -PAD_X, PY0, PY1, PCB_Z0, PCB_Z1)
stand = [cyl_x(ST_R, -PCB_X, -PAD_X - PL_T + 0.01, *uv(u, v)) for u, v in HOLES]
plate = plate.fuse(stand)
pcuts = [cyl_x(1.1, -PCB_X - 1, -PAD_X + 1, *uv(u, v)) for u, v in HOLES]          # M2.5 self-tapping
pcuts += [cyl_x(1.7, -PAD_X - PL_T - 1, -PAD_X + 1, sg * SCR_Y, SCR_Z) for sg in (1, -1)]
# a window between the standoffs: air for the board's underside, less to print
pcuts.append(box(-PAD_X - PL_T - 1, -PAD_X + 1, uv(56.0, 0)[0], uv(9.0, 0)[0], PCB_Z0 + 9, SCR_Z - 6))
pcuts.append(box(-PAD_X - PL_T - 1, -PAD_X + 1, uv(56.0, 0)[0], uv(9.0, 0)[0], SCR_Z + 6, PCB_Z1 - 9))
plate = plate.cut(pcuts[0].fuse(pcuts[1:])).removeSplitter()
pl = show("SkrPlate", plate, "SKR board plate (print, 2x M3x12 into the pad, 4x M2.5x8 for the board)")

# ---------------------------------------------------------------- colours / save ---
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


export(halves[0], "skr_collar_rear")
export(halves[1], "skr_collar_front")
export(plate, "skr_plate", (V(0, 1, 0), 90))      # back face (x = -PAD_X) on the bed, standoffs up
for o in (cr, cf, pl):
    print(f"{o.Name} vol {o.Shape.Volume / 1000:.2f} cm3 valid {o.Shape.isValid()} solids {len(o.Shape.Solids)}")

# ---------------------------------------------------------------- checks ---
housing = bas.getObject("BaseHousing").Shape
heads = Part.makeCompound([cyl(4.3, bp.screw_r.Value * math.cos(math.radians(45 + 90 * k)),
                               bp.screw_r.Value * math.sin(math.radians(45 + 90 * k)), FL_T, FL_T + 5) for k in range(4)])
static = {"BaseHousing": housing, "TableScrewHeads": heads,
          "LimitCollarFront": lim.getObject("LimitCollarFront").Shape,
          "LimitCollarRear": lim.getObject("LimitCollarRear").Shape, "EndstopJ1": lim.getObject("EndstopJ1").Shape}
mine = {"SkrCollarRear": halves[0], "SkrCollarFront": halves[1], "SkrPlate": plate, "SkrPico": board, "SkrKeepOut": keep}
print("static fit:")
bad = 0
for a in mine:
    for b, s in list(static.items()) + [(k, v) for k, v in mine.items() if k > a]:
        if {a, b} in ({"SkrPico", "SkrKeepOut"}, {"SkrPlate", "SkrKeepOut"}):
            continue   # the board is its own keep-out; the standoffs go through the solder layer
        v = mine[a].common(s).Volume
        if v > 0.01:
            bad += 1
            print(f"  overlap {a} x {b}: {v:.1f} mm3")
if not bad:
    print("  none")
gap = {a: min(mine[a].distToShape(static[b])[0] for b in ("LimitCollarRear", "LimitCollarFront", "EndstopJ1"))
       for a in ("SkrPlate", "SkrKeepOut")}
print("gap to the J1 collar / board: " + ", ".join(f"{a} {d:.2f} mm" for a, d in gap.items()))
d_t = mine["SkrKeepOut"].distToShape(heads)[0]
print(f"gap from the plugs to the table screw heads: {d_t:.2f} mm")

# the turret a full turn
onturret = [tur.getObject("TurretBody").Shape, tur.getObject("J1HubScrews").Shape] + \
    [lim.getObject(n).Shape for n in ("LimitPlate", "LimitFlag", "EndstopJ2", "EndstopJ3")]
for n in ("J2_Motor", "J3_Motor"):
    body = pgd.getObject("Motor_NEMA17").Shape.fuse([pgd.getObject(k).Shape for k in ("Flange", "Gearbox")])
    body.Placement = tur.getObject(n).Placement.multiply(body.Placement)
    onturret.append(body)
onturret = Part.makeCompound(onturret)
near = (99.0, None)
hit = {}
for i in range(72):
    ang = -180 + 5 * i
    mv = onturret.copy()
    mv.rotate(V(0, 0, 0), V(0, 0, 1), ang)
    for a, s in mine.items():
        v = mv.common(s).Volume
        if v > 0.01 and v > hit.get(a, (0, 0))[0]:
            hit[a] = (v, ang)
    d = mv.distToShape(Part.makeCompound(list(mine.values())))[0]
    if d < near[0]:
        near = (d, ang)
print("J1 sweep (turret, its brackets, flag and motors a full turn over the board):")
for a, (v, ang) in hit.items():
    print(f"  {a}: {v:.1f} mm3 at J1={ang}")
if not hit:
    print(f"  none; nearest {near[0]:.2f} mm at J1={near[1]}")
