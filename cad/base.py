"""
base.py - parametric FreeCAD model of the arm's base (J1): printed housing,
51211 thrust bearing and the J1 PG27 hanging under the housing roof.

Builds cad/base.FCStd, base_housing.step and base_housing.stl (print it as
modelled: table flange on the bed, the 45 deg cone under the roof needs no
support). Needs cad/pg27.FCStd next to it - the J1 motor and the mounting
cut-outs in the roof are App::Links into that file, so a change to the PG27
parameters carries over here after a recompute.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/base.py --pass cad/base.FCStd

Frame: table at z = 0, J1 axis = Z. The J1 gearbox face sits on the roof's
underside; its shaft comes up through the roof into the bearing's bore, where
the turret's D-bore hub picks it up (next part). The turret rests on the
bearing's upper washer; the shaft only carries the yaw torque.
"""

import os
import sys

import FreeCAD as App
import Part  # noqa: F401
import Import
import Mesh

out = os.path.abspath(next(a for a in sys.argv if a.endswith(".FCStd")))
here = os.path.dirname(out)
pg = App.openDocument(os.path.join(here, "pg27.FCStd"))
doc = App.newDocument("Base")
doc.saveAs(out)  # cross-document links need a saved owner (relative path to pg27.FCStd)

PARAMS = [
    ("bear_d",      "90 mm",   "51211 outer diameter"),
    ("bear_bore",   "55 mm",   "51211 bore"),
    ("bear_h",      "25 mm",   "51211 height"),
    ("wash_t",      "7.5 mm",  "~ washer thickness (for the picture only)"),
    ("seat_h",      "3 mm",    "bearing seat depth in the roof"),
    ("clr",         "0.3 mm",  "printing clearance"),
    ("roof_t",      "8 mm",    "roof thickness under the bearing"),
    ("motor_drop",  "74 mm",   "PG27 below its face = gb_h + fl_t + motor_h (pg27.FCStd)"),
    ("floor_gap",   "3 mm",    "motor bottom above the table"),
    ("body_od",     "104 mm",  "housing outer diameter"),
    ("inner_d",     "64 mm",   "motor cavity (NEMA17 diagonal is 59.8)"),
    ("cone_top_d",  "40 mm",   "cavity narrows at 45 deg to this under the roof"),
    ("fl_d",        "160 mm",  "table flange diameter"),
    ("fl_t",        "5 mm",    "table flange thickness"),
    ("screw_d",     "5.5 mm",  "4 table screws (M5)"),
    ("screw_r",     "70 mm",   "table screw radius"),
    ("gus_l",       "24 mm",   "gusset reach on the flange"),
    ("gus_h",       "30 mm",   "gusset height on the wall"),
    ("gus_t",       "4 mm",    "gusset thickness"),
    ("win_w",       "22 mm",   "cable window width"),
    ("win_h",       "20 mm",   "cable window height"),
    ("motor_rot",   "0 deg",   "J1 motor turned about Z (hole pattern / cable side)"),
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
# derived heights, kept on the sheet so the turret can read them
n = len(PARAMS) + 3
for k, (alias, value, note) in enumerate([
    ("body_h",   "=roof_t + motor_drop + floor_gap", "housing height = roof top"),
    ("face_z",   "=body_h - roof_t",                 "J1 gearbox face (roof underside)"),
    ("bear_top", "=body_h - seat_h + bear_h",        "turret rests here (bearing top)"),
    ("shaft_top", "=face_z + 2.7 mm + 18 mm",        "J1 shaft tip (boss 2.7 + shaft 18)"),
]):
    r = n + k
    ss.set(f"A{r}", alias)
    ss.set(f"B{r}", value)
    ss.setAlias(f"B{r}", alias)
    ss.set(f"C{r}", note)
doc.recompute()

P = "Params."


def expr(o, prop, e):
    o.setExpression(prop, e)


def place(o, x="0 mm", y="0 mm", z="0 mm"):
    expr(o, ".Placement.Base.x", x)
    expr(o, ".Placement.Base.y", y)
    expr(o, ".Placement.Base.z", z)


def cyl(name, r, h, z, x="0 mm", y="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", h)
    place(o, x, y, z)
    return o


def hide(*objs):
    for o in objs:
        o.Visibility = False


# --------------------------------------------------------------- housing ---
shell = cyl("Shell", f"{P}body_od / 2", f"{P}body_h", "0 mm")
flange = cyl("TableFlange", f"{P}fl_d / 2", f"{P}fl_t", "0 mm")

gussets = []
for k in range(6):
    a = 30 + 60 * k
    w = doc.addObject("Part::Wedge", f"Gusset{k}")
    w.Xmin = w.X2min = 0
    expr(w, "Xmax", f"{P}gus_l")
    w.X2max = 0.01
    w.Ymin = 0
    expr(w, "Ymax", f"{P}gus_h")
    expr(w, "Zmin", f"-{P}gus_t / 2")
    expr(w, "Zmax", f"{P}gus_t / 2")
    expr(w, "Z2min", f"-{P}gus_t / 2")
    expr(w, "Z2max", f"{P}gus_t / 2")
    # wedge's Y (its tapering axis) -> world Z, its X -> radial at angle a
    w.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), a).multiply(App.Rotation(App.Vector(1, 0, 0), 90))
    place(w, f"({P}body_od / 2 - 1 mm) * cos({a} deg)", f"({P}body_od / 2 - 1 mm) * sin({a} deg)", f"{P}fl_t")
    gussets.append(w)

solid = doc.addObject("Part::MultiFuse", "HousingSolid")
solid.Shapes = [shell, flange] + gussets
hide(shell, flange, *gussets)

cavity = cyl("Cavity", f"{P}inner_d / 2", f"{P}face_z - ({P}inner_d - {P}cone_top_d) / 2 + 1.01 mm", "-1 mm")
cone = doc.addObject("Part::Cone", "CavityCone")
expr(cone, "Radius1", f"{P}inner_d / 2")
expr(cone, "Radius2", f"{P}cone_top_d / 2")
expr(cone, "Height", f"({P}inner_d - {P}cone_top_d) / 2")
place(cone, z=f"{P}face_z - ({P}inner_d - {P}cone_top_d) / 2")
seat = cyl("BearingSeat", f"{P}bear_d / 2 + {P}clr", f"{P}seat_h + 1 mm", f"{P}body_h - {P}seat_h")
screws = [cyl(f"TableScrew{k}", f"{P}screw_d / 2", f"{P}fl_t + 2 mm", "-1 mm",
              f"{P}screw_r * cos({45 + 90 * k} deg)", f"{P}screw_r * sin({45 + 90 * k} deg)")
          for k in range(4)]
win = doc.addObject("Part::Box", "CableWindow")
expr(win, "Length", f"{P}body_od / 2 + 1 mm")  # through the wall only, not the flange
expr(win, "Width", f"{P}win_w")
expr(win, "Height", f"{P}win_h + 1 mm")
place(win, "0 mm", f"-{P}win_w / 2", "-1 mm")

# J1 mounting cut-outs straight from pg27.FCStd, placed on the roof underside
mcut = doc.addObject("App::Link", "J1_MountCut")
mcut.LinkedObject = pg.getObject("PG27_MountCut")
expr(mcut, ".Placement.Base.z", f"{P}face_z")
expr(mcut, ".Placement.Rotation.Angle", f"{P}motor_rot")
mcut.Placement.Rotation.Axis = App.Vector(0, 0, 1)

tools = doc.addObject("Part::MultiFuse", "HousingTools")
tools.Shapes = [cavity, cone, seat, win, mcut] + screws
hide(cavity, cone, seat, win, mcut, *screws)

housing = doc.addObject("Part::Cut", "BaseHousing")
housing.Base = solid
housing.Tool = tools
hide(solid, tools)
housing.Label = "Base housing (print)"

# ---------------------------------------------------------- bought parts ---
j1 = doc.addObject("App::Link", "J1_Motor")
j1.LinkedObject = pg.getObject("PG27")
expr(j1, ".Placement.Base.z", f"{P}face_z")
expr(j1, ".Placement.Rotation.Angle", f"{P}motor_rot")
j1.Placement.Rotation.Axis = App.Vector(0, 0, 1)
j1.Label = "J1 - 17HS15-1684S-PG27"


def ring(name, r_in, r_out, h, z):
    a = cyl(name + "_o", r_out, h, z)
    b = cyl(name + "_i", r_in, f"{h} + 0.02 mm", f"{z} - 0.01 mm")
    c = doc.addObject("Part::Cut", name)
    c.Base, c.Tool = a, b
    hide(a, b)
    return c


z0 = f"{P}body_h - {P}seat_h"
w_lo = ring("Washer_Housing", f"{P}bear_bore / 2 + 1 mm", f"{P}bear_d / 2", f"{P}wash_t", z0)
w_hi = ring("Washer_Shaft", f"{P}bear_bore / 2", f"{P}bear_d / 2 - 0.5 mm", f"{P}wash_t",
            f"{z0} + {P}bear_h - {P}wash_t")
balls = ring("Balls", f"{P}bear_bore / 2 + 6 mm", f"{P}bear_d / 2 - 6 mm",
             f"{P}bear_h - 2 * {P}wash_t", f"{z0} + {P}wash_t")
bearing = doc.addObject("App::Part", "Bearing_51211")
bearing.Label = "51211 thrust bearing (55x90x25)"
for o in (w_lo, w_hi, balls):
    bearing.addObject(o)

doc.recompute()
bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
if bad:
    sys.exit(f"recompute failed: {bad}")

doc.saveAs(out)
stem = os.path.join(here, "base_housing")
Import.export([housing], stem + ".step")
Mesh.export([housing], stem + ".stl")

bb = housing.Shape.BoundBox
print(f"housing: vol {housing.Shape.Volume / 1000:.1f} cm3, {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}, "
      f"valid {housing.Shape.isValid()}, solids {len(housing.Shape.Solids)}")
for a in ("body_h", "face_z", "bear_top", "shaft_top"):
    print(f"{a:10s} {ss.get(a)}")
motor_bb = j1.Shape.BoundBox
print(f"J1 motor z {motor_bb.ZMin:.1f} .. {motor_bb.ZMax:.1f}")
print("motor/housing overlap mm3:", round(j1.Shape.common(housing.Shape).Volume, 2))
print("bearing/housing overlap mm3:", round(bearing.Shape.common(housing.Shape).Volume if hasattr(bearing, 'Shape') else -1, 2))
