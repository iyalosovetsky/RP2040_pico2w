"""
tools.py - parametric FreeCAD model of the J4 tool brackets, the tool flanges and the
tool clamps (interchangeable end-of-arm tools).

Two brackets bolt under the wrist fork's bridge (4x M3 into its heat inserts):
  bracket_z - plate under the fork, J4 vertical (body up, shaft down): J4 turns the tool
              about the vertical; the tool hangs coaxially under the J4 shaft.
  bracket_y - plate under the fork + side plate, J4 across the arm like J3 on the turret
              (body outward on +y): J4 tilts the tool in the arm's plane. The J4 axis sits
              low and forward so a tool clamped at its centre of mass can swing.
Tool interface (same on both flanges): 50x50 plate, 4x M3 on a 40x40 square, screws go
in from the flange side (reachable in the gap under/next to the bracket), heat inserts
are in the tool's plate. The screws sit outside the tool body so they stay reachable.
  flange_z / flange_y - D-hub on the J4 shaft + 50x50 plate
  clamp_axial_775 / clamp_axial_52 - ring clamp for J4 vertical (plate on top of the ring)
  clamp_side_775 / clamp_side_52   - ring clamp for J4 across (plate on the ring's side)
The ST3215 gripper module is not modelled yet.

Run headless (needs pg27.FCStd and forearm.FCStd next to it):
    <FreeCAD.AppImage> freecadcmd cad/tools.py --pass cad/tools.FCStd

Frame: the wrist fork's (forearm.FCStd): origin on the wrist axle, X forward,
Y across the arm (+y = J2 side), Z up. The fork's bridge bottom is at z = -fk_drop.
The script ends by reporting, for each tool on bracket_y, the tilt range in which
the tool clears the fork, the bracket and the forearm.
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
for f in ("pg27", "forearm"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
pg, fad = App.getDocument("pg27"), App.getDocument("forearm")
doc = App.newDocument("Tools")
doc.saveAs(out)

PARAMS = [
    ("fk_drop",    "24 mm",   "wrist fork bridge bottom below the wrist axle (forearm.FCStd)"),
    ("fk_in_x1",   "10 mm",   "fork inserts: x positions (forearm.FCStd FK_Insert*)"),
    ("fk_in_x2",   "34 mm",   ""),
    ("fk_in_y",    "7 mm",    "fork inserts: |y|"),
    ("br_t",       "6 mm",    "bracket plate thickness (= pg27 mount_t)"),
    ("m3_clear",   "3.4 mm",  "M3 clearance"),
    ("m3_head_d",  "6.5 mm",  "M3 head counterbore"),
    ("m3_head_h",  "3.2 mm",  "M3 head counterbore depth"),
    ("ins_d",      "4.2 mm",  "M3 heat insert hole"),
    ("ins_h",      "6 mm",    "M3 heat insert depth"),
    ("zx",         "68 mm",   "bracket_z: J4 axis x (motor body clears the fork bridge, ends at x 44)"),
    ("z_w",        "50 mm",   "bracket_z: plate width"),
    ("yx",         "70 mm",   "bracket_y: J4 axis x"),
    ("yz",         "-80 mm",  "bracket_y: J4 axis z (low, so tool ends pass under the fork)"),
    ("y_face",     "37 mm",   "bracket_y: J4 gearbox face |y| (side plate 31..37)"),
    ("y_plate_r",  "28 mm",   "bracket_y: side plate margin around the J4 axis"),
    ("fk_y_out",   "13.5 mm", "fork cheek outer face |y|"),
    ("shaft_d",    "7.98 mm", "PG27 shaft"),
    ("shaft_reach", "20.7 mm", "PG27 shaft tip from the gearbox face (boss 2.7 + 18)"),
    ("flat_depth", "0.5 mm",  "~ PG27 D-flat depth"),
    ("d_clr",      "0.15 mm", "D-bore clearance"),
    ("hub_r",      "11 mm",   "flange D-hub radius (room for the M3 grub nut slot)"),
    ("hub_gap",    "1 mm",    "gap between the bracket and the flange hub"),
    ("tp",         "50 mm",   "tool interface plate square"),
    ("tp_t",       "6 mm",    "tool interface plate thickness"),
    ("tp_hole",    "40 mm",   "tool interface: 4x M3 on this square"),
    ("grub_d",     "3.2 mm",  "M3 grub"),
    ("nut_w",      "5.7 mm",  "M3 nut across flats"),
    ("nut_t",      "2.6 mm",  "M3 nut slot"),
    ("cl_wall",    "6 mm",    "clamp ring wall"),
    ("cl_h",       "30 mm",   "clamp ring height"),
    ("cl_slit",    "2 mm",    "clamp slit"),
    ("cl_lug",     "10 mm",   "clamp pinch lug length out of the ring"),
    ("m4_clear",   "4.4 mm",  "M4 pinch bolt"),
    ("d775",       "42.2 mm", "775 motor body + clearance"),
    ("d52",        "52.2 mm", "52 mm spindle + clearance"),
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


def cyl_z(name, r, z0, z1, x="0 mm", y="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", f"({z1}) - ({z0})")
    place(o, x, y, z0)
    return o


def cyl_y(name, r, y0, y1, x="0 mm", z="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", f"({y1}) - ({y0})")
    o.Placement.Rotation = YROT
    place(o, x, y0, z)
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


def link(name, obj, rot, x="0 mm", y="0 mm", z="0 mm"):
    lk = doc.addObject("App::Link", name)
    lk.LinkedObject = obj
    lk.Placement.Rotation = rot
    place(lk, x, y, z)
    return lk


def fork_bolts(prefix, z_bot, z_top):
    """4x M3 up into the fork's inserts, heads counterbored from the bottom face."""
    t = []
    for k, (x, sy) in enumerate(((f"{P}fk_in_x1", 1), (f"{P}fk_in_x1", -1), (f"{P}fk_in_x2", 1), (f"{P}fk_in_x2", -1))):
        y = f"{sy} * {P}fk_in_y"
        t.append(cyl_z(f"{prefix}Bolt{k}", f"{P}m3_clear / 2", f"{z_bot} - 1 mm", f"{z_top} + 1 mm", x, y))
        t.append(cyl_z(f"{prefix}Head{k}", f"{P}m3_head_d / 2", f"{z_bot} - 1 mm", f"{z_bot} + {P}m3_head_h", x, y))
    return t


ROT_Z_DOWN = App.Rotation(App.Vector(1, 0, 0), 180)   # PG27 shaft (+Z) -> -Z, body up
ROT_Y_IN = App.Rotation(App.Vector(1, 0, 0), 90)      # PG27 shaft (+Z) -> -Y, body toward +Y
zb, zt = f"-{P}fk_drop - {P}br_t", f"-{P}fk_drop"     # bracket plate under the fork bridge

# --------------------------------------------------------------- bracket Z ---
bz_plate = box("BZ_Plate", "-2 mm", f"{P}zx + 30 mm", f"-{P}z_w / 2", f"{P}z_w / 2", zb, zt)
bz_cut = link("BZ_J4Cut", pg.getObject("PG27_MountCut"), ROT_Z_DOWN, f"{P}zx", "0 mm", zt)
bracket_z = cut("BracketZ", bz_plate, fork_bolts("BZ", zb, zt) + [bz_cut])
bracket_z.Label = "Tool bracket Z (print): J4 vertical"
j4_z = link("J4_Motor_Z", pg.getObject("PG27"), ROT_Z_DOWN, f"{P}zx", "0 mm", zt)

# flange Z on the J4 shaft: hub then the 50x50 plate, screws from the hub side
fz_top = f"{zb} - {P}hub_gap"
fz_tip = f"{zt} - {P}shaft_reach"
fz_hub = cyl_z("FZ_Hub", f"{P}hub_r", f"{fz_tip} - 0.5 mm", fz_top, f"{P}zx")
fz_plate = box("FZ_Plate", f"{P}zx - {P}tp / 2", f"{P}zx + {P}tp / 2", f"-{P}tp / 2", f"{P}tp / 2",
               f"{fz_tip} - 0.5 mm - {P}tp_t", f"{fz_tip} - 0.5 mm")
fz_tools = [cyl_z("FZ_Bore", f"{P}shaft_d / 2 + {P}d_clr", f"{fz_tip} - 1 mm", f"{fz_top} + 1 mm", f"{P}zx"),
            box("FZ_Flat", f"{P}zx + {P}shaft_d / 2 - {P}flat_depth + {P}d_clr", f"{P}zx + {P}shaft_d * 1.5",
                f"-{P}shaft_d", f"{P}shaft_d", f"{fz_tip} - 1 mm", f"{fz_top} + 1 mm"),
            # grub along +x onto the flat, nut slot opening on the hub's top face
            box("FZ_Grub", f"{P}zx", f"{P}zx + {P}hub_r + 1 mm", f"-{P}grub_d / 2", f"{P}grub_d / 2",
                f"{fz_top} - 6 mm - {P}grub_d / 2", f"{fz_top} - 6 mm + {P}grub_d / 2"),
            box("FZ_Nut", f"{P}zx + {P}shaft_d / 2 + 1.5 mm", f"{P}zx + {P}shaft_d / 2 + 1.5 mm + {P}nut_t",
                f"-{P}nut_w / 2", f"{P}nut_w / 2", f"{fz_top} - 6 mm - {P}nut_w / 2", f"{fz_top} + 1 mm")]
for k, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
    fz_tools.append(cyl_z(f"FZ_Hole{k}", f"{P}m3_clear / 2", f"{fz_tip} - 2 mm - {P}tp_t", f"{fz_tip}",
                          f"{P}zx + {sx} * {P}tp_hole / 2", f"{sy} * {P}tp_hole / 2"))
flange_z = cut("FlangeZ", fuse("FZ_Solid", [fz_hub, fz_plate]), fz_tools)
flange_z.Label = "Tool flange Z (print): D-hub on the J4 shaft + 50x50 plate"

# --------------------------------------------------------------- bracket Y ---
yf = f"{P}y_face"
by_base = box("BY_Base", "-2 mm", "44 mm", f"-{P}fk_y_out", yf, zb, zt)
by_side = box("BY_Side", "-2 mm", f"{P}yx + {P}y_plate_r", f"{yf} - {P}br_t", yf,
              f"{P}yz - {P}y_plate_r", zt)
by_cut = link("BY_J4Cut", pg.getObject("PG27_MountCut"), ROT_Y_IN, f"{P}yx", yf, f"{P}yz")
bracket_y = cut("BracketY", fuse("BY_Solid", [by_base, by_side]), fork_bolts("BY", zb, zt) + [by_cut])
bracket_y.Label = "Tool bracket Y (print): J4 across the arm, tilts the tool"
j4_y = link("J4_Motor_Y", pg.getObject("PG27"), ROT_Y_IN, f"{P}yx", yf, f"{P}yz")

# flange Y: hub along -y from the side plate, 50x50 plate facing -y
fy_top = f"{yf} - {P}br_t - {P}hub_gap"
fy_tip = f"{yf} - {P}shaft_reach"
fy_hub = cyl_y("FY_Hub", f"{P}hub_r", f"{fy_tip} - 0.5 mm", fy_top, f"{P}yx", f"{P}yz")
fy_plate = box("FY_Plate", f"{P}yx - {P}tp / 2", f"{P}yx + {P}tp / 2", f"{fy_tip} - 0.5 mm - {P}tp_t",
               f"{fy_tip} - 0.5 mm", f"{P}yz - {P}tp / 2", f"{P}yz + {P}tp / 2")
fy_tools = [cyl_y("FY_Bore", f"{P}shaft_d / 2 + {P}d_clr", f"{fy_tip} - 1 mm", f"{fy_top} + 1 mm", f"{P}yx", f"{P}yz"),
            box("FY_Flat", f"{P}yx + {P}shaft_d / 2 - {P}flat_depth + {P}d_clr", f"{P}yx + {P}shaft_d * 1.5",
                f"{fy_tip} - 1 mm", f"{fy_top} + 1 mm", f"{P}yz - {P}shaft_d", f"{P}yz + {P}shaft_d"),
            box("FY_Grub", f"{P}yx", f"{P}yx + {P}hub_r + 1 mm", f"{fy_top} - 6 mm - {P}grub_d / 2",
                f"{fy_top} - 6 mm + {P}grub_d / 2", f"{P}yz - {P}grub_d / 2", f"{P}yz + {P}grub_d / 2"),
            box("FY_Nut", f"{P}yx + {P}shaft_d / 2 + 1.5 mm", f"{P}yx + {P}shaft_d / 2 + 1.5 mm + {P}nut_t",
                f"{fy_top} - 6 mm - {P}nut_w / 2", f"{fy_top} + 1 mm", f"{P}yz - {P}nut_w / 2", f"{P}yz + {P}nut_w / 2")]
for k, (sx, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
    fy_tools.append(cyl_y(f"FY_Hole{k}", f"{P}m3_clear / 2", f"{fy_tip} - 2 mm - {P}tp_t", f"{fy_tip}",
                          f"{P}yx + {sx} * {P}tp_hole / 2", f"{P}yz + {sz} * {P}tp_hole / 2"))
flange_y = cut("FlangeY", fuse("FY_Solid", [fy_hub, fy_plate]), fy_tools)
flange_y.Label = "Tool flange Y (print): D-hub on the J4 shaft + 50x50 plate"

# ------------------------------------------------------------- tool clamps ---
# Modelled in their own frame: tool axis = Z, ring centre at the origin,
# interface plate either on top (axial) or on the +Y side (side).
def clamp(name, bore, side):
    ro = f"{bore} / 2 + {P}cl_wall"
    ring = cyl_z(name + "_Ring", ro, f"-{P}cl_h / 2", f"{P}cl_h / 2")
    # pinch lug: on +x for the axial clamp, on -x for the side clamp (away from its plate)
    lx0, lx1 = (f"-({ro} + {P}cl_lug)", "0 mm") if side else ("0 mm", f"{ro} + {P}cl_lug")
    lug = box(name + "_Lug", lx0, lx1, f"-{P}cl_wall", f"{P}cl_wall", f"-{P}cl_h / 2", f"{P}cl_h / 2")
    if side:
        plate = box(name + "_Plate", f"-{P}tp / 2", f"{P}tp / 2", f"{ro} - 1 mm", f"{ro} + {P}tp_t",
                    f"-{P}tp / 2", f"{P}tp / 2")
        holes = [cyl_y(f"{name}_Ins{k}", f"{P}ins_d / 2", f"{ro} + {P}tp_t - {P}ins_h", f"{ro} + {P}tp_t + 1 mm",
                       f"{sx} * {P}tp_hole / 2", f"{sz} * {P}tp_hole / 2")
                 for k, (sx, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1)))]
    else:
        plate = box(name + "_Plate", f"-{P}tp / 2", f"{P}tp / 2", f"-{P}tp / 2", f"{P}tp / 2",
                    f"{P}cl_h / 2 - 0.01 mm", f"{P}cl_h / 2 + {P}tp_t")
        holes = [cyl_z(f"{name}_Ins{k}", f"{P}ins_d / 2", f"{P}cl_h / 2 + {P}tp_t - {P}ins_h", f"{P}cl_h / 2 + {P}tp_t + 1 mm",
                       f"{sx} * {P}tp_hole / 2", f"{sy} * {P}tp_hole / 2")
                 for k, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1)))]
    sgn = "-" if side else ""
    tools = [cyl_z(name + "_Bore", f"{bore} / 2", f"-{P}cl_h / 2 - 1 mm", f"{P}cl_h / 2 + 1 mm"),
             box(name + "_Slit", f"{sgn}0 mm" if not side else f"-({ro} + {P}cl_lug + 1 mm)",
                 f"{ro} + {P}cl_lug + 1 mm" if not side else "0 mm",
                 f"-{P}cl_slit / 2", f"{P}cl_slit / 2", f"-{P}cl_h / 2 - 1 mm", f"{P}cl_h / 2 + 1 mm"),
             cyl_y(name + "_Pinch", f"{P}m4_clear / 2", f"-{P}cl_wall - 1 mm", f"{P}cl_wall + 1 mm",
                   f"{sgn}({ro} + {P}cl_lug / 2)")] + holes
    o = cut(name, fuse(name + "_Solid", [ring, lug, plate]), tools)
    return o


clamps = {
    "clamp_axial_775": clamp("ClampAxial775", f"{P}d775", False),
    "clamp_axial_52": clamp("ClampAxial52", f"{P}d52", False),
    "clamp_side_775": clamp("ClampSide775", f"{P}d775", True),
    "clamp_side_52": clamp("ClampSide52", f"{P}d52", True),
}
for k, o in clamps.items():
    o.Label = k.replace("_", " ") + " (print)"

# context: the wrist fork
ctx = doc.addObject("App::Link", "Ctx_WristFork")
ctx.LinkedObject = fad.getObject("WristFork")
grp_z = doc.addObject("App::DocumentObjectGroup", "Setup_Z")
for o in (bracket_z, j4_z, flange_z):
    grp_z.addObject(o)
grp_y = doc.addObject("App::DocumentObjectGroup", "Setup_Y")
for o in (bracket_y, j4_y, flange_y):
    grp_y.addObject(o)
grp_c = doc.addObject("App::DocumentObjectGroup", "Clamps")
for o in clamps.values():
    grp_c.addObject(o)
    o.Visibility = False
for o in (bracket_y, j4_y, flange_y):
    o.Visibility = False      # show the Z setup by default

doc.recompute()
bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
if bad:
    sys.exit(f"recompute failed: {bad}")
doc.save()


# ----------------------------------------------------------- exports ---
def export(obj, stem, rot_axis=None, ang=0):
    s = obj.Shape.copy()
    if rot_axis is not None:
        s.rotate(App.Vector(0, 0, 0), rot_axis, ang)
    s.translate(App.Vector(0, 0, -s.BoundBox.ZMin))
    tmp = Part.show(s, "tmp_export")
    Import.export([tmp], os.path.join(here, stem + ".step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.05))
    m.write(os.path.join(here, stem + ".stl"))
    doc.removeObject(tmp.Name)


X = App.Vector(1, 0, 0)
export(bracket_z, "bracket_z")                      # bottom face on the bed
export(bracket_y, "bracket_y", X, -90)              # outer face of the side plate on the bed
export(flange_z, "flange_z")                        # plate on the bed, hub up
export(flange_y, "flange_y", X, 90)                 # plate on the bed, hub up
for stem, o in clamps.items():
    if "side" in stem:
        export(o, stem, X, 90)                      # interface plate on the bed
    else:
        export(o, stem, X, 180)                     # interface plate on the bed

for o in [bracket_z, bracket_y, flange_z, flange_y] + list(clamps.values()):
    s = o.Shape
    print(f"{o.Name:14s} vol {s.Volume / 1000:6.2f} cm3 valid {s.isValid()} solids {len(s.Solids)}")

# ------------------------------------------------------------ fit checks ---
fork = ctx.Shape
pgd = pg
body = pgd.getObject("Motor_NEMA17").Shape.fuse([pgd.getObject(k).Shape for k in ("Flange", "Gearbox")])


def motor_body(lk):
    s = body.copy()
    s.Placement = lk.Placement.multiply(s.Placement)
    return s


print("static fit (mm3, should be 0):")
for a, b in ((bracket_z, "fork"), (bracket_y, "fork"), (flange_z, bracket_z), (flange_y, bracket_y)):
    sb = fork if b == "fork" else b.Shape
    print(f"  {a.Name} x {b if b == 'fork' else b.Name}: {a.Shape.common(sb).Volume:.1f}")
print(f"  J4 body (Z) x fork: {motor_body(j4_z).common(fork).Volume:.1f}")
print(f"  J4 body (Y) x fork: {motor_body(j4_y).common(fork).Volume:.1f}")
print(f"  J4 body (Y) x bracket Y: {motor_body(j4_y).common(bracket_y.Shape).Volume:.1f}")

# tilt range on bracket Y: tool envelope = clamp + cylinder body, clamp at the tool's centre of mass,
# tool pitch p: 0 = pointing down, +90 = pointing forward. Obstacles: fork, bracket Y, flange Y,
# and the forearm for J3 in -70..35 (it leaves the wrist backwards).
L3 = fad.getObject("Params").len_l3.Value
forearm = fad.getObject("Forearm").Shape
TOOLS = {  # name: (clamp object, body radius, length above / below the clamp centre)
    "775 + chuck": (clamps["clamp_side_775"], 21.0, 48.0, 92.0),
    # clamped 25 mm above its centre of mass: clamped exactly at the CoG its top end hits the
    # fork between +5 and +65 deg; 25 mm up frees the whole range for <= 0.27 N*m on J4
    "spindle 52": (clamps["clamp_side_52"], 26.0, 52.0, 138.0),
}
yx, yz = ss.yx.Value, ss.yz.Value
plate_face = ss.y_face.Value - ss.shaft_reach.Value - 0.5 - ss.tp_t.Value   # tool plate meets the flange here


def tool_shape(entry, pitch):
    cl, r, up, down = entry
    s = cl.Shape.copy()
    body_c = Part.makeCylinder(r, up + down, App.Vector(0, 0, -down))
    s = s.fuse(body_c)
    ro = cl.Shape.BoundBox.YMax          # clamp plate outer face (+y) in the clamp frame
    s.translate(App.Vector(0, plate_face - ro, 0))
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -pitch)   # +pitch tips the bottom forward
    s.translate(App.Vector(yx, 0, yz))
    return s


obstacles = [fork, bracket_y.Shape, flange_y.Shape]
for j3 in (-70, -30, 0, 35):
    f = forearm.copy()
    f.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -j3)
    a = math.radians(j3)
    f.translate(App.Vector(-L3 * math.cos(a), 0, -L3 * math.sin(a)))
    obstacles.append(f)
print("tilt range on bracket Y (clear of fork, bracket, flange, forearm):")
for name, entry in TOOLS.items():
    ok = [p for p in range(-60, 131, 5) if all(tool_shape(entry, p).common(o).Volume < 0.5 for o in obstacles)]
    rng = f"{min(ok)}..{max(ok)} deg" if ok else "none"
    gaps = [p for p in range(min(ok), max(ok) + 1, 5) if p not in ok] if ok else []
    print(f"  {name}: {rng}" + (f" (blocked at {gaps})" if gaps else ""))
