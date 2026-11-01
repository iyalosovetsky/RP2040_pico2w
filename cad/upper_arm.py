"""
upper_arm.py - parametric FreeCAD model of the upper arm (J2) and the J3 crank.

Builds cad/upper_arm.FCStd plus print files (already laid flat for printing):
  upper_arm_j2.stl   - J2-side plate with the D-hub on the J2 shaft + elbow 609Z seat
  upper_arm_j3.stl   - J3-side plate, bushing boss riding on the crank hub + elbow 609Z seat
  upper_arm_spacer.stl - print 2: tubes between the plates (M4x35 through-bolts)
  j3_crank.stl       - D-hub on the J3 shaft, D18 bushing for the J3-side plate, 35 mm arm
Needs turret.FCStd (and through it base.FCStd, pg27.FCStd) in the same folder.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/upper_arm.py --pass cad/upper_arm.FCStd

Frames: turret frame as in turret.FCStd (shoulder axis along Y at z = shoulder_z).
Each part is modelled in its own link frame - X along the link, Y = joint axis -
and shown at the pose set by pose_j2 / pose_j3 (kinematic angles, as in the viewer:
J2 = upper arm above horizontal, J3 = forearm above horizontal, crank points opposite).

Lateral stack (|y|): plates 9..16 (forearm |y| < 7.5); +y: J2 hub 16..25.5 inside the turret lug's gap;
-y: 6803 in the plate (16..11), crank collar 16..20.5, crank arm 21..25.5,
J3 drive rod 16.5..20.5 (outside the plate).
The crank-to-rod pin is an M4 in a printed bushing: a 609Z (7 mm wide) doesn't fit
between the cheek, crank, rod and plate.
"""

import os
import sys

import FreeCAD as App
import Part  # noqa: F401
import Import
import Mesh

out = os.path.abspath(next(a for a in sys.argv if a.endswith(".FCStd")))
here = os.path.dirname(out)
for f in ("pg27", "base", "turret"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
tur = App.getDocument("turret")
doc = App.newDocument("UpperArm")
doc.saveAs(out)

PARAMS = [
    ("shoulder_z", "155 mm",  "shoulder axis height (turret.FCStd shoulder_z)"),
    ("len_l2",     "140 mm",  "shoulder -> elbow"),
    ("R",          "40 mm",   "J3 crank length (= forearm tail); 40 keeps the tail pin clear of the plate at 140 deg"),
    ("pl_in",      "9 mm",    "plate inner face |y| (forearm is |y| < 7.5)"),
    ("pl_t",       "7 mm",    "plate thickness (= 609Z width, bearing sits flush)"),
    ("pl_r",       "18 mm",   "plate half-width / end radius"),
    ("j2_hub_r",   "11 mm",   "J2 D-hub radius (room for the M3 nut slot; turret lug gap is 12.5)"),
    ("j2_hub_out", "25.5 mm", "J2 hub outer end |y| (cheek inner face at 26)"),
    ("shaft_d",    "7.98 mm", "PG27 shaft"),
    ("flat_depth", "0.98 mm", "D-flat depth: 7.0 mm across the flat on the 7.98 shaft (measured)"),
    ("d_clr",      "0.05 mm", "D-bore clearance; fit test: 0.15 had play"),
    ("grub_d",     "3.2 mm",  "M3 grub hole"),
    ("nut_w",      "5.7 mm",  "M3 nut across flats (trap)"),
    ("nut_t",      "2.6 mm",  "M3 nut trap thickness"),
    ("b6803_d",    "26 mm",   "6803 OD - J3-side shoulder bearing (17x26x5)"),
    ("b6803_bore", "17 mm",   "6803 bore = crank journal diameter"),
    ("b6803_w",    "5 mm",    "6803 width"),
    ("b6803_fit",  "0 mm",    "6803 seat radial clearance (also the temporary bushing's OD)"),
    ("tmp_clr",    "0.25 mm", "temporary printed bushing: running clearance on the journal (radius)"),
    ("lip_d3",     "20 mm",   "hole through the lip behind the 6803 (journal 17 passes)"),
    ("collar_r",   "10.5 mm", "crank collar pressing the 6803 inner ring (outer ring starts at ~11.5)"),
    ("b609_d",     "22 mm",   "609Z OD"),
    ("b609_w",     "7 mm",    "609Z width"),
    ("b609_fit",   "0 mm",    "608/609 seat clearance (radius); press fit, 0.1 went in freely"),
    ("elb_boss_r", "15 mm",   "elbow boss radius"),
    ("elb_t",      "7 mm",    "plate thickness at the elbow: no boss, the levelling/drive rods pass right outside"),
    ("lip_hole_d", "13 mm",   "hole through the lip behind the 609Z"),
    ("sp_x1",      "55 mm",   "spacer 1 position along the link"),
    ("sp_x2",      "90 mm",   "spacer 2 position (forearm folded to 30 deg still clears)"),
    ("sp_r",       "6 mm",    "spacer tube radius"),
    ("m4_clear",   "4.4 mm",  "M4 clearance"),
    ("m4_head_d",  "7.5 mm",  "M4 head counterbore"),
    ("m4_head_h",  "3 mm",    "M4 head counterbore depth"),
    ("m4_nut_w",   "7.2 mm",  "M4 nut across flats"),
    ("m4_nut_t",   "3.4 mm",  "M4 nut trap depth"),
    ("cr_y0",      "25.5 mm", "crank hub outer end |y|"),
    ("cr_t",       "4.5 mm",  "crank arm thickness (|y| 21..25.5)"),
    ("cr_w",       "16 mm",   "crank arm width"),
    ("cr_boss_r",  "12 mm",   "crank root ring around the J3 shaft (clamp), |y| 20.5..25.5"),
    ("cl_slit",    "1 mm",    "clamp hub slit width"),
    ("cl_reach",   "19 mm",   "clamp lugs: outer edge from the shaft axis"),
    ("cl_lug_t",   "5.5 mm",  "clamp lugs: thickness each side of the slit"),
    ("cl_bolt_d",  "3.4 mm",  "clamp pinch bolt M3"),
    ("cl_head_d",  "6.2 mm",  "M3 head counterbore in the lug"),
    ("pin_d",      "4.2 mm",  "M4 pin hole (crank-rod, printed bushing)"),
    ("pose_j2",    "60 deg",  "display pose: upper arm above horizontal"),
    ("pose_j3",    "-30 deg", "display pose: forearm above horizontal"),
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
YROT = App.Rotation(App.Vector(1, 0, 0), -90)   # Part::Cylinder axis Z -> +Y


def expr(o, prop, e):
    o.setExpression(prop, e)


def place(o, x="0 mm", y="0 mm", z="0 mm"):
    expr(o, ".Placement.Base.x", x)
    expr(o, ".Placement.Base.y", y)
    expr(o, ".Placement.Base.z", z)


def cyl_y(name, r, y0, y1, x="0 mm", z="0 mm"):
    """Cylinder along Y from y0 to y1 (expressions, y1 > y0)."""
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", f"({y1}) - ({y0})")
    o.Placement.Rotation = YROT
    place(o, x, y0, z)
    return o


def box(name, lx, ly, lz, x, y, z):
    o = doc.addObject("Part::Box", name)
    for k, v in (("Length", lx), ("Width", ly), ("Height", lz)):
        expr(o, k, v)
    place(o, x, y, z)
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
    t = tools if not isinstance(tools, list) else fuse(name + "_Tools", tools)
    o = doc.addObject("Part::Cut", name)
    o.Base, o.Tool = b, t
    hide(b, t)
    return o


def d_bore(name, y0, y1, side=1):
    """D-shaped bore along Y for the PG27 shaft; the flat faces +X (side=1) or -X (side=-1)."""
    b = cyl_y(name + "_R", f"{P}shaft_d / 2 + {P}d_clr", y0, y1)
    x = (f"{P}shaft_d / 2 - {P}flat_depth + {P}d_clr" if side > 0
         else f"-{P}shaft_d * 3 / 2 + {P}flat_depth - {P}d_clr")
    f = box(name + "_F", f"{P}shaft_d", f"({y1}) - ({y0}) + 2 mm", f"{P}shaft_d",
            x, f"({y0}) - 1 mm", f"-{P}shaft_d / 2")
    return cut(name, b, f)


def grub(name, y, out_r, side, face_y):
    """Radial M3 grub along +X (side=1) or -X onto the shaft flat. The nut drops into a
    closed slot that opens only on the hub's end face at face_y (nothing cut through the
    hub wall), so the hub must be at least shaft r + 1.5 + nut_t + ~2.5 mm in radius."""
    if side > 0:
        hx, nx = "0 mm", f"{P}shaft_d / 2 + 1.5 mm"
    else:
        hx, nx = f"-({out_r} + 1 mm)", f"-{P}shaft_d / 2 - 1.5 mm - {P}nut_t"
    hole = box(name + "_H", f"{out_r} + 1 mm", f"{P}grub_d", f"{P}grub_d", hx, f"{y} - {P}grub_d / 2", f"-{P}grub_d / 2")
    # slot: nut_t along the screw, nut_w across it (Z), from below the screw axis to the end face
    lo, hi = (f"{y} - {P}nut_w / 2", f"{face_y} + 1 mm") if not face_y.startswith("-") else (f"{face_y} - 1 mm", f"{y} + {P}nut_w / 2")
    nut = box(name + "_N", f"{P}nut_t", f"({hi}) - ({lo})", f"{P}nut_w", nx, lo, f"-{P}nut_w / 2")
    return [hole, nut]


def plate(name, y0, y1):
    """Link outline (stadium) in the X/Z plane between y0 and y1."""
    parts = [box(name + "_B", f"{P}len_l2", f"({y1}) - ({y0})", f"2 * {P}pl_r", "0 mm", y0, f"-{P}pl_r"),
             cyl_y(name + "_S", f"{P}pl_r", y0, y1),
             cyl_y(name + "_E", f"{P}pl_r", y0, y1, x=f"{P}len_l2")]
    return fuse(name, parts)


def bolt_tools(name, x, lo, hi, head_side):
    """M4 through-bolt along Y at (x, z=0) through lo..hi: head counterbore in the +Y face
    (head_side > 0, J2 plate) or a nut trap in the -Y face (J3 plate)."""
    t = [cyl_y(name + "_H", f"{P}m4_clear / 2", f"{lo} - 1 mm", f"{hi} + 1 mm", x=x)]
    if head_side > 0:
        t.append(cyl_y(name + "_CB", f"{P}m4_head_d / 2", f"{hi} - {P}m4_head_h", f"{hi} + 1 mm", x=x))
    else:
        y_nut = lo
        nut = doc.addObject("Part::Prism", name + "_NT")
        nut.Polygon = 6
        expr(nut, "Circumradius", f"{P}m4_nut_w / sqrt(3)")
        expr(nut, "Height", f"{P}m4_nut_t + 1 mm")
        nut.Placement.Rotation = YROT
        place(nut, x, f"{y_nut} - 1 mm", "0 mm")
        t.append(nut)
    return t


# ------------------------------------------------------- upper arm, J2 side ---
pj2 = plate("PlateJ2", f"{P}pl_in", f"{P}pl_in + {P}pl_t")
hub2 = cyl_y("HubJ2", f"{P}j2_hub_r", f"{P}pl_in + {P}pl_t - 0.01 mm", f"{P}j2_hub_out")
elb2 = cyl_y("ElbowBossJ2", f"{P}elb_boss_r", f"{P}pl_in", f"{P}pl_in + {P}elb_t", x=f"{P}len_l2")
# clamp lugs under the hub (arm frame -Z): the lower levelling rod always passes above the axis
hy0, hy1 = f"{P}pl_in + {P}pl_t + 2 mm", f"{P}j2_hub_out"
lug2 = box("ClampLugJ2", f"{P}cl_slit + 2 * {P}cl_lug_t", f"({hy1}) - ({hy0})", f"{P}cl_reach - {P}j2_hub_r + 3 mm",
           f"-({P}cl_slit / 2 + {P}cl_lug_t)", hy0, f"-{P}cl_reach")
j2_solid = fuse("J2Solid", [pj2, hub2, elb2, lug2])
j2_tools = [d_bore("BoreJ2", f"{P}pl_in + 1 mm", f"{P}j2_hub_out + 1 mm")]
j2_tools += grub("GrubJ2", f"({P}pl_in + {P}pl_t + {P}j2_hub_out) / 2", f"{P}j2_hub_r", 1, f"{P}j2_hub_out")
yc2 = f"(({hy0}) + ({hy1})) / 2"
zb2 = f"-({P}cl_reach + {P}j2_hub_r) / 2 - 1.5 mm"
j2_tools += [
    box("ClampSlitJ2", f"{P}cl_slit", f"({hy1}) - ({hy0}) + 1 mm", f"{P}cl_reach + 1 mm - {P}shaft_d / 2",
        f"-{P}cl_slit / 2", hy0, f"-{P}cl_reach - 1 mm"),
    box("ClampBoltJ2", f"2 * ({P}cl_slit + 2 * {P}cl_lug_t)", f"{P}cl_bolt_d", f"{P}cl_bolt_d",
        f"-({P}cl_slit + 2 * {P}cl_lug_t)", f"{yc2} - {P}cl_bolt_d / 2", f"{zb2} - {P}cl_bolt_d / 2"),
    box("ClampHeadJ2", "3 mm", f"{P}cl_head_d", f"{P}cl_head_d", f"{P}cl_slit / 2 + {P}cl_lug_t - 2 mm",
        f"{yc2} - {P}cl_head_d / 2", f"{zb2} - {P}cl_head_d / 2"),
    box("ClampNutJ2", "3 mm", f"{P}nut_w + 0.4 mm", f"{P}nut_w + 0.4 mm", f"-({P}cl_slit / 2 + {P}cl_lug_t) - 1 mm",
        f"{yc2} - {P}nut_w / 2 - 0.2 mm", f"{zb2} - {P}nut_w / 2 - 0.2 mm"),
]
j2_tools += [cyl_y("Seat609J2", f"{P}b609_d / 2 + {P}b609_fit", f"{P}pl_in + {P}elb_t - {P}b609_w",
                   f"{P}pl_in + {P}elb_t + 1 mm", x=f"{P}len_l2"),
             cyl_y("LipJ2", f"{P}lip_hole_d / 2", f"{P}pl_in - 1 mm", f"{P}pl_in + {P}elb_t", x=f"{P}len_l2")]
for k, x in enumerate((f"{P}sp_x1", f"{P}sp_x2")):
    j2_tools += bolt_tools(f"BoltJ2_{k}", x, f"{P}pl_in", f"{P}pl_in + {P}pl_t", +1)
plate_j2 = cut("UpperArmJ2", j2_solid, j2_tools)
plate_j2.Label = "Upper arm, J2 side (print)"

# ------------------------------------------------------- upper arm, J3 side ---
pj3 = plate("PlateJ3", f"-{P}pl_in - {P}pl_t", f"-{P}pl_in")
elb3 = cyl_y("ElbowBossJ3", f"{P}elb_boss_r", f"-{P}pl_in - {P}elb_t", f"-{P}pl_in", x=f"{P}len_l2")
j3_solid = fuse("J3Solid", [pj3, elb3])
# shoulder: 6803 sits inside the plate (outer face flush), a lip on the inner side holds it;
# the crank's 17 mm journal runs through. Until the 6803 arrives, a printed bushing of the
# same size goes in the same seat (temp_bushing_6803.stl).
j3_tools = [cyl_y("Seat6803", f"{P}b6803_d / 2 + {P}b6803_fit", f"-{P}pl_in - {P}pl_t - 1 mm",
                  f"-{P}pl_in - {P}pl_t + {P}b6803_w"),
            cyl_y("Lip6803", f"{P}lip_d3 / 2", f"-{P}pl_in - {P}pl_t + {P}b6803_w - 0.01 mm", f"-{P}pl_in + 1 mm"),
            cyl_y("Seat609J3", f"{P}b609_d / 2 + {P}b609_fit", f"-{P}pl_in - {P}elb_t - 1 mm",
                  f"-{P}pl_in - {P}elb_t + {P}b609_w", x=f"{P}len_l2"),
            cyl_y("LipJ3", f"{P}lip_hole_d / 2", f"-{P}pl_in - {P}elb_t", f"-{P}pl_in + 1 mm", x=f"{P}len_l2")]
for k, x in enumerate((f"{P}sp_x1", f"{P}sp_x2")):
    j3_tools += bolt_tools(f"BoltJ3_{k}", x, f"-{P}pl_in - {P}pl_t", f"-{P}pl_in", -1)
plate_j3 = cut("UpperArmJ3", j3_solid, j3_tools)
plate_j3.Label = "Upper arm, J3 side (print)"

spacers = []
for k, x in enumerate((f"{P}sp_x1", f"{P}sp_x2")):
    tube = cyl_y(f"SpacerTube{k}", f"{P}sp_r", f"-{P}pl_in", f"{P}pl_in", x=x)
    hole = cyl_y(f"SpacerHole{k}", f"{P}m4_clear / 2", f"-{P}pl_in - 1 mm", f"{P}pl_in + 1 mm", x=x)
    s = cut(f"Spacer{k}", tube, hole)
    s.Label = f"Spacer {k + 1} (print, M4x35)"
    spacers.append(s)

tb_o = cyl_y("TmpBush_O", f"{P}b6803_d / 2", f"-{P}pl_in - {P}pl_t", f"-{P}pl_in - {P}pl_t + {P}b6803_w")
tb_i = cyl_y("TmpBush_I", f"{P}b6803_bore / 2 + {P}tmp_clr", f"-{P}pl_in - {P}pl_t - 1 mm", f"-{P}pl_in - {P}pl_t + {P}b6803_w + 1 mm")
temp_bush = cut("TempBushing6803", tb_o, tb_i)
temp_bush.Label = "Temporary bushing in place of the 6803 (print, PETG)"
b6_o = cyl_y("B6803_O", f"{P}b6803_d / 2", f"-{P}pl_in - {P}pl_t", f"-{P}pl_in - {P}pl_t + {P}b6803_w")
b6_i = cyl_y("B6803_I", f"{P}b6803_bore / 2", f"-{P}pl_in - {P}pl_t - 1 mm", f"-{P}pl_in - {P}pl_t + {P}b6803_w + 1 mm")
bearing6803 = cut("Bearing6803", b6_o, b6_i)
bearing6803.Label = "6803 (17x26x5), bought"
bearing6803.Visibility = False

ua = doc.addObject("App::Part", "UpperArm")
ua.Label = "Upper arm L2 (posed)"
for o in (plate_j2, plate_j3, *spacers, temp_bush, bearing6803):
    ua.addObject(o)
ua.Placement.Rotation.Axis = App.Vector(0, 1, 0)
expr(ua, ".Placement.Rotation.Angle", f"-{P}pose_j2")
expr(ua, ".Placement.Base.z", f"{P}shoulder_z")

# ------------------------------------------------------------- J3 crank ---
# journal for the 6803 inner ring, from the crank out to the plate's lip
cr_hub = cyl_y("CrankHub", f"{P}b6803_bore / 2", f"-{P}cr_y0", f"-{P}pl_in - {P}pl_t + {P}b6803_w")
cr_collar = cyl_y("CrankCollar", f"{P}collar_r", f"-{P}cr_y0", f"-{P}pl_in - {P}pl_t")
cr_arm = box("CrankArm", f"{P}R", f"{P}cr_t", f"{P}cr_w", "0 mm", f"-{P}cr_y0", f"-{P}cr_w / 2")
cr_tip = cyl_y("CrankTip", f"{P}cr_w / 2", f"-{P}cr_y0", f"-{P}cr_y0 + {P}cr_t", x=f"{P}R")
cr_ring = cyl_y("CrankRing", f"{P}cr_boss_r", f"-{P}cr_y0", f"-{P}cr_y0 + 5 mm")
lug3 = box("ClampLugCrank", f"{P}cl_reach - {P}cr_boss_r + 3 mm", f"{P}cr_t + 0.5 mm", f"{P}cl_slit + 2 * {P}cl_lug_t",
           f"-{P}cl_reach", f"-{P}cr_y0", f"-({P}cl_slit / 2 + {P}cl_lug_t)")
cr_solid = fuse("CrankSolid", [cr_hub, cr_collar, cr_arm, cr_tip, cr_ring, lug3])
cr_tools = [d_bore("BoreJ3", f"-{P}cr_y0 - 1 mm", f"-{P}pl_in - 2 mm", side=-1),
            cyl_y("CrankPin", f"{P}pin_d / 2", f"-{P}cr_y0 - 1 mm", f"-{P}cr_y0 + {P}cr_t + 1 mm", x=f"{P}R")]
# clamp: slit along -X through the root ring and the collar (not the 6803 journal), M3 across
xb3 = f"-({P}cl_reach + {P}cr_boss_r) / 2 - 1.5 mm"
yc3 = f"-{P}cr_y0 + ({P}cr_t + 0.5 mm) / 2"
g = [
    box("ClampSlitCrank", f"{P}cl_reach + 1 mm - {P}shaft_d / 2", f"{P}cr_y0 - {P}pl_in - {P}pl_t + 1 mm", f"{P}cl_slit",
        f"-{P}cl_reach - 1 mm", f"-{P}cr_y0 - 1 mm", f"-{P}cl_slit / 2"),
    box("ClampBoltCrank", f"{P}cl_bolt_d", f"{P}cl_bolt_d", f"2 * ({P}cl_slit + 2 * {P}cl_lug_t)",
        f"{xb3} - {P}cl_bolt_d / 2", f"{yc3} - {P}cl_bolt_d / 2", f"-({P}cl_slit + 2 * {P}cl_lug_t)"),
    box("ClampHeadCrank", f"{P}cl_head_d", f"{P}cl_head_d", "3 mm", f"{xb3} - {P}cl_head_d / 2",
        f"{yc3} - {P}cl_head_d / 2", f"{P}cl_slit / 2 + {P}cl_lug_t - 2 mm"),
    box("ClampNutCrank", f"{P}nut_w + 0.4 mm", f"{P}nut_w + 0.4 mm", "3 mm", f"{xb3} - {P}nut_w / 2 - 0.2 mm",
        f"{yc3} - {P}nut_w / 2 - 0.2 mm", f"-({P}cl_slit / 2 + {P}cl_lug_t) - 1 mm"),
]
crank = cut("J3Crank", cr_solid, cr_tools + g)
crank.Label = "J3 crank (print)"
cp = doc.addObject("App::Part", "Crank")
cp.Label = "J3 crank (posed)"
cp.addObject(crank)
cp.Placement.Rotation.Axis = App.Vector(0, 1, 0)
expr(cp, ".Placement.Rotation.Angle", f"-({P}pose_j3 + 180 deg)")
expr(cp, ".Placement.Base.z", f"{P}shoulder_z")

# ----------------------------------------------------------- context ---
ctx = doc.addObject("App::DocumentObjectGroup", "Turret_context")
for n in ("TurretBody", "J1Hub", "J1HubScrews", "J2_Motor", "J3_Motor", "Ctx_BaseHousing", "Ctx_Bearing_51211", "Ctx_J1_Motor"):
    lk = doc.addObject("App::Link", "Ctx_" + n.replace("Ctx_", ""))
    lk.LinkedObject = tur.getObject(n)
    lk.LinkTransform = True
    ctx.addObject(lk)

doc.recompute()
bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
if bad:
    sys.exit(f"recompute failed: {bad}")
doc.save()

# ----------------------------------------------------------- exports ---
def export(part, stem, rot):
    s = part.Shape.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), rot)
    s.translate(App.Vector(0, 0, -s.BoundBox.ZMin))
    Import.export([Part.show(s, stem)], os.path.join(here, stem + ".step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.05))
    m.write(os.path.join(here, stem + ".stl"))
    doc.removeObject(stem)


export(plate_j2, "upper_arm_j2", 90)      # inner face (y = +pl_in) on the bed
export(plate_j3, "upper_arm_j3", -90)     # inner face (y = -pl_in) on the bed
export(spacers[0], "upper_arm_spacer", -90)
export(crank, "j3_crank", 90)             # hub/arm outer face (y = -cr_y0) on the bed
export(temp_bush, "temp_bushing_6803", 90)

for o in (plate_j2, plate_j3, spacers[0], crank, temp_bush):
    s = o.Shape
    print(f"{o.Name:12s} vol {s.Volume / 1000:6.2f} cm3 valid {s.isValid()} solids {len(s.Solids)}")

# ------------------------------------------------- interference sweep ---
static = {o.LinkedObject.Name: o.Shape for o in ctx.Group}
# the J2/J3 shafts turn with the upper arm / crank, so leave the shaft + boss out of the static set
pgd = App.getDocument("pg27")
for n, lk in (("J2_Motor", "J2_Motor"), ("J3_Motor", "J3_Motor")):
    m = tur.getObject(lk)
    body = pgd.getObject("Motor_NEMA17").Shape.fuse([pgd.getObject(k).Shape for k in ("Flange", "Gearbox")])
    body.Placement = m.Placement.multiply(body.Placement)
    static[n] = body


def posed(shape, ang_deg):
    s = shape.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -ang_deg)
    s.translate(App.Vector(0, 0, ss.shoulder_z.Value))
    return s


arm_parts = {o.Name: o.Shape for o in (plate_j2, plate_j3, *spacers, temp_bush)}
worst = {}
for j2 in (35, 60, 90, 120, 150):
    for j3 in (-70, -48, -26, -4, 18, 35):
        rel = j3 - j2
        if not -150 <= rel <= -40:   # angle between the links = 180 + rel: 30..140 deg
            continue
        arm = {k: posed(v, j2) for k, v in arm_parts.items()}
        cr = posed(crank.Shape, j3 + 180)
        for an, a in list(arm.items()) + [("J3Crank", cr)]:
            for sn, s in static.items():
                v = a.common(s).Volume
                if v > 0.01:
                    worst[(an, sn)] = max(worst.get((an, sn), 0), v)
        for an, a in arm.items():
            v = a.common(cr).Volume
            if v > 0.01:
                worst[(an, "J3Crank")] = max(worst.get((an, "J3Crank"), 0), v)
print("interference sweep (J2 35..150, J3 -70..35, links 30..140 deg apart):")
print("  none" if not worst else "\n".join(f"  {a} x {b}: {v:.1f} mm3" for (a, b), v in worst.items()))
