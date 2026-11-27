"""
export_parts.py - dump every CAD part as a mesh for the browser viewer.

Writes cad/viewer/parts.js (window.ARM_CAD = {...}): each part tessellated in its own
joint frame (FreeCAD coordinates: X forward, Y across the arm (+Y = J2 side), Z up),
plus the motor placements and the geometry the viewer's kinematics need. A <script>
tag loads it, so the viewer still opens straight from disk.

Run headless after changing any cad/*.py model:
    <FreeCAD.AppImage> freecadcmd cad/viewer/export_parts.py
"""

import base64
import json
import math
import os
import struct
import sys

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
DOCS = ("pg27", "base", "turret", "upper_arm", "forearm", "tools", "limits", "electronics")
for f in DOCS:
    App.openDocument(os.path.join(CAD, f + ".FCStd"))
D = {n: App.getDocument(n) for n in DOCS}
TOL = 0.3
sys.path.insert(0, CAD)
import endstop_dims as ES  # noqa: E402
V = App.Vector


def mesh(shape):
    pts, tris = shape.tessellate(TOL)
    p = struct.pack("<%df" % (3 * len(pts)), *[c for v in pts for c in (v.x, v.y, v.z)])
    i = struct.pack("<%dI" % (3 * len(tris)), *[k for t in tris for k in t])
    return {"p": base64.b64encode(p).decode(), "i": base64.b64encode(i).decode(), "n": len(tris)}


def shp(doc, name):
    return D[doc].getObject(name).Shape


def compound(doc, names):
    return Part.makeCompound([shp(doc, n) for n in names])


def mat(placement):
    m = placement.toMatrix()
    return [m.A11, m.A12, m.A13, m.A14, m.A21, m.A22, m.A23, m.A24,
            m.A31, m.A32, m.A33, m.A34, m.A41, m.A42, m.A43, m.A44]


def elbow_b609():
    s = Part.makeCompound([shp("forearm", "B609_ElbowJ2"), shp("forearm", "B609_ElbowJ3")]).copy()
    s.translate(App.Vector(D["forearm"].getObject("Params").len_l2.Value, 0, 0))
    return s


def elbow_washers():
    """One each side of the forearm, as forearm.py's washers() puts them."""
    p = D["forearm"].getObject("Params")
    a, b = shp("forearm", "ElbowWasher").copy(), shp("forearm", "ElbowWasher").copy()
    a.translate(App.Vector(0, p.fa_t.Value / 2 + 0.05, 0))
    b.translate(App.Vector(0, -p.fa_t.Value / 2 - 0.05 - p.wash_t.Value, 0))
    return Part.makeCompound([a, b])


# --- limit switches: the lever with its roller moves, the body doesn't ---
# EndstopJ* in limits.FCStd is a compound (body, terminals, lever standing free); the lever is child 2.
def board(tag):
    return Part.makeCompound(shp("limits", "Endstop" + tag).childShapes()[:2])


def lever(tag):
    return shp("limits", "Endstop" + tag).childShapes()[2]


SH_Z = D["turret"].getObject("Params").shoulder_z.Value
Z_SEAT = SH_Z - ES.ROLLER_DEPTH - ES.SW_T / 2
X0 = -(ES.ROLLER_XR + ES.ROLLER_X)
Y2, Y3 = ES.J2_FACE - ES.PRESS_TOP, ES.J3_FACE + ES.PRESS_TOP
Y0_J1 = -ES.ROLLER_X + ES.J1_ROLLER_OFF
# switch frame (x along the body, y out of the lever face, z its thickness) -> the frame the switch lives in
# (the turret's for J2/J3, the world's for J1), as cad/limits.py places them; switch z is the hinge axis
TO_FRAME = {
    "J2": (lambda b: V(b.x + X0, b.y + Y2, b.z + Z_SEAT), V(0, 0, 1)),
    "J3": (lambda b: V(-b.x - X0, -b.y + Y3, b.z + Z_SEAT), V(0, 0, 1)),
    "J1": (lambda b: V(b.z + ES.J1_SEAT_X, b.x + Y0_J1, b.y + ES.J1_EDGE), V(1, 0, 0)),
}
FREE = ES.lever_turn(ES.FREE_TOP)      # the lever's angle standing free, from where it lies on a cam's flat


def _rot(s, c, ax, ang):
    r = s.copy()
    r.rotate(c, ax, ang)
    return r


def mover(tag):
    """what works this switch, posed at joint angle ang"""
    if tag == "J1":
        s = Part.makeCompound([shp("limits", "LimitFlag")])
        return lambda ang: _rot(s, V(0, 0, 0), V(0, 0, 1), ang)
    s = compound("upper_arm", ["UpperArmJ2"] if tag == "J2" else ["J3Crank"])
    off = 0 if tag == "J2" else 180
    return lambda ang: _rot(s, V(0, 0, 0), V(0, 1, 0), -(ang + off)).translated(V(0, 0, SH_Z))


def lever_table(tag, spans):
    """the lever's angle (deg, from standing free; negative = pushed in) against the joint angle near each trip
    point: the cam pushes the roller in as far as it has to, so the lever sits at the largest angle up to free
    that the cam doesn't overlap"""
    to, ax = TO_FRAME[tag]
    hinge = to(V(ES.LEV_HINGE[0], ES.LEV_HINGE[1], 0))
    free = lever(tag)
    bb = free.BoundBox
    win = Part.makeBox(bb.XLength + 30, bb.YLength + 30, bb.ZLength + 30, V(bb.XMin - 15, bb.YMin - 15, bb.ZMin - 15))
    pose = mover(tag)
    low = ES.lever_turn(ES.PRESS_TOP - 0.3) - FREE
    segs = []
    for lo, hi in spans:
        step, lv = 0.5, []
        for i in range(int(round((hi - lo) / step)) + 1):
            cam = pose(lo + i * step).common(win)
            hit = lambda a: cam.Volume > 0 and _rot(free, hinge, ax, a).common(cam).Volume > 0.0005   # noqa: E731
            if not hit(0.0):
                a = 0.0
            elif hit(low):
                a = low
            else:
                a0, a1 = low, 0.0          # a0 clear, a1 hit
                for _ in range(10):
                    m = (a0 + a1) / 2
                    a0, a1 = (a0, m) if hit(m) else (m, a1)
                a = a0
            lv.append(round(a, 3))
        segs.append({"a0": lo, "step": step, "lv": lv})
    return {"hinge": list(hinge), "axis": list(ax), "free": FREE, "click": ES.lever_turn(ES.OP_TOP), "segs": segs}


parts = {
    # world (static)
    "base_housing": shp("base", "BaseHousing"),
    "bearing_51211": compound("base", ["Washer_Housing", "Washer_Shaft", "Balls"]),
    "j1_keeper": shp("base", "J1Keeper"),
    "limit_collar": compound("limits", ["LimitCollarFront", "LimitCollarRear"]),
    "endstop_j1": board("J1"),
    "lever_j1": lever("J1"),
    "skr_plate": shp("electronics", "SkrPlate"),
    "skr_pico": shp("electronics", "SkrPico"),
    # PG27, one mesh reused for all four joints (its own frame: gearbox face at 0, shaft +Z)
    "pg27_body": shp("pg27", "Motor_NEMA17"),
    "pg27_gear": compound("pg27", ["Flange", "Gearbox", "Boss", "Gearbox_CapScrews"]),
    "pg27_shaft": compound("pg27", ["Shaft", "Circlip"]),
    # turret frame (turns with J1)
    "turret_body": shp("turret", "TurretBody"),
    "j1_hub": shp("turret", "J1Hub"),
    "j1_hub_screws": shp("turret", "J1HubScrews"),
    "limit_plate": shp("limits", "LimitPlate"),
    "limit_flag": shp("limits", "LimitFlag"),
    "endstops": Part.makeCompound([board("J2"), board("J3")]),
    "lever_j2": lever("J2"),
    "lever_j3": lever("J3"),
    # upper arm frame (origin on the shoulder axis, X along the link)
    "ua_j2": shp("upper_arm", "UpperArmJ2"),
    "ua_j2_cap": shp("upper_arm", "UpperArmJ2Cap"),
    "ua_j3": shp("upper_arm", "UpperArmJ3"),
    "ua_spacers": compound("upper_arm", ["Spacer0", "Spacer1", "Spacer2"]),
    "ua_bush6803": shp("upper_arm", "TempBushing6803"),   # 6803 (17x26x5) or its printed stand-in
    # 609Z: elbow pair in the upper arm frame (the CAD draws them at the elbow origin), wrist in the forearm frame
    "b609_elbow": elbow_b609(),
    "b609_wrist": shp("forearm", "B609_Wrist"),
    # crank frame (origin on the shoulder axis, X along the crank)
    "crank": shp("upper_arm", "J3Crank"),
    "crank_cap": shp("upper_arm", "J3CrankCap"),
    # forearm frame (origin on the elbow axle)
    "forearm": shp("forearm", "Forearm"),
    "elbow_axle": shp("forearm", "ElbowAxle"),
    "elbow_washers": elbow_washers(),
    # the six M4 rod pins with their nuts, each in the frame of the part it goes through:
    # A shoulder (world orientation), B/C elbow plate, D wrist fork, E crank, F forearm
    **{"pin_" + k.lower(): shp("forearm", "Pin" + k) for k in "ABCDEF"},
    # elbow plate (origin on the elbow axle, keeps its orientation)
    "elbow_plate": shp("forearm", "ElbowPlate"),
    "b609_eplate": shp("forearm", "B609_ElbowPlate"),
    # rods: along +X from pin to pin, at their own Y plane
    "rod_drive": shp("forearm", "RodDrive"),
    "rod_low": shp("forearm", "RodLevLow"),
    "rod_up": shp("forearm", "RodLevUp"),
    # wrist fork frame (origin on the wrist axle, keeps its orientation)
    "wrist_fork": shp("forearm", "WristFork"),
    "wrist_axle": shp("forearm", "WristAxle"),
    "bracket_z": shp("tools", "BracketZ"),
    "bracket_y": shp("tools", "BracketY"),
    "flange_z": shp("tools", "FlangeZ"),
    "flange_y": shp("tools", "FlangeY"),
    # clamps: own frame, tool axis Z, ring centre at 0 (axial: plate on top, side: plate on +Y)
    "clamp_axial_775": shp("tools", "ClampAxial775"),
    "clamp_axial_52": shp("tools", "ClampAxial52"),
    "clamp_side_775": shp("tools", "ClampSide775"),
    "clamp_side_52": shp("tools", "ClampSide52"),
}


def val(doc, alias):
    return D[doc].getObject("Params").get(alias).Value


geom = {
    "shoulder_z": val("upper_arm", "shoulder_z"), "L2": val("upper_arm", "len_l2"), "L3": val("forearm", "len_l3"),
    "R": val("upper_arm", "R"), "lev_v": val("forearm", "lev_v"), "lev_w": val("forearm", "lev_w"),
    "zx": val("tools", "zx"), "yx": val("tools", "yx"), "yz": val("tools", "yz"), "y_face": val("tools", "y_face"),
    "fk_drop": val("tools", "fk_drop"), "br_t": val("tools", "br_t"), "shaft_reach": val("tools", "shaft_reach"),
    "tp_t": val("tools", "tp_t"), "cl_h": val("tools", "cl_h"), "cl_wall": val("tools", "cl_wall"),
    "d775": val("tools", "d775"), "d52": val("tools", "d52"),
}
motors = {
    "J1": mat(D["base"].getObject("J1_Motor").Placement),
    "J2": mat(D["turret"].getObject("J2_Motor").Placement),
    "J3": mat(D["turret"].getObject("J3_Motor").Placement),
    "J4z": mat(D["tools"].getObject("J4_Motor_Z").Placement),
    "J4y": mat(D["tools"].getObject("J4_Motor_Y").Placement),
}
# each trip point with the cam's whole run onto the roller before it and a little overshoot after
limits = {
    "J1": lever_table("J1", [(-179.5, -163.5), (163.5, 179.5)]),
    "J2": lever_table("J2", [(ES.J2_LIM[0] - 8, ES.J2_LIM[0] + 13), (ES.J2_LIM[1] - 13, ES.J2_LIM[1] + 8)]),
    "J3": lever_table("J3", [(ES.J3_LIM[0] - 8, ES.J3_LIM[0] + 13), (ES.J3_LIM[1] - 13, ES.J3_LIM[1] + 8)]),
}
for t, Lm in limits.items():
    trips = []
    for sg in Lm["segs"]:
        on = [sg["a0"] + i * sg["step"] for i, a in enumerate(sg["lv"]) if Lm["free"] + a <= Lm["click"]]
        trips.append((min(on), max(on)) if on else None)
    print("LIMIT", t, "hinge", [round(c, 2) for c in Lm["hinge"]], "pressed", trips,
          "deepest", round(min(min(sg["lv"]) for sg in Lm["segs"]) + Lm["free"], 2), "deg from the flat")
out = {"geom": geom, "motors": motors, "limits": limits, "parts": {k: mesh(v) for k, v in parts.items()}}
path = os.path.join(HERE, "parts.js")
with open(path, "w") as fh:
    fh.write("// generated by export_parts.py from cad/*.FCStd - do not edit\n")
    fh.write("window.ARM_CAD = ")
    json.dump(out, fh, separators=(",", ":"))
    fh.write(";\n")
tris = sum(p["n"] for p in out["parts"].values())
print(f"EXPORTED {len(parts)} parts, {tris} triangles, {os.path.getsize(path) / 1e6:.1f} MB -> {path}")
print("GEOM", json.dumps(geom))
