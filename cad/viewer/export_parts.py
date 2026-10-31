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
import os
import struct

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
for f in ("pg27", "base", "turret", "upper_arm", "forearm", "tools"):
    App.openDocument(os.path.join(CAD, f + ".FCStd"))
D = {n: App.getDocument(n) for n in ("pg27", "base", "turret", "upper_arm", "forearm", "tools")}
TOL = 0.3


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


parts = {
    # world (static)
    "base_housing": shp("base", "BaseHousing"),
    "bearing_51211": compound("base", ["Washer_Housing", "Washer_Shaft", "Balls"]),
    # PG27, one mesh reused for all four joints (its own frame: gearbox face at 0, shaft +Z)
    "pg27_body": shp("pg27", "Motor_NEMA17"),
    "pg27_gear": compound("pg27", ["Flange", "Gearbox", "Boss", "Gearbox_CapScrews"]),
    "pg27_shaft": compound("pg27", ["Shaft", "Circlip"]),
    # turret frame (turns with J1)
    "turret_body": shp("turret", "TurretBody"),
    "j1_hub": shp("turret", "J1Hub"),
    # upper arm frame (origin on the shoulder axis, X along the link)
    "ua_j2": shp("upper_arm", "UpperArmJ2"),
    "ua_j3": shp("upper_arm", "UpperArmJ3"),
    "ua_spacers": compound("upper_arm", ["Spacer0", "Spacer1"]),
    "ua_bush6803": shp("upper_arm", "TempBushing6803"),   # 6803 (17x26x5) or its printed stand-in
    # 609Z: elbow pair in the upper arm frame (the CAD draws them at the elbow origin), wrist in the forearm frame
    "b609_elbow": elbow_b609(),
    "b609_wrist": shp("forearm", "B609_Wrist"),
    # crank frame (origin on the shoulder axis, X along the crank)
    "crank": shp("upper_arm", "J3Crank"),
    # forearm frame (origin on the elbow axle)
    "forearm": shp("forearm", "Forearm"),
    "elbow_axle": shp("forearm", "ElbowAxle"),
    # elbow plate (origin on the elbow axle, keeps its orientation)
    "elbow_plate": shp("forearm", "ElbowPlate"),
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
out = {"geom": geom, "motors": motors, "parts": {k: mesh(v) for k, v in parts.items()}}
path = os.path.join(HERE, "parts.js")
with open(path, "w") as fh:
    fh.write("// generated by export_parts.py from cad/*.FCStd - do not edit\n")
    fh.write("window.ARM_CAD = ")
    json.dump(out, fh, separators=(",", ":"))
    fh.write(";\n")
tris = sum(p["n"] for p in out["parts"].values())
print(f"EXPORTED {len(parts)} parts, {tris} triangles, {os.path.getsize(path) / 1e6:.1f} MB -> {path}")
print("GEOM", json.dumps(geom))
