"""
pg27.py - parametric FreeCAD model of the 17HS15-1684S-PG27 geared stepper.

Builds cad/pg27.FCStd (and pg27.step) from the measured dimensions in the
`Params` spreadsheet. Every solid is a Part primitive whose size/position is an
expression on that sheet, so editing a cell in FreeCAD rebuilds the model.

Run headless (the AppImage path is the active line in ~/freecad.sh):
    <FreeCAD.AppImage> freecadcmd cad/pg27.py --pass cad/pg27.FCStd

Frame: origin on the gearbox top face (the mounting face), +Z along the output
shaft. The motor hangs below (-Z).

Values marked "~" in the sheet's note column are estimated from photos, not
measured. If a solid doesn't follow a changed cell, select the objects,
right-click > "Mark to recompute", then Ctrl+R (seen headless: editing the
sheet from Python did not touch its dependents on its own).

Part colors are not set here (freecadcmd has no view providers); they were
applied once through the GUI and live in pg27.FCStd. Rerunning this script
resets them to the default grey.

Two helper solids are hidden in the document for designing printed parts:
  PG27_MountCut      - subtract from a plate that sits on the mounting face
                       (z = 0 .. mount_t): boss recess, shaft clearance,
                       4x M3 clearance + counterbore, cap-screw head relief.
  PG27_BodyClearance - subtract from a part that wraps around the gearbox.
"""

import os
import sys

import FreeCAD as App
import Part  # noqa: F401  (registers Part:: types)
import Import

out = next(a for a in sys.argv if a.endswith(".FCStd"))
doc = App.newDocument("PG27")

# ---------------------------------------------------------------- params ---
# (alias, value, comment). "~" marks values estimated, not measured.
PARAMS = [
    ("motor_sq",    "42.3 mm", "NEMA17 body square"),
    ("motor_h",     "39 mm",   "NEMA17 body height (measured)"),
    ("fl_sq",       "40 mm",   "adapter flange square (measured)"),
    ("fl_d",        "52 mm",   "flange corners cut by this circle (measured)"),
    ("fl_t",        "5 mm",    "adapter flange thickness (measured)"),
    ("gb_d",        "35.9 mm", "gearbox OD (measured, photo)"),
    ("gb_h",        "30 mm",   "gearbox height (measured)"),
    ("boss_d",      "22 mm",   "output bearing boss (measured)"),
    ("boss_h",      "2.7 mm",  "boss height above mounting face (measured)"),
    ("shaft_d",     "7.98 mm", "output shaft (measured)"),
    ("shaft_l",     "18 mm",   "shaft length above the boss (measured)"),
    ("flat_l",      "15 mm",   "~ D-flat length (VXB listing)"),
    ("flat_depth", "0.98 mm", "D-flat depth: 7.0 mm across the flat on the 7.98 shaft (measured)"),
    ("hole_pcd",    "28 mm",   "~ 4 mounting holes, 45/135/225/315 deg (photo)"),
    ("hole_d",      "2.5 mm",  "M3 tapped hole (confirmed with an M3 screw)"),
    ("hole_depth",  "6.5 mm",  "thread depth (measured: the gearbox top ring, 6.5)"),
    ("cap_pcd",     "28 mm",   "~ gearbox clamp screws, 0/90/180/270 deg (photo)"),
    ("cap_d",       "5.5 mm",  "~ M3 socket head"),
    ("notch_d",     "7 mm",    "~ rim notch around each clamp screw head"),
    ("notch_h",     "3 mm",    "~ notch depth"),
    ("clr",         "0.3 mm",  "printing clearance used by the cut tools"),
    ("mount_t",     "6 mm",    "plate thickness the MountCut tool is sized for"),
    ("m3_clear",    "3.4 mm",  "M3 clearance hole"),
    ("m3_head_d",   "6.5 mm",  "M3 socket head counterbore"),
    ("m3_head_h",   "3.2 mm",  "M3 socket head counterbore depth"),
]

ss = doc.addObject("Spreadsheet::Sheet", "Params")
ss.set("A1", "parameter")
ss.set("B1", "value")
ss.set("C1", "note")
for i, (alias, value, note) in enumerate(PARAMS, start=2):
    ss.set(f"A{i}", alias)
    ss.set(f"B{i}", value)
    ss.setAlias(f"B{i}", alias)
    ss.set(f"C{i}", note)
doc.recompute()

P = "Params."


def expr(obj, prop, e):
    obj.setExpression(prop, e)


def place(obj, x="0 mm", y="0 mm", z="0 mm"):
    expr(obj, ".Placement.Base.x", x)
    expr(obj, ".Placement.Base.y", y)
    expr(obj, ".Placement.Base.z", z)


def cyl(name, r, h, z, x="0 mm", y="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", h)
    place(o, x, y, z)
    return o


def box(name, lx, ly, lz, x, y, z):
    o = doc.addObject("Part::Box", name)
    expr(o, "Length", lx)
    expr(o, "Width", ly)
    expr(o, "Height", lz)
    place(o, x, y, z)
    return o


def on_pcd(pcd, ang):
    return (f"{P}{pcd} / 2 * cos({ang} deg)", f"{P}{pcd} / 2 * sin({ang} deg)")


def fuse(name, objs):
    o = doc.addObject("Part::MultiFuse", name)
    o.Shapes = objs
    for s in objs:
        s.Visibility = False
    return o


def cut(name, base, tool):
    o = doc.addObject("Part::Cut", name)
    o.Base = base
    o.Tool = tool
    base.Visibility = tool.Visibility = False
    return o


# ------------------------------------------------------------- the motor ---
motor = box("Motor_NEMA17", f"{P}motor_sq", f"{P}motor_sq", f"{P}motor_h",
            f"-{P}motor_sq / 2", f"-{P}motor_sq / 2", f"-({P}gb_h + {P}fl_t + {P}motor_h)")

fl_box = box("Flange_Square", f"{P}fl_sq", f"{P}fl_sq", f"{P}fl_t",
             f"-{P}fl_sq / 2", f"-{P}fl_sq / 2", f"-({P}gb_h + {P}fl_t)")
fl_circ = cyl("Flange_Circle", f"{P}fl_d / 2", f"{P}fl_t", f"-({P}gb_h + {P}fl_t)")
flange = doc.addObject("Part::MultiCommon", "Flange")
flange.Shapes = [fl_box, fl_circ]
fl_box.Visibility = fl_circ.Visibility = False

gb_body = cyl("Gearbox_Body", f"{P}gb_d / 2", f"{P}gb_h", f"-{P}gb_h")
gb_tools = []
for k, ang in enumerate((45, 135, 225, 315)):
    x, y = on_pcd("hole_pcd", ang)
    gb_tools.append(cyl(f"MountHole{k}", f"{P}hole_d / 2", f"{P}hole_depth + 0.01 mm",
                        f"-{P}hole_depth", x, y))
for k, ang in enumerate((0, 90, 180, 270)):
    x, y = on_pcd("cap_pcd", ang)
    gb_tools.append(cyl(f"CapNotch{k}", f"{P}notch_d / 2", f"{P}notch_h + 0.01 mm",
                        f"-{P}notch_h", x, y))
gearbox = cut("Gearbox", gb_body, fuse("Gearbox_Tools", gb_tools))

heads = []
for k, ang in enumerate((0, 90, 180, 270)):
    x, y = on_pcd("cap_pcd", ang)
    heads.append(cyl(f"CapHead{k}", f"{P}cap_d / 2", f"{P}notch_h - 0.3 mm", f"-{P}notch_h", x, y))
cap_heads = fuse("Gearbox_CapScrews", heads)

boss = cyl("Boss", f"{P}boss_d / 2", f"{P}boss_h", "0 mm")
clip = cyl("Circlip", f"{P}shaft_d / 2 + 2.5 mm", "0.8 mm", f"{P}boss_h")
shaft_raw = cyl("Shaft_Round", f"{P}shaft_d / 2", f"{P}shaft_l", f"{P}boss_h")
flat = box("Shaft_FlatCut", f"{P}shaft_d", f"{P}shaft_d", f"{P}flat_l + 0.01 mm",
           f"{P}shaft_d / 2 - {P}flat_depth", f"-{P}shaft_d / 2",
           f"{P}boss_h + {P}shaft_l - {P}flat_l")
shaft = cut("Shaft", shaft_raw, flat)

part = doc.addObject("App::Part", "PG27")
part.Label = "17HS15-1684S-PG27"
for o in (motor, flange, gearbox, cap_heads, boss, clip, shaft):
    part.addObject(o)

# ------------------------------------------------------- design helpers ---
tools = [
    # boss recess and shaft clearance through the plate (and beyond)
    cyl("MC_Boss", f"{P}boss_d / 2 + {P}clr", f"{P}boss_h + {P}clr", "-0.01 mm"),
    cyl("MC_Shaft", f"{P}shaft_d / 2 + 3 mm",  # clears the circlip
        f"{P}mount_t + {P}shaft_l + 5 mm", "-0.01 mm"),
]
for k, ang in enumerate((45, 135, 225, 315)):
    x, y = on_pcd("hole_pcd", ang)
    tools.append(cyl(f"MC_Hole{k}", f"{P}m3_clear / 2", f"{P}mount_t + 0.02 mm", "-0.01 mm", x, y))
    tools.append(cyl(f"MC_Head{k}", f"{P}m3_head_d / 2", f"{P}m3_head_h + 5 mm",
                     f"{P}mount_t - {P}m3_head_h", x, y))
for k, ang in enumerate((0, 90, 180, 270)):
    x, y = on_pcd("cap_pcd", ang)
    tools.append(cyl(f"MC_CapRelief{k}", f"{P}notch_d / 2", "1 mm", "-0.01 mm", x, y))
mount_cut = fuse("PG27_MountCut", tools)
mount_cut.Visibility = False

body_clear = cyl("PG27_BodyClearance", f"{P}gb_d / 2 + {P}clr", f"{P}gb_h + 0.01 mm", f"-{P}gb_h")
body_clear.Visibility = False

helpers = doc.addObject("App::DocumentObjectGroup", "DesignHelpers")
helpers.addObject(mount_cut)
helpers.addObject(body_clear)

doc.recompute()

bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
if bad:
    sys.exit(f"recompute failed: {bad}")

doc.saveAs(os.path.abspath(out))
step = os.path.splitext(out)[0] + ".step"
Import.export([motor, flange, gearbox, cap_heads, boss, clip, shaft], os.path.abspath(step))

for o in (motor, flange, gearbox, boss, shaft, mount_cut):
    bb = o.Shape.BoundBox
    print(f"{o.Name:16s} vol {o.Shape.Volume:9.1f} mm3  z {bb.ZMin:7.2f} .. {bb.ZMax:6.2f}  "
          f"xy {bb.XLength:5.1f} x {bb.YLength:5.1f}")
print("saved", out, "and", step)
