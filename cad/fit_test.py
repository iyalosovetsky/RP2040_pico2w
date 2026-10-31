"""
fit_test.py - small coupons to check the printed fits before the big prints.

Every size comes from the same Params sheets the real parts use (pg27, base, upper_arm,
forearm), so a coupon that fits means the parts will. Builds cad/fit_test.FCStd and
  fit_test_a_motor.stl  - PG27 mount plate: boss recess, shaft clearance, 4x M3 + counterbores
  fit_test_b_hub.stl    - D-bore clamp hub on the PG27 shaft: flat 7.3 across, slit + M3 pinch,
                          M3 grub on the flat with its nut slot
  fit_test_c_seats.stl  - 608/609 seat (22x7), 6803 seat (26x5), 8 mm axle hole, M4 pin hole,
                          M3 nut trap, M3 heat insert hole
  fit_test_d_51211.stl  - ring with the 51211 seat diameter
All are laid flat for printing. Print them with the same filament and settings as the parts.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/fit_test.py --pass cad/fit_test.FCStd
"""

import os
import sys

import FreeCAD as App
import Part
import Import
import Mesh

out = os.path.abspath(next(a for a in sys.argv if a.endswith(".FCStd")))
here = os.path.dirname(out)
for f in ("pg27", "base", "upper_arm", "forearm"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
D = {n: App.getDocument(n) for n in ("pg27", "base", "upper_arm", "forearm")}
doc = App.newDocument("FitTest")
doc.saveAs(out)


def v(doc_name, alias):
    return D[doc_name].getObject("Params").get(alias).Value


V = App.Vector
ua, fa = "upper_arm", "forearm"
shaft_d, flat, d_clr = v(ua, "shaft_d"), v(ua, "flat_depth"), v(ua, "d_clr")
nut_w, nut_t, grub_d = v(ua, "nut_w"), v(ua, "nut_t"), v(ua, "grub_d")


def cyl(r, h, x=0, y=0, z=0):
    return Part.makeCylinder(r, h, V(x, y, z))


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def hexagon(across_flats, h, x, y, z):
    r = across_flats / 3 ** 0.5
    pts = [V(x + r * __import__("math").cos(a * 3.14159265 / 3), y + r * __import__("math").sin(a * 3.14159265 / 3), z)
           for a in range(7)]
    return Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, h))


def show(shape, name, label):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.Label = label
    return o


# A: plate on the PG27 face (plate on the shaft side, face at z = 0), print face-down
mc = D["pg27"].getObject("PG27_MountCut").Shape
mount_t = D["pg27"].getObject("Params").get("mount_t").Value
plate = box(-23, 23, -23, 23, 0, mount_t).cut(mc)
coupon_a = show(plate, "A_MotorPlate", "A: PG27 mount plate (bolt it to the gearbox with 4x M3x8)")

# B: clamp hub like the J2 hub / crank: D-bore along Z, slit + lugs, grub on the flat
hub_r, hub_h = 11.0, 12.0
reach, lug_t, slit = v(ua, "cl_reach"), v(ua, "cl_lug_t"), v(ua, "cl_slit")
hub = cyl(hub_r, hub_h).fuse(box(-(slit / 2 + lug_t), slit / 2 + lug_t, -reach, -hub_r + 3, 0, hub_h))
bore = cyl(shaft_d / 2 + d_clr, hub_h + 2, z=-1).cut(box(shaft_d / 2 - flat + d_clr, 10, -10, 10, -2, hub_h + 2))
slit_cut = box(-slit / 2, slit / 2, -reach - 1, -shaft_d / 2 + 0.5, -1, hub_h + 1)
yb = -(reach + hub_r) / 2 - 1.5
pinch = box(-10, 10, yb - 1.7, yb + 1.7, hub_h / 2 - 1.7, hub_h / 2 + 1.7)
head = box(slit / 2 + lug_t - 2, 10, yb - 3.1, yb + 3.1, hub_h / 2 - 3.1, hub_h / 2 + 3.1)
nut_b = hexagon(nut_w + 0.4, 3, 0, 0, 0)
nut_b.rotate(V(0, 0, 0), V(0, 1, 0), -90)
nut_b.translate(V(-(slit / 2 + lug_t) + 2.5, yb, hub_h / 2))   # 2.5 deep pocket in the -x lug, open outward
grub = box(0, hub_r + 1, -grub_d / 2, grub_d / 2, hub_h / 2 - grub_d / 2, hub_h / 2 + grub_d / 2)
grub_nut = box(shaft_d / 2 + 1.5, shaft_d / 2 + 1.5 + nut_t, -nut_w / 2, nut_w / 2, hub_h / 2 - nut_w / 2, hub_h + 1)
coupon_b = show(hub.cut(bore).cut(slit_cut).cut(pinch).cut(head).cut(nut_b).cut(grub).cut(grub_nut),
                "B_ClampHub", "B: D-bore clamp hub (slide onto the PG27 shaft)")

# C: bar with the bearing seats and the small holes, print flat
t = 8.0
b609_r = v(ua, "b609_d") / 2 + v(ua, "b609_fit")
b6803_r = v(ua, "b6803_d") / 2 + v(ua, "b6803_fit")
axle_r = v(fa, "axle_d") / 2 + v(fa, "axle_clr")
pin_r = v(fa, "pin_d") / 2
ins_r = v(fa, "ins_d") / 2
bar = box(0, 112, 0, 34, 0, t)
seats = [
    cyl(b609_r, 7.0, 17, 17, t - 7.0), cyl(6.5, t, 17, 17, -1),            # 608/609 seat + lip hole
    cyl(b6803_r, 5.0, 50, 17, t - 5.0), cyl(10.0, t, 50, 17, -1),          # 6803 seat + lip hole
    cyl(axle_r, t + 2, 76, 9, -1),                                         # 8 mm axle (clamped bores)
    cyl(pin_r, t + 2, 76, 25, -1),                                         # M4 pin
    hexagon(nut_w + 0.4, nut_t + 0.4, 92, 9, t - nut_t - 0.4), cyl(1.65, t + 2, 92, 9, -1),   # M3 nut trap
    cyl(ins_r, 6.0, 92, 25, t - 6.0),                                      # M3 heat insert
    cyl(v("forearm", "axle_d") / 2 + v("forearm", "bush_clr"), t + 2, 104, 17, -1),   # 8 mm running fit
]
c = bar
for s in seats:
    c = c.cut(s)
coupon_c = show(c, "C_Seats", "C: 22x7 and 26x5 bearing seats, 8 mm axle, M4 pin, M3 nut trap, M3 insert")

# D: ring with the 51211 seat (base roof seat diameter), 3 mm tall
seat_r = v("base", "bear_d") / 2 + v("base", "clr")
coupon_d = show(cyl(seat_r + 3, 3).cut(cyl(seat_r, 5, z=-1)), "D_Seat51211", "D: 51211 seat ring")

doc.recompute()
doc.save()

for o, stem in ((coupon_a, "fit_test_a_motor"), (coupon_b, "fit_test_b_hub"),
                (coupon_c, "fit_test_c_seats"), (coupon_d, "fit_test_d_51211")):
    s = o.Shape
    tmp = Part.show(s, "tmp_export")
    Import.export([tmp], os.path.join(here, stem + ".step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.05))
    m.write(os.path.join(here, stem + ".stl"))
    doc.removeObject(tmp.Name)
    bb = s.BoundBox
    print(f"{stem:18s} {bb.XLength:5.1f} x {bb.YLength:5.1f} x {bb.ZLength:4.1f} mm  {s.Volume / 1000:5.2f} cm3 "
          f"valid {s.isValid()} solids {len(s.Solids)}")
print(f"sizes: D-bore {shaft_d + 2 * d_clr - flat:.2f} across the flat / D{shaft_d + 2 * d_clr:.2f}, "
      f"608/609 seat D{2 * b609_r:.2f}, 6803 seat D{2 * b6803_r:.2f}, axle D{2 * axle_r:.2f}, "
      f"51211 seat D{2 * seat_r:.2f}")
