"""
check_nuts.py - puts an M3 nut (5.5 across flats, 2.4 thick) on the screw axis of every nut pocket
and reports whether it fits there, whether it can get there from the pocket's opening, and whether
the pocket stops it turning. Run after the stage scripts:
    <FreeCAD.AppImage> freecadcmd cad/check_nuts.py
A line ending in <<<<< is a pocket to look at. The tie's four lines show 0.2 mm3: its slots stop
0.3 mm short of a nut corner; the ties are printed and work, so they stay as they are.
"""
import math, os, sys, FreeCAD as App, Part
C = os.path.dirname(os.path.abspath(next(a for a in sys.argv if a.endswith("check_nuts.py"))))
sys.path.insert(0, C)
import endstop_dims as ES
V = App.Vector
AX = {"x": V(1, 0, 0), "y": V(0, 1, 0), "z": V(0, 0, 1)}

def nut(c, axis, ang, af=5.5, t=2.4):
    R = af / 2 / math.cos(math.radians(30))
    pts = [V(R * math.cos(math.radians(60 * k + ang)), R * math.sin(math.radians(60 * k + ang)), -t / 2) for k in range(7)]
    n = Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, t))
    if axis == "x":
        n.rotate(V(0, 0, 0), V(0, 1, 0), 90)
    elif axis == "y":
        n.rotate(V(0, 0, 0), V(1, 0, 0), 90)
    n.translate(c)
    return n

def check(tag, part, c, axis, ins, travel=14):
    """nut on the screw axis at c (axis = thread direction), ins = direction it is pushed in from"""
    vols = [(part.common(nut(c, axis, a)).Volume, a) for a in range(0, 60, 5)]
    vmin, abest = min(vols)
    spins = max(vols)[0] < 0.01
    path = 0.0
    if vmin < 0.01:
        d = V(*ins); d.normalize()
        path = max(part.common(nut(c + d * (-k * 0.5), axis, abest)).Volume for k in range(1, int(travel * 2)))
    ok = vmin < 0.01 and path < 0.01 and not spins
    print("NUT %-34s seat %s  way in %s  held %s   %s" % (
        tag, "ok" if vmin < 0.01 else "BLOCKED %.1f mm3" % vmin,
        "ok" if path < 0.01 else "BLOCKED %.1f mm3" % path, "no - SPINS" if spins else "yes", "" if ok else "<<<<<"))

def axis_point(doc, hole, pocket):
    b = doc.getObject(hole).Shape.common(doc.getObject(pocket).Shape).BoundBox
    return V((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, (b.ZMin + b.ZMax) / 2), doc.getObject(pocket).Shape.BoundBox

docs = {n: App.openDocument("%s/%s.FCStd" % (C, n)) for n in ("pg27", "base", "turret", "upper_arm", "forearm", "tools", "limits")}
fa, tl, lim, ua = docs["forearm"], docs["tools"], docs["limits"], docs["upper_arm"]

# J1 hub: the grub nut (thread along x, slid in from +y) and the 3 flange nuts (slid in radially)
tu = docs["turret"]; tq = tu.getObject("Params"); hub = tu.getObject("J1Hub").Shape
check("J1 hub grub", hub, V(tq.grub_nut_x.Value + tq.nut_t.Value / 2, 0, tq.grub_z.Value), "x", (0, -1, 0))
hz = tq.bear_top.Value - tq.hub_nut_top.Value - tq.nut_t.Value / 2
for k in range(3):
    a = math.radians(90 + 120 * k)
    check("J1 hub flange %d" % k, hub, V(tq.hub_scr_r.Value * math.cos(a), tq.hub_scr_r.Value * math.sin(a), hz), "z",
          (-math.cos(a), -math.sin(a), 0), travel=8)

# forearm and wrist fork: grub nut slots (thread along z, pushed in along y from the open face)
for tag, part, h, p in (("forearm elbow grub", "Forearm", "FA_Grub_H", "FA_Grub_N"), ("wrist fork grub", "WristFork", "FK_Grub_H", "FK_Grub_N")):
    c, pb = axis_point(fa, h, p)
    sh = fa.getObject(part).Shape
    opn = 1 if abs(pb.YMax - c.y) > abs(pb.YMin - c.y) else -1
    print("    %s: slot x %.2f wide, z %.2f thick, y %.2f..%.2f, screw axis y %.2f" % (tag, pb.XLength, pb.ZLength, pb.YMin, pb.YMax, c.y))
    check(tag, sh, c, "z", (0, -opn, 0))
# tool flanges
for tag, part, h, p, ax in (("flange_z grub", "FlangeZ", "FZ_Grub", "FZ_Nut", "x"), ("flange_y grub", "FlangeY", "FY_Grub", "FY_Nut", "x")):
    c, pb = axis_point(tl, h, p)
    sh = tl.getObject(part).Shape
    ext = {"y": (pb.YMin, pb.YMax, c.y), "z": (pb.ZMin, pb.ZMax, c.z)}
    k, (lo, hi, cc) = max(ext.items(), key=lambda kv: kv[1][1] - kv[1][0])
    opn = 1 if hi - cc > cc - lo else -1
    d = (0, -opn, 0) if k == "y" else (0, 0, -opn)
    print("    %s: slot %.2f x %.2f x %.2f, opens along %s%s" % (tag, pb.XLength, pb.YLength, pb.ZLength, "+" if opn > 0 else "-", k))
    check(tag, sh, c, ax, d)
# upper arm: the ties (printed already - for reference)
for k in range(1):
    s = ua.getObject("Spacer%d" % k).Shape
    for j, z in enumerate((8, -8)):
        for t in ("P", "N"):
            c, pb = axis_point(ua, "TieHole%d_%d" % (k, j), "TieNut%d_%d%s" % (k, j, t))
            check("tie nut %s%d" % (t, j), s, c, "y", (0, 0, -1 if z > 0 else 1))
# limits: positions from the same numbers limits.py uses
tp = docs["turret"].getObject("Params"); bp = docs["base"].getObject("Params")
TOP, SH_Z = tp.plate_top.Value, tp.shoulder_z.Value
HR, BODY_H = bp.body_od.Value / 2, bp.body_h.Value
X_END = ES.TIP_END + ES.BOARD_L
Y2, Y3 = ES.J2_FACE - ES.STANDOFF, ES.J3_FACE + ES.STANDOFF
MIR = Y2 + Y3
plate = lim.getObject("LimitPlate").Shape
zc = TOP + 2.5 + 2.9 / 2
for hx, hy in ES.HOLES:
    for adj in (ES.ADJ[0], 0, ES.ADJ[1]):
        x, y = hx - X_END, Y2 - (hy + adj)
        check("limit_plate J2 hole %g adj %+g" % (hx, adj), plate, V(x, y, zc), "z", (0, -1, 0))
        check("limit_plate J3 hole %g adj %+g" % (hx, adj), plate, V(-x, MIR - y, zc), "z", (0, 1, 0))
FX = -(ES.J1_FLAG_R[0] + ES.J1_FLAG_R[1]) / 2
check("limit_plate flag nut (under arm)", plate, V(FX, 0, TOP + 1.4), "z", (0, 0, 1))
cf, cr = lim.getObject("LimitCollarFront").Shape, lim.getObject("LimitCollarRear").Shape
SEAT_X = ES.J1_PCB_X - ES.BOARD_T
Y0 = ES.J1_HINGE_Y - ES.LEV_HINGE_X
for hx, hy in ES.HOLES:
    for adj in (ES.ADJ[0], 0, ES.ADJ[1]):
        check("collar front hole %g adj %+g" % (hx, adj), cf, V(SEAT_X - 2.0 - 2.9 / 2, Y0 + hx, ES.J1_EDGE - hy - adj), "x", (0, 0, -1))
CZ1 = BODY_H - 1.0; CZ0 = CZ1 - ES.J1_COLLAR_H
for sg in (1, -1):
    for z in ES.J1_COLLAR_SCR_Z:
        check("collar rear ear %+d z %g" % (sg, z), cr, V(-5.2 - 1.3, sg * (HR + 8.5), z), "x", (1, 0, 0), travel=6)
    check("collar rear SKR pad %+d" % sg, cr, V(-ES.SKR_PAD_X + 4.7, sg * ES.SKR_SCR_Y, ES.SKR_SCR_Z), "x", (0, 0, -1), travel=10)
