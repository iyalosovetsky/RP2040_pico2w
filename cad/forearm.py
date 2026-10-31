"""
forearm.py - parametric FreeCAD model of the forearm, the three rods, the elbow
levelling plate and the wrist fork (scheme C parallelogram).

Builds cad/forearm.FCStd plus print files laid flat:
  forearm.stl       - L3 link with the J3 tail (pin to the drive rod), elbow hub
                      clamped on the elbow axle, wrist 609Z seat
  rod_drive.stl     - J3 crank -> forearm tail, length L2, plane |y| 16.5..20.5 (-y)
  rod_lev_low.stl   - turret lug -> elbow plate, length L2, plane 17..21 (+y)
  rod_lev_up.stl    - elbow plate -> wrist fork, length L3, plane 26..30 (+y)
  elbow_plate.stl   - triangle on the elbow axle (plain bushing), keeps its orientation
  wrist_fork.stl    - fork on the wrist axle, keeps its orientation; its bottom bridge
                      (4x M3 inserts) takes the Z or Y tool bracket
Bought: elbow axle D8 x 45 and wrist axle D8 x 34 - cut from an 8 mm linear rod, or M8 bolts
with a plain shank (DIN 931: M8x55 elbow, M8x40 wrist, nyloc nuts).
Bearings: 609Z (9 mm bore) with an 8->9 sleeve on the axle (brass tube 9x0.5, or the printed
axle_sleeve_8x9.stl as a stop-gap), or 608ZZ (8x22x7) straight on the axle - the seats are
the same 22x7 for both. 2 in the upper arm plates, 1 in the forearm tip. M4 pins with printed
bushings for the rods.
Needs upper_arm.FCStd (and the files it uses) in the same folder.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/forearm.py --pass cad/forearm.FCStd

Joint limits this geometry is checked for (sweep at the end):
J2 35..150 deg, J3 -70..35 deg, angle between the links 30..140 deg.
"""

import math
import os
import sys

import FreeCAD as App
import Part  # noqa: F401
import Import
import Mesh

out = os.path.abspath(next(a for a in sys.argv if a.endswith(".FCStd")))
here = os.path.dirname(out)
for f in ("pg27", "base", "turret", "upper_arm"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
tur, uad = App.getDocument("turret"), App.getDocument("upper_arm")
doc = App.newDocument("Forearm")
doc.saveAs(out)

PARAMS = [
    ("shoulder_z", "155 mm",  "shoulder axis height (turret.FCStd)"),
    ("len_l2",     "140 mm",  "upper arm (upper_arm.FCStd)"),
    ("len_l3",     "140 mm",  "elbow -> wrist"),
    ("R",          "40 mm",   "forearm tail = J3 crank (upper_arm.FCStd R)"),
    ("lev_v",      "30 mm",   "levelling offset back (turret lug at x = -lev_v)"),
    ("lev_w",      "30 mm",   "levelling offset up (elbow plate / wrist fork pin)"),
    ("fa_t",       "15 mm",   "forearm thickness (|y| < 7.5, plates start at 9)"),
    ("fa_hw",      "12 mm",   "forearm half-width along the link"),
    ("fa_end_r",   "14 mm",   "forearm end radius at elbow and wrist"),
    ("fa_tail_r",  "9 mm",    "forearm tail end radius"),
    ("tail_boss_r", "6 mm",   "tail pin boss radius (reaches the drive rod plane)"),
    ("drv_y0",     "16.5 mm", "drive rod inner face |y| (-y side)"),
    ("low_y0",     "17 mm",   "lower levelling rod inner face |y| (+y side)"),
    ("up_y0",      "26 mm",   "upper levelling rod inner face |y| (+y side)"),
    ("rod_t",      "4 mm",    "rod thickness"),
    ("rod_w",      "10 mm",   "rod width"),
    ("pin_d",      "4.2 mm",  "M4 pin hole"),
    ("pl_y0",      "21.5 mm", "elbow plate inner face |y| (+y)"),
    ("pl_t",       "4 mm",    "elbow plate thickness"),
    ("pl_hub_r",   "10 mm",   "elbow plate hub radius"),
    ("pl_arm_r",   "6 mm",    "elbow plate pin ends radius"),
    ("axle_d",     "8 mm",    "elbow / wrist axle: 8 mm linear rod or M8 bolt shank (DIN 931)"),
    ("b_bore",     "9 mm",    "bearing bore: 9 = 609Z (needs the 8->9 sleeve), 8 = 608ZZ (no sleeve)"),
    ("axle_clr",   "0.1 mm",  "axle bore clearance where it is clamped"),
    ("bush_clr",   "0.2 mm",  "axle bore clearance where it turns (elbow plate)"),
    ("b609_d",     "22 mm",   "609Z OD"),
    ("b609_w",     "7 mm",    "609Z width"),
    ("b609_fit",   "0 mm",    "608/609 seat radial clearance; press fit, 0.1 went in freely"),
    ("lip_hole_d", "13 mm",   "hole through the lip behind the wrist 609Z"),
    ("fk_in",      "8.5 mm",  "wrist fork cheek inner face |y|"),
    ("fk_t",       "5 mm",    "wrist fork cheek thickness"),
    ("fk_r",       "12 mm",   "wrist fork cheek radius around the axle"),
    ("fk_len",     "44 mm",   "wrist fork reach forward of the axle"),
    ("fk_drop",    "24 mm",   "wrist fork bridge bottom below the axle"),
    ("fk_bridge_t", "6 mm",   "wrist fork bridge thickness"),
    ("fk_post_r",  "6 mm",    "wrist fork post radius (upper rod pin)"),
    ("ins_d",      "4.2 mm",  "M3 heat insert hole (tool bracket)"),
    ("grub_d",     "3.2 mm",  "M3 grub"),
    ("nut_w",      "5.7 mm",  "M3 nut across flats"),
    ("nut_t",      "2.6 mm",  "M3 nut trap"),
    ("pose_j2",    "60 deg",  "display pose"),
    ("pose_j3",    "-30 deg", "display pose"),
]
ss = doc.addObject("Spreadsheet::Sheet", "Params")
for c, t in (("A1", "parameter"), ("B1", "value"), ("C1", "note")):
    ss.set(c, t)
for i, (alias, value, note) in enumerate(PARAMS, start=2):
    ss.set(f"A{i}", alias)
    ss.set(f"B{i}", value if not value.startswith("-") else "=" + value)
    ss.setAlias(f"B{i}", alias)
    ss.set(f"C{i}", note)
doc.recompute()
P = "Params."
YROT = App.Rotation(App.Vector(1, 0, 0), -90)


def expr(o, prop, e):
    o.setExpression(prop, e)


def place(o, x="0 mm", y="0 mm", z="0 mm"):
    expr(o, ".Placement.Base.x", x)
    expr(o, ".Placement.Base.y", y)
    expr(o, ".Placement.Base.z", z)


def cyl_y(name, r, y0, y1, x="0 mm", z="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", f"({y1}) - ({y0})")
    o.Placement.Rotation = YROT
    place(o, x, y0, z)
    return o


def cyl_z(name, r, z0, z1, x="0 mm", y="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", f"({z1}) - ({z0})")
    place(o, x, y, z0)
    return o


def box(name, x0, x1, y0, y1, z0, z1):
    o = doc.addObject("Part::Box", name)
    expr(o, "Length", f"({x1}) - ({x0})")
    expr(o, "Width", f"({y1}) - ({y0})")
    expr(o, "Height", f"({z1}) - ({z0})")
    place(o, x0, y0, z0)
    return o


def hide(*objs):
    for o in objs:
        o.Visibility = False


def fuse(name, objs):
    o = doc.addObject("Part::MultiFuse", name)
    o.Shapes = objs
    hide(*objs)
    return o


def cut(name, b, tools):
    t = fuse(name + "_Tools", tools) if isinstance(tools, list) else tools
    o = doc.addObject("Part::Cut", name)
    o.Base, o.Tool = b, t
    hide(b, t)
    return o


def grub_up(name, x, y, z0, z1, face_y):
    """M3 grub along +Z at (x, y) from the bore (z0) out through the hub (z1). The nut drops
    into a closed slot that opens only on the end face at face_y - nothing cut through the wall."""
    hole = box(name + "_H", f"{x} - {P}grub_d / 2", f"{x} + {P}grub_d / 2",
               f"{y} - {P}grub_d / 2", f"{y} + {P}grub_d / 2", z0, z1)
    zn = f"({z0}) + 2 mm"
    lo, hi = (f"{y} - {P}nut_w / 2", f"{face_y} + 1 mm") if not face_y.startswith("-") else (f"{face_y} - 1 mm", f"{y} + {P}nut_w / 2")
    nut = box(name + "_N", f"{x} - {P}nut_w / 2", f"{x} + {P}nut_w / 2", lo, hi, zn, f"{zn} + {P}nut_t")
    return [hole, nut]


def rod(name, length, y0):
    """Flat bar along +X from pin to pin, between y0 and y0 + rod_t."""
    y1 = f"{y0} + {P}rod_t"
    body = fuse(name + "_S", [box(name + "_B", "0 mm", length, y0, y1, f"-{P}rod_w / 2", f"{P}rod_w / 2"),
                              cyl_y(name + "_E0", f"{P}rod_w / 2", y0, y1),
                              cyl_y(name + "_E1", f"{P}rod_w / 2", y0, y1, x=length)])
    holes = [cyl_y(name + "_H0", f"{P}pin_d / 2", f"{y0} - 1 mm", f"{y1} + 1 mm"),
             cyl_y(name + "_H1", f"{P}pin_d / 2", f"{y0} - 1 mm", f"{y1} + 1 mm", x=length)]
    return cut(name, body, holes)


# ---------------------------------------------------------------- forearm ---
yt = f"{P}fa_t / 2"
fa_parts = [
    box("FA_Body", f"-{P}R", f"{P}len_l3", f"-{yt}", yt, f"-{P}fa_hw", f"{P}fa_hw"),
    cyl_y("FA_Elbow", f"{P}fa_end_r", f"-{yt}", yt),
    cyl_y("FA_Wrist", f"{P}fa_end_r", f"-{yt}", yt, x=f"{P}len_l3"),
    cyl_y("FA_Tail", f"{P}fa_tail_r", f"-{yt}", yt, x=f"-{P}R"),
    cyl_y("FA_TailBoss", f"{P}tail_boss_r", f"-{P}drv_y0 + 0.2 mm", f"-{yt} + 0.01 mm", x=f"-{P}R"),
]
fa_tools = [
    cyl_y("FA_ElbowBore", f"{P}axle_d / 2 + {P}axle_clr", f"-{yt} - 1 mm", f"{yt} + 1 mm"),
    cyl_y("FA_Seat609", f"{P}b609_d / 2 + {P}b609_fit", f"{yt} - {P}b609_w", f"{yt} + 1 mm", x=f"{P}len_l3"),
    cyl_y("FA_Lip", f"{P}lip_hole_d / 2", f"-{yt} - 1 mm", f"{yt} - {P}b609_w + 0.1 mm", x=f"{P}len_l3"),
    cyl_y("FA_TailPin", f"{P}pin_d / 2", f"-{P}drv_y0 - 1 mm", f"{yt} + 1 mm", x=f"-{P}R"),
] + grub_up("FA_Grub", "0 mm", "0 mm", f"{P}axle_d / 2 - 0.5 mm", f"{P}fa_end_r + 1 mm", f"{yt}")
forearm = cut("Forearm", fuse("FA_Solid", fa_parts), fa_tools)
forearm.Label = "Forearm L3 (print)"

# ------------------------------------------------------------------- rods ---
rod_drive = rod("RodDrive", f"{P}len_l2", f"-{P}drv_y0 - {P}rod_t")
rod_low = rod("RodLevLow", f"{P}len_l2", f"{P}low_y0")
rod_up = rod("RodLevUp", f"{P}len_l3", f"{P}up_y0")
rod_drive.Label, rod_low.Label, rod_up.Label = ("Drive rod J3 (print)", "Lower levelling rod (print)",
                                                "Upper levelling rod (print)")

# ------------------------------------------------------------ elbow plate ---
py0, py1 = f"{P}pl_y0", f"{P}pl_y0 + {P}pl_t"
ep = fuse("EP_Solid", [
    cyl_y("EP_Hub", f"{P}pl_hub_r", py0, py1),
    cyl_y("EP_V", f"{P}pl_arm_r", py0, py1, x=f"-{P}lev_v"),
    cyl_y("EP_W", f"{P}pl_arm_r", py0, py1, z=f"{P}lev_w"),
    box("EP_BarV", f"-{P}lev_v", "0 mm", py0, py1, f"-{P}pl_arm_r", f"{P}pl_arm_r"),
    box("EP_BarW", f"-{P}pl_arm_r", f"{P}pl_arm_r", py0, py1, "0 mm", f"{P}lev_w"),
])
elbow_plate = cut("ElbowPlate", ep, [
    cyl_y("EP_Bore", f"{P}axle_d / 2 + {P}bush_clr", f"{py0} - 1 mm", f"{py1} + 1 mm"),
    cyl_y("EP_PinV", f"{P}pin_d / 2", f"{py0} - 1 mm", f"{py1} + 1 mm", x=f"-{P}lev_v"),
    cyl_y("EP_PinW", f"{P}pin_d / 2", f"{py0} - 1 mm", f"{py1} + 1 mm", z=f"{P}lev_w"),
])
elbow_plate.Label = "Elbow levelling plate (print)"

# ------------------------------------------------------------- wrist fork ---
fk_parts = []
for tag, (a, b) in (("P", (f"{P}fk_in", f"{P}fk_in + {P}fk_t")), ("N", (f"-{P}fk_in - {P}fk_t", f"-{P}fk_in"))):
    fk_parts += [cyl_y(f"FK_Disk{tag}", f"{P}fk_r", a, b),
                 box(f"FK_Cheek{tag}", "0 mm", f"{P}fk_len", a, b, f"-{P}fk_drop", "0 mm")]
fk_parts += [
    box("FK_Bridge", "0 mm", f"{P}fk_len", f"-{P}fk_in - {P}fk_t", f"{P}fk_in + {P}fk_t",
        f"-{P}fk_drop", f"-{P}fk_drop + {P}fk_bridge_t"),
    box("FK_PostWeb", f"-{P}fk_post_r", f"{P}fk_post_r", f"{P}fk_in", f"{P}fk_in + {P}fk_t", "0 mm", f"{P}lev_w"),
    cyl_y("FK_Post", f"{P}fk_post_r", f"{P}fk_in", f"{P}up_y0 - 0.5 mm", z=f"{P}lev_w"),
    cyl_y("FK_ClampBoss", "11 mm", f"-{P}fk_in - {P}fk_t - 6 mm", f"-{P}fk_in - {P}fk_t + 0.01 mm"),
]
fk_tools = [
    cyl_y("FK_Bore", f"{P}axle_d / 2 + {P}axle_clr", f"-{P}fk_in - {P}fk_t - 7 mm", f"{P}fk_in + {P}fk_t + 1 mm"),
    cyl_y("FK_PostPin", f"{P}pin_d / 2", f"{P}fk_in - 1 mm", f"{P}up_y0 + 1 mm", z=f"{P}lev_w"),
] + grub_up("FK_Grub", "0 mm", f"-{P}fk_in - {P}fk_t - 3 mm", f"{P}axle_d / 2 - 0.5 mm", "12 mm",
            f"-{P}fk_in - {P}fk_t - 6 mm")
for k, (x, y) in enumerate(((10, 7), (10, -7), (34, 7), (34, -7))):
    fk_tools.append(cyl_z(f"FK_Insert{k}", f"{P}ins_d / 2", f"-{P}fk_drop - 1 mm", f"-{P}fk_drop + {P}fk_bridge_t + 1 mm",
                          f"{x} mm", f"{y} mm"))
wrist_fork = cut("WristFork", fuse("FK_Solid", fk_parts), fk_tools)
wrist_fork.Label = "Wrist fork (print), tool brackets bolt under it"

# ------------------------------------------------------------- axles ---
elbow_axle = cyl_y("ElbowAxle", f"{P}axle_d / 2", "-18 mm", "27 mm")
wrist_axle = cyl_y("WristAxle", f"{P}axle_d / 2", "-20 mm", "14 mm")
elbow_axle.Label, wrist_axle.Label = ("Elbow axle D8x45: 8 mm linear rod or M8x55 bolt shank",
                                      "Wrist axle D8x34: 8 mm linear rod or M8x40 bolt shank")
sl_o = cyl_y("Sleeve_O", f"{P}b_bore / 2 - 0.02 mm", "0 mm", f"{P}b609_w")
sl_i = cyl_y("Sleeve_I", f"{P}axle_d / 2 + 0.05 mm", "-1 mm", f"{P}b609_w + 1 mm")
sleeve = cut("AxleSleeve", sl_o, sl_i)
sleeve.Label = "Axle sleeve 8->9 for a 609Z (print in PETG as a stop-gap; brass tube 9x0.5 is better)"
sleeve.Visibility = False


def b609(name, x, y0):
    """609Z (9x22x7), bought: shown so it's clear what the axles turn in."""
    o = cyl_y(name + "_O", f"{P}b609_d / 2", y0, f"{y0} + {P}b609_w", x=x)
    i = cyl_y(name + "_I", f"{P}b_bore / 2", f"{y0} - 1 mm", f"{y0} + {P}b609_w + 1 mm", x=x)
    return cut(name, o, i)


# wrist: in the forearm tip's seat (forearm frame); elbow: in the two upper arm plates
# (|y| 9..16, they turn with the upper arm - drawn in the forearm frame, it's a ring either way)
b609_wrist = b609("B609_Wrist", f"{P}len_l3", f"{yt} - {P}b609_w")
b609_e1 = b609("B609_ElbowJ2", "0 mm", "9 mm")
b609_e2 = b609("B609_ElbowJ3", "0 mm", "-16 mm")
b609_wrist.Label = "609Z wrist bearing (bought): the wrist axle turns in it"
b609_e1.Label = b609_e2.Label = "609Z elbow bearing in the upper arm plate (bought)"

doc.recompute()
bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
if bad:
    sys.exit(f"recompute failed: {bad}")

# ------------------------------------------------------ posed assembly ---
L2, L3, R = ss.len_l2.Value, ss.len_l3.Value, ss.R.Value
V, W_ = ss.lev_v.Value, ss.lev_w.Value
ZS = ss.shoulder_z.Value


def kin(j2, j3):
    a2, a3 = math.radians(j2), math.radians(j3)
    u2 = App.Vector(math.cos(a2), 0, math.sin(a2))
    f = App.Vector(math.cos(a3), 0, math.sin(a3))
    O = App.Vector(0, 0, ZS)
    E = O + u2 * L2
    Wp = E + f * L3
    return dict(O=O, E=E, W=Wp, u2=u2, f=f)


def posed(shape, ang_deg, at):
    s = shape.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -ang_deg)
    s.translate(at)
    return s


def moving(j2, j3):
    k = kin(j2, j3)
    vv, ww = App.Vector(-V, 0, 0), App.Vector(0, 0, W_)
    return {
        "Forearm": posed(forearm.Shape, j3, k["E"]),
        "ElbowPlate": posed(elbow_plate.Shape, 0, k["E"]),
        "WristFork": posed(wrist_fork.Shape, 0, k["W"]),
        "RodDrive": posed(rod_drive.Shape, j2, k["O"] - k["f"] * R),
        "RodLevLow": posed(rod_low.Shape, j2, k["O"] + vv),
        "RodLevUp": posed(rod_up.Shape, j3, k["E"] + ww),
        "ElbowAxle": posed(elbow_axle.Shape, 0, k["E"]),
        "B609_Wrist": posed(b609_wrist.Shape, j3, k["E"]),
        "B609_Elbow": posed(b609_e1.Shape.fuse(b609_e2.Shape), j2, k["E"]),
        "WristAxle": posed(wrist_axle.Shape, 0, k["W"]),
        "UpperArmJ2": posed(uad.getObject("UpperArmJ2").Shape, j2, k["O"]),
        "UpperArmJ3": posed(uad.getObject("UpperArmJ3").Shape, j2, k["O"]),
        "Spacer0": posed(uad.getObject("Spacer0").Shape, j2, k["O"]),
        "Spacer1": posed(uad.getObject("Spacer1").Shape, j2, k["O"]),
        "J3Crank": posed(uad.getObject("J3Crank").Shape, j3 + 180, k["O"]),
    }


asm = doc.addObject("App::DocumentObjectGroup", "Assembly_pose")
for n, s in moving(ss.pose_j2.Value, ss.pose_j3.Value).items():
    if n in ("Forearm", "ElbowPlate", "WristFork", "RodDrive", "RodLevLow", "RodLevUp", "ElbowAxle", "WristAxle",
             "B609_Wrist", "B609_Elbow"):
        o = doc.addObject("Part::Feature", "Posed_" + n)
        o.Shape = s
        asm.addObject(o)
for n in (forearm, rod_drive, rod_low, rod_up, elbow_plate, wrist_fork, elbow_axle, wrist_axle,
          b609_wrist, b609_e1, b609_e2):
    n.Visibility = False
ctx = doc.addObject("App::DocumentObjectGroup", "Context")
for n in ("TurretBody", "J2_Motor", "J3_Motor", "Ctx_BaseHousing"):
    lk = doc.addObject("App::Link", "Ctx_" + n.replace("Ctx_", ""))
    lk.LinkedObject = tur.getObject(n)
    lk.LinkTransform = True
    ctx.addObject(lk)
doc.recompute()
doc.save()

# ----------------------------------------------------------- exports ---
def export(obj, stem, rot):
    s = obj.Shape.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), rot)
    s.translate(App.Vector(0, 0, -s.BoundBox.ZMin))
    tmp = Part.show(s, "tmp_export")
    Import.export([tmp], os.path.join(here, stem + ".step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.05))
    m.write(os.path.join(here, stem + ".stl"))
    doc.removeObject(tmp.Name)


export(forearm, "forearm", -90)         # +y face on the bed; the tail boss on -y points up
export(rod_drive, "rod_drive", 90)
export(rod_low, "rod_lev_low", 90)
export(rod_up, "rod_lev_up", 90)
export(elbow_plate, "elbow_plate", 90)
export(sleeve, "axle_sleeve_8x9", 90)   # print 3 (only with 609Z)
export(wrist_fork, "wrist_fork", 0)     # bridge on the bed, cheeks up (support under the clamp boss)

for o in (forearm, rod_drive, rod_low, rod_up, elbow_plate, wrist_fork):
    s = o.Shape
    print(f"{o.Name:11s} vol {s.Volume / 1000:6.2f} cm3 valid {s.isValid()} solids {len(s.Solids)}")

# ------------------------------------------------- interference sweep ---
pgd = App.getDocument("pg27")
static = {"TurretBody": tur.getObject("TurretBody").Shape,
          "BaseHousing": tur.getObject("Ctx_BaseHousing").Shape}
for n in ("J2_Motor", "J3_Motor"):
    body = pgd.getObject("Motor_NEMA17").Shape.fuse([pgd.getObject(k).Shape for k in ("Flange", "Gearbox")])
    body.Placement = tur.getObject(n).Placement.multiply(body.Placement)
    static[n] = body
new = ("Forearm", "ElbowPlate", "WristFork", "RodDrive", "RodLevLow", "RodLevUp", "ElbowAxle", "WristAxle",
       "B609_Wrist", "B609_Elbow")
# parts that are meant to touch: axles in their bores
ok_pairs = {("ElbowAxle", "Forearm"), ("ElbowAxle", "ElbowPlate"), ("ElbowAxle", "UpperArmJ2"),
            ("ElbowAxle", "UpperArmJ3"), ("WristAxle", "Forearm"), ("WristAxle", "WristFork"),
            ("B609_Wrist", "Forearm"), ("B609_Wrist", "WristAxle"), ("B609_Elbow", "ElbowAxle"),
            ("B609_Elbow", "UpperArmJ2"), ("B609_Elbow", "UpperArmJ3")}
worst = {}
poses = 0
for j2 in (35, 50, 70, 90, 110, 130, 150):
    for j3 in (-70, -50, -30, -10, 10, 35):
        if not -150 <= j3 - j2 <= -40:   # angle between the links = 180 + (J3 - J2): 30..140 deg
            continue
        poses += 1
        mv = moving(j2, j3)
        names = list(mv)
        for a in new:
            for sn, s in static.items():
                v = mv[a].common(s).Volume
                if v > 0.01:
                    worst[(a, sn)] = max(worst.get((a, sn), (0, ""))[0], v), f"J2={j2} J3={j3}"
            for b in names:
                if b == a or (b in new and names.index(b) < names.index(a)):
                    continue
                if (a, b) in ok_pairs or (b, a) in ok_pairs:
                    continue
                v = mv[a].common(mv[b]).Volume
                if v > 0.01:
                    key = (a, b)
                    if v > worst.get(key, (0, ""))[0]:
                        worst[key] = (v, f"J2={j2} J3={j3}")
print(f"interference sweep over {poses} poses (J2 35..150, J3 -70..35, links 30..140 deg):")
if not worst:
    print("  none")
for (a, b), (v, at) in sorted(worst.items(), key=lambda kv: -kv[1][0]):
    print(f"  {a} x {b}: {v:.1f} mm3 at {at}")
