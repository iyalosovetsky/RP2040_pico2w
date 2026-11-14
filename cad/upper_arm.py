"""
upper_arm.py - parametric FreeCAD model of the upper arm (J2) and the J3 crank.

Builds cad/upper_arm.FCStd plus print files (already laid flat for printing):
  upper_arm_j2.stl     - J2-side plate: saddle with a D-seat for the J2 shaft, elbow 609Z seat,
                         two limit switch fingers. Print inner face down.
  upper_arm_j2_cap.stl - cap under that saddle: 2x M3x16 + nuts pull it up onto the shaft
  upper_arm_j3.stl     - J3-side plate, 6803 seat on the crank's journal + elbow 609Z seat
  upper_arm_tie.stl    - print 3: blocks across the gap between the plates; two ribs on each face
                         sit in two grooves in each plate, 2x M3x12 per plate into nuts in the tie
  j3_crank.stl         - crank: saddle with a D-seat for the J3 shaft, D17 journal for the J3-side
                         plate's 6803, 40 mm arm, one limit switch finger. Print outer face down.
  j3_crank_cap.stl     - its cap, with the other finger: 2x M3x16 + nuts from the arm's side
Limit switches (endstop_dims.py, limits.py): the J2-side plate and the crank carry two fingers each
that sweep past a switch board lying under the shoulder - one finger per end of travel.
Needs turret.FCStd (and through it base.FCStd, pg27.FCStd) in the same folder.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/upper_arm.py --pass cad/upper_arm.FCStd

Frames: turret frame as in turret.FCStd (shoulder axis along Y at z = shoulder_z).
Each part is modelled in its own link frame - X along the link, Y = joint axis -
and shown at the pose set by pose_j2 / pose_j3 (kinematic angles, as in the viewer:
J2 = upper arm above horizontal, J3 = forearm above horizontal, crank points opposite).

The PG27 shafts end 15.3 mm from the arm's middle, so a hub only has |y| 16..25.5 of shaft to hold.
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
sys.path.insert(0, here)
import endstop_dims as ES  # noqa: E402

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
    ("j2_hub_out", "25.5 mm", "J2 hub outer end |y| (cheek inner face at 26)"),
    ("shaft_d",    "7.98 mm", "PG27 shaft"),
    ("flat_depth", "0.98 mm", "D-flat depth: 7.0 mm across the flat on the 7.98 shaft (measured)"),
    ("d_clr",      "0.05 mm", "D-bore clearance; fit test: 0.15 had play"),
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
    ("sp_x0",      "25 mm",   "plate tie 1 centre along the link (clear of the J2 clamp jaw, r 18)"),
    ("sp_x1",      "55 mm",   "plate tie 2 centre"),
    ("sp_x2",      "90 mm",   "plate tie 3 centre (forearm folded to 30 deg still clears)"),
    ("web_len",    "16 mm",   "plate tie: length along the link"),
    ("web_hw",     "14 mm",   "plate tie: half-height across the link (plate half-width 18)"),
    ("web_key",    "1.5 mm",  "plate tie: rib height = groove depth in each plate"),
    ("web_fit",    "0.1 mm",  "plate tie: groove clearance per side"),
    ("web_rib_w",  "4 mm",    "plate tie: rib width - narrow, so the groove's roof bridges cleanly with the plate printed inner face down"),
    ("web_rib_x",  "5 mm",    "plate tie: the two ribs' centres either side of the tie's middle (the M3 holes are between them)"),
    ("web_scr_z",  "8 mm",    "plate tie: 2 M3 per plate at +-this across the link"),
    ("m3_clear",   "3.4 mm",  "M3 clearance"),
    ("m3_head_h",  "3.2 mm",  "M3 head counterbore depth (heads flush: the rods pass outside the plates)"),
    ("cl_head_h",  "3 mm",    "clamp: head pocket depth"),
    ("hub_hw",     "12.5 mm", "J2 hub block: half-width across the clamp screws"),
    ("hub_top",    "11 mm",   "hub saddle: height over the shaft axis (the lower levelling rod passes 12.2 above it)"),
    ("cap_gap",    "0.8 mm",  "gap between saddle and cap - the screws close it onto the shaft"),
    ("cap_t",      "9.2 mm",  "cap thickness (to 10 from the axis)"),
    ("cl_x",       "8.5 mm",  "J2 clamp screws: distance from the shaft axis"),
    ("cl_x3",      "11.3 mm", "crank clamp screws: distance from the axis (heads on the arm's side, clear of the 16 wide arm)"),
    ("cr_blk_hw",  "15.2 mm", "crank hub block: half-width across the clamp screws"),
    ("cl_nut_x",   "3.6 mm",  "clamp nut slot: plastic between it and the split"),
    ("cr_y0",      "25.5 mm", "crank hub outer end |y|"),
    ("cr_t",       "4.5 mm",  "crank arm thickness (|y| 21..25.5)"),
    ("cr_w",       "16 mm",   "crank arm width"),
    ("cr_boss_r",  "12 mm",   "crank root ring around the J3 shaft, |y| 20.5..25.5"),
    ("cl_bolt_d",  "3.4 mm",  "clamp screw M3"),
    ("cl_head_d",  "6.2 mm",  "M3 head counterbore"),
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


def d_seat(name, y0, y1, flat):
    """D-shaped seat along Y for the PG27 shaft, its flat facing +Z (flat="z") or +X ("x")."""
    b = cyl_y(name + "_R", f"{P}shaft_d / 2 + {P}d_clr", y0, y1)
    off = f"{P}shaft_d / 2 - {P}flat_depth + {P}d_clr"
    ly = f"({y1}) - ({y0}) + 2 mm"
    if flat == "z":
        f = box(name + "_F", f"{P}shaft_d", ly, f"{P}shaft_d", f"-{P}shaft_d / 2", f"({y0}) - 1 mm", off)
    else:
        f = box(name + "_F", f"{P}shaft_d", ly, f"{P}shaft_d", off, f"({y0}) - 1 mm", f"-{P}shaft_d / 2")
    return cut(name, b, f)


def finger(name, ang, r0, y0, y1, face_y):
    """Limit switch finger: a radial bar at ang (deg, in the part's frame) from r0 out to
    ES.FINGER_R, between y0 and y1; the face at face_y works the switch lever and has its
    two long edges chamfered so it rides onto the lever from either end."""
    w, c = ES.FINGER_W / 2, ES.FINGER_CH
    back, sg = (y1, 1) if face_y == y0 else (y0, -1)
    prof = [(-w, face_y + sg * c), (-w + c, face_y), (w - c, face_y), (w, face_y + sg * c), (w, back), (-w, back)]
    pts = [App.Vector(r0, y, t) for t, y in prof]
    s = Part.Face(Part.makePolygon(pts + pts[:1])).extrude(App.Vector(ES.FINGER_R - r0, 0, 0))
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -ang)
    o = doc.addObject("Part::Feature", name)
    o.Shape = s
    return o


def plate(name, y0, y1):
    """Link outline (stadium) in the X/Z plane between y0 and y1."""
    parts = [box(name + "_B", f"{P}len_l2", f"({y1}) - ({y0})", f"2 * {P}pl_r", "0 mm", y0, f"-{P}pl_r"),
             cyl_y(name + "_S", f"{P}pl_r", y0, y1),
             cyl_y(name + "_E", f"{P}pl_r", y0, y1, x=f"{P}len_l2")]
    return fuse(name, parts)


def tie_tools(name, x, face, side):
    """Two grooves for a plate tie's ribs in the plate's inner face (y = side * face), plus 2 M3
    clearance holes with head counterbores in the outer face (y = side * (face + pl_t))."""
    y0 = f"{face} - 0.01 mm" if side > 0 else f"-{face} - {P}web_key"
    t = [box(f"{name}_Groove{k}", f"{P}web_rib_w + 2 * {P}web_fit", f"{P}web_key + 0.01 mm", f"2 * ({P}web_hw + {P}web_fit)",
             f"{x} + {sx} * {P}web_rib_x - {P}web_rib_w / 2 - {P}web_fit", y0, f"-{P}web_hw - {P}web_fit")
         for k, sx in enumerate((1, -1))]
    out = f"{face} + {P}pl_t"
    for k, z in enumerate((f"{P}web_scr_z", f"-{P}web_scr_z")):
        if side > 0:
            t += [cyl_y(f"{name}_H{k}", f"{P}m3_clear / 2", f"{face} - 1 mm", f"{out} + 1 mm", x=x, z=z),
                  cyl_y(f"{name}_CB{k}", f"{P}cl_head_d / 2", f"{out} - {P}m3_head_h", f"{out} + 1 mm", x=x, z=z)]
        else:
            t += [cyl_y(f"{name}_H{k}", f"{P}m3_clear / 2", f"-({out}) - 1 mm", f"-{face} + 1 mm", x=x, z=z),
                  cyl_y(f"{name}_CB{k}", f"{P}cl_head_d / 2", f"-({out}) - 1 mm", f"-({out}) + {P}m3_head_h", x=x, z=z)]
    return t


# ------------------------------------------------------- upper arm, J2 side ---
pj2 = plate("PlateJ2", f"{P}pl_in", f"{P}pl_in + {P}pl_t")
elb2 = cyl_y("ElbowBossJ2", f"{P}elb_boss_r", f"{P}pl_in", f"{P}pl_in + {P}elb_t", x=f"{P}len_l2")
# J2 hub. The shaft stops 0.7 mm inside the plate, so all that can grip it lies between the plate and
# the turret cheek (|y| 16..25.5), and a split ring of that size is far too stiff to close. So the hub
# is two parts. A saddle on the plate has a D-shaped seat: the shaft's flat lies against the seat's
# flat roof, which takes the torque straight into the plate. A loose cap underneath is pulled up by
# 2x M3 and presses the flat home - no play, and nothing has to bend. The cap is under the hub (arm
# frame -Z) because the lower levelling rod passes 12.2 mm above the axis.
hy0, hy1 = f"{P}pl_in + {P}pl_t", f"{P}j2_hub_out"
hub2 = box("HubJ2", f"2 * {P}hub_hw", f"({hy1}) - ({hy0}) + 0.01 mm", f"{P}hub_top",
           f"-{P}hub_hw", f"({hy0}) - 0.01 mm", "0 mm")
# limit switch fingers on the shoulder end, in the inner 3 mm of the plate: thin enough to pass
# inside the head of the M4 pin that holds the lower levelling rod to the turret's ear
lim2 = [finger(f"LimFingerJ2_{k}", a, 15, ES.J2_FACE, ES.J2_FACE + ES.J2_FINGER_T, ES.J2_FACE)
        for k, a in enumerate(ES.J2_FINGERS)]
j2_solid = fuse("J2Solid", [pj2, hub2, elb2] + lim2)
# the seat runs 1.5 mm into the plate as a closed pocket for the shaft's tip
j2_tools = [d_seat("SeatJ2", f"({hy0}) - 1.5 mm", f"({hy1}) + 1 mm", "z")]
yc2 = f"(({hy0}) + ({hy1})) / 2 + 0.15 mm"
cap2_z = f"-({P}cap_gap + {P}cap_t)"
cap2_tools = [cyl_y("CapJ2_Seat", f"{P}shaft_d / 2 + {P}d_clr", f"({hy0}) - 1 mm", f"({hy1}) + 1 mm")]
for k, sx in enumerate((1, -1)):
    xc = f"{sx} * {P}cl_x"
    j2_tools += [   # nut slot open on the hub's end face, screw hole up from the split
        box(f"ClampNutJ2_{k}", f"{P}nut_w + 0.4 mm", f"({hy1}) - ({yc2}) + {P}nut_w / 2 + 1.2 mm", f"{P}nut_t",
            f"{xc} - {P}nut_w / 2 - 0.2 mm", f"{yc2} - {P}nut_w / 2 - 0.2 mm", f"{P}cl_nut_x"),
        box(f"ClampBoltJ2_{k}", f"{P}cl_bolt_d", f"{P}cl_bolt_d", f"{P}hub_top - 0.5 mm",
            f"{xc} - {P}cl_bolt_d / 2", f"{yc2} - {P}cl_bolt_d / 2", "-1 mm"),
    ]
    cap2_tools += [
        box(f"CapJ2_Bolt{k}", f"{P}cl_bolt_d", f"{P}cl_bolt_d", f"{P}cap_t + 2 mm",
            f"{xc} - {P}cl_bolt_d / 2", f"{yc2} - {P}cl_bolt_d / 2", f"{cap2_z} - 1 mm"),
        box(f"CapJ2_Head{k}", f"{P}cl_head_d", f"{P}cl_head_d", f"{P}cl_head_h + 1 mm",
            f"{xc} - {P}cl_head_d / 2", f"{yc2} - {P}cl_head_d / 2", f"{cap2_z} - 1 mm"),
    ]
cap_j2 = cut("UpperArmJ2Cap", box("CapJ2_B", f"2 * {P}hub_hw", f"({hy1}) - ({hy0}) - 0.3 mm", f"{P}cap_t",
                                  f"-{P}hub_hw", f"({hy0}) + 0.3 mm", cap2_z), cap2_tools)
cap_j2.Label = "J2 hub cap (print, 2x M3x16 + nuts)"
j2_tools += [cyl_y("Seat609J2", f"{P}b609_d / 2 + {P}b609_fit", f"{P}pl_in + {P}elb_t - {P}b609_w",
                   f"{P}pl_in + {P}elb_t + 1 mm", x=f"{P}len_l2"),
             cyl_y("LipJ2", f"{P}lip_hole_d / 2", f"{P}pl_in - 1 mm", f"{P}pl_in + {P}elb_t", x=f"{P}len_l2")]
TIES = (f"{P}sp_x0", f"{P}sp_x1", f"{P}sp_x2")
for k, x in enumerate(TIES):
    j2_tools += tie_tools(f"TieJ2_{k}", x, f"{P}pl_in", +1)
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
for k, x in enumerate(TIES):
    j3_tools += tie_tools(f"TieJ3_{k}", x, f"{P}pl_in", -1)
plate_j3 = cut("UpperArmJ3", j3_solid, j3_tools)
plate_j3.Label = "Upper arm, J3 side (print)"

# plate ties: a block across the gap with two ribs on each face sitting in two grooves in each plate
# (the form fit takes the racking, not the screws), 2 M3x12 from each plate into nuts in the tie.
# Ribs, not one wide tenon: the plates print inner face down, and a 4 mm groove bridges cleanly where
# a 13 mm pocket sags. They run the tie's whole height, so the tie prints standing with no overhang.
spacers = []
for k, x in enumerate(TIES):
    body = box(f"TieBody{k}", f"{P}web_len", f"2 * {P}pl_in", f"2 * {P}web_hw",
               f"{x} - {P}web_len / 2", f"-{P}pl_in", f"-{P}web_hw")
    keys = [box(f"TieKey{k}_{t}{j}", f"{P}web_rib_w", f"{P}web_key - 0.1 mm", f"2 * {P}web_hw",
                f"{x} + {sx} * {P}web_rib_x - {P}web_rib_w / 2", y0, f"-{P}web_hw")
            for t, y0 in (("P", f"{P}pl_in - 0.01 mm"), ("N", f"-{P}pl_in - {P}web_key + 0.11 mm"))
            for j, sx in enumerate((1, -1))]
    holes = []
    for j, (z, sz) in enumerate(((f"{P}web_scr_z", 1), (f"-{P}web_scr_z", -1))):
        holes.append(cyl_y(f"TieHole{k}_{j}", f"{P}m3_clear / 2", f"-{P}pl_in - {P}web_key - 1 mm",
                           f"{P}pl_in + {P}web_key + 1 mm", x=x, z=z))
        # nut slots 3 mm inside each face, open to the tie's top/bottom edge
        for t, yn in (("P", f"{P}pl_in - 3 mm - {P}nut_t"), ("N", f"-{P}pl_in + 3 mm")):
            holes.append(box(f"TieNut{k}_{j}{t}", f"{P}nut_w + 0.3 mm", f"{P}nut_t", f"{P}web_hw",
                             f"{x} - ({P}nut_w + 0.3 mm) / 2", yn,
                             z if sz > 0 else f"{z} - {P}web_hw"))
    s = cut(f"Spacer{k}", fuse(f"TieSolid{k}", [body] + keys), holes)
    s.Label = f"Plate tie {k + 1} (print, 4x M3x12 + nuts)"
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
for o in (plate_j2, cap_j2, plate_j3, *spacers, temp_bush, bearing6803):
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
# hub: the same two parts as on J2. The saddle is the half towards the arm (+X): its D-seat's flat
# takes the torque. The cap is the half behind the shaft; its screws come in from the arm's side, one
# above and one below the arm, into nuts in the cap. The collar's cap side is gone with it - the
# saddle's half of the collar still backs the 6803's inner ring.
y3a, y3b = f"-{P}cr_y0", f"-{P}pl_in - {P}pl_t"
cr_blk = box("CrankBlock", f"{P}hub_top", f"({y3b}) - ({y3a}) - 0.5 mm", f"2 * {P}cr_blk_hw", "0 mm", y3a, f"-{P}cr_blk_hw")
# limit switch fingers in the crank arm's plane (the drive rod runs inside it): the high-limit one
# on the saddle, the low-limit one on the cap
lim3 = [finger(f"LimFingerJ3_{k}", a, 10, ES.J3_FACE - ES.J3_FINGER_T, ES.J3_FACE, ES.J3_FACE)
        for k, a in enumerate(ES.J3_FINGERS)]
cr_solid = fuse("CrankSolid", [cr_hub, cr_collar, cr_arm, cr_tip, cr_ring, cr_blk, lim3[1]])
cr_tools = [d_seat("SeatJ3", f"({y3a}) - 1 mm", f"({y3b}) + 1.5 mm", "x"),
            cyl_y("CrankPin", f"{P}pin_d / 2", f"-{P}cr_y0 - 1 mm", f"-{P}cr_y0 + {P}cr_t + 1 mm", x=f"{P}R"),
            box("CrankCapRoom", "30 mm", f"({y3b}) - ({y3a}) + 1 mm", "60 mm", "-30 mm", f"({y3a}) - 1 mm", "-30 mm")]
yc3 = f"(({y3a}) + ({y3b}) - 0.5 mm) / 2"
cap3_x = f"-({P}cap_gap + {P}cap_t)"
cap3_tools = [cyl_y("CrankCap_Seat", f"{P}shaft_d / 2 + {P}d_clr", f"({y3a}) - 1 mm", f"({y3b}) + 1 mm")]
g = []
for k, sz in enumerate((1, -1)):
    zc = f"{sz} * {P}cl_x3"
    g += [
        box(f"ClampBoltCrank{k}", f"{P}hub_top + 2 mm", f"{P}cl_bolt_d", f"{P}cl_bolt_d",
            "-1 mm", f"{yc3} - {P}cl_bolt_d / 2", f"{zc} - {P}cl_bolt_d / 2"),
        box(f"ClampHeadCrank{k}", f"{P}cl_head_h + 1 mm", f"{P}cl_head_d", f"{P}cl_head_d",
            f"{P}hub_top - {P}cl_head_h", f"{yc3} - {P}cl_head_d / 2", f"{zc} - {P}cl_head_d / 2"),
    ]
    cap3_tools += [
        box(f"CrankCap_Bolt{k}", f"{P}cap_t + 2 mm", f"{P}cl_bolt_d", f"{P}cl_bolt_d",
            f"{cap3_x} - 1 mm", f"{yc3} - {P}cl_bolt_d / 2", f"{zc} - {P}cl_bolt_d / 2"),
        # nut slot open on the cap's outer end
        box(f"CrankCap_Nut{k}", f"{P}nut_t", f"({yc3}) - ({y3a}) + {P}nut_w / 2 + 1.2 mm", f"{P}nut_w + 0.4 mm",
            f"-({P}cap_gap + {P}cl_nut_x + {P}nut_t)", f"({y3a}) - 1 mm", f"{zc} - {P}nut_w / 2 - 0.2 mm"),
    ]
cap3_b = box("CrankCap_B", f"{P}cap_t", f"({y3b}) - ({y3a}) - 0.5 mm", f"2 * {P}cr_blk_hw", cap3_x, y3a, f"-{P}cr_blk_hw")
crank_cap = cut("J3CrankCap", fuse("CrankCapSolid", [cap3_b, lim3[0]]), cap3_tools)
crank_cap.Label = "J3 crank cap (print, 2x M3x16 + nuts)"
crank = cut("J3Crank", cr_solid, cr_tools + g)
crank.Label = "J3 crank (print)"
cp = doc.addObject("App::Part", "Crank")
cp.Label = "J3 crank (posed)"
cp.addObject(crank)
cp.addObject(crank_cap)
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
export(cap_j2, "upper_arm_j2_cap", 0)     # screw head side on the bed, seat up
export(plate_j3, "upper_arm_j3", -90)     # inner face (y = -pl_in) on the bed
export(spacers[0], "upper_arm_tie", 0)   # print 3; standing on its edge, ribs upright on the two sides
export(crank, "j3_crank", 90)             # hub/arm outer face (y = -cr_y0) on the bed
export(crank_cap, "j3_crank_cap", 90)     # the same end on the bed: finger flat, nut slots open downwards
export(temp_bush, "temp_bushing_6803", 90)

for o in (plate_j2, cap_j2, plate_j3, *spacers, crank, crank_cap, temp_bush):
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


arm_parts = {o.Name: o.Shape for o in (plate_j2, cap_j2, plate_j3, *spacers, temp_bush)}
crank_all = Part.makeCompound([crank.Shape, crank_cap.Shape])
worst = {}
for j2 in (35, 60, 90, 120, 150):
    for j3 in (-70, -48, -26, -4, 18, 35):
        rel = j3 - j2
        if not -150 <= rel <= -40:   # angle between the links = 180 + rel: 30..140 deg
            continue
        arm = {k: posed(v, j2) for k, v in arm_parts.items()}
        cr = posed(crank_all, j3 + 180)
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
