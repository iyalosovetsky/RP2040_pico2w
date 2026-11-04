"""
turret.py - parametric FreeCAD model of the turret (J1 output, carries J2 + J3).

Builds cad/turret.FCStd plus print files for its two printed parts:
  turret_body.stl/.step  - plate + two motor cheeks + levelling lug + motor cradles.
                           Print plate-down (the bearing recess opens onto the bed).
  turret_j1hub.stl/.step - hub on the J1 shaft with an anti-lift disc at the bottom,
                           held to the turret by 3x M3x20 from above into M3 nuts slid
                           into side slots in its flange. Print flange-down.
  turret_j1wedge.stl/.step - taper wedge on the shaft's flat (no play), pulled up by an
                           M3x25 from the turret top into the nut in its block. Print block-down.
  turret_j1drill_guide.stl - centring plug to drill the wedge screw hole into a turret
                           printed without it. Print collar-down.
Needs pg27.FCStd and base.FCStd in the same folder (App::Links to the motors,
their mounting cut-outs and the base for context).

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/turret.py --pass cad/turret.FCStd

Anti-lift: the 51211 only takes thrust, and with the arm reaching out (J4 + tool at
~300 mm) the overturning moment is several times what the turret's weight resists
over the bearing's ball circle (r ~36). The hub's bottom disc runs 0.2 mm under the lip
of the J1 keeper (base.FCStd, screwed to the seat floor), so the turret can't lift.
J1 play: a printed D-bore on the 8 mm D-shaft always rattles, and nothing at the hub can be
reached once the turret is on. So the hub's bore is round with a 1:10 tapered slot over the
flat; a printed wedge sits in it and an M3x25 from the turret top (on 2 mm of washers, so
its tip stays 1.3 mm above the shaft) pulls the wedge up into the taper. Pulling the hub up
to the turret (step 4) only loosens the wedge, so it's tightened last.
Assembly order:
  1. J1 into the base (4x M3x8 from above).
  2. M3 nuts into the 3 side slots of the hub flange and into the side pocket of the wedge
     block. Wedge into the hub from below (block first, up the bore), hub onto the J1 shaft
     with a fingertip under the wedge until the shaft tip carries its block. The hub rests
     on the motor screw heads for now.
  3. Both keeper halves around the hub disc, 4x M3x10 into the inserts in the seat floor
     (lift the hub a little on the shaft to get them in; the housing washer goes on after).
  4. 51211 housing washer (over the keeper foot), ball cage, shaft washer, then the turret;
     turn it until its 3 holes line up with the hub nuts and pull the hub up with 3x M3x20.
  5. M3x25 + 2 mm of washers through the turret centre into the wedge nut; tighten until J1
     has no play by hand (the taper multiplies the pull 10x - snug, not hard).
  A turret printed with blind insert pockets: drill those through Ø3.4 from below. The centre
  hole: screw the hub to the turret on the bench, push the drill guide up the hub bore from
  below and drill Ø3.4 through.

The J2/J3 motors hang 74 mm out from the cheeks on 4x M3 into the gearbox, so each one
also lies in a cradle that grows out of the plate: floor on the bed, two side walls fused
into the cheek, a saddle under the gearbox and two pads under the motor body with slots
for a cable tie over the motor (turn the motor so its connector faces up).

Frame: as base.FCStd (table z = 0, J1 = Z). Shoulder axis along Y at z = D1,
the arm's plane is X/Z. J2 bolts to the +Y cheek, J3 to the -Y cheek, both
bodies outward. Lateral stack between the cheeks (|y|):
  0..8 forearm, 10..16 upper arm plates,
  +y: 17..21 lower levelling rod, 21..26 pin boss on the J2 cheek's ear (x = lev_x)
  -y: 16.5..20.5 J3 drive rod, 21..25 J3 crank arm
The upper arm's -Y plate turns on the J3 crank hub (D18) as a plain bearing:
a 609Z can't go there because the J3 shaft has to pass through it.
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
base = App.openDocument(os.path.join(here, "base.FCStd"))
doc = App.newDocument("Turret")
doc.saveAs(out)

PARAMS = [
    ("bear_top",   "107 mm",  "51211 top (base.FCStd bear_top)"),
    ("bear_d",     "90 mm",   "51211 OD"),
    ("bear_in",    "27.5 mm", "51211 bore radius - keep the hub flange inside it"),
    ("roof_top",   "85 mm",   "base roof top (base.FCStd body_h)"),
    ("seat_h",     "3 mm",    "bearing recess depth in the turret underside"),
    ("clr",        "0.3 mm",  "printing clearance"),
    ("bear_fit",   "0.3 mm",  "51211 seat clearance (radius; fit test: 0.3 is right)"),
    ("plate_d",    "100 mm",  "turret plate (skirts the bearing)"),
    ("plate_t",    "18 mm",   "plate thickness incl. the recess"),
    ("axis_up",    "33 mm",   "shoulder axis above the plate top (PG27 flange corner r26)"),
    ("cheek_in",   "26 mm",   "cheek inner face |y|"),
    ("cheek_t",    "10 mm",   "cheek thickness (M3 counterbore + boss recess)"),
    ("cheek_r",    "28 mm",   "cheek top radius around the shoulder axis"),
    ("lug_t",      "5 mm",    "levelling lug thickness (on the +Y cheek)"),
    ("lev_x",      "=-30 mm",  "levelling offset V: lug pin X from the shoulder axis"),
    ("lug_pin_r",  "6 mm",    "radius of the cheek ear / pin boss around the rod pin"),
    ("pin_d",      "4.2 mm",  "M4 pin hole"),
    ("hub_d",      "20 mm",   "J1 hub OD (M3 heads on the roof sit at r >= 10.75)"),
    ("hub_bot",    "84 mm",   "J1 hub bottom: seat floor 82, J1 screw heads up to 82.8"),
    ("hub_disc_r", "17.5 mm", "J1 hub anti-lift disc radius (keeper wall r 18, lip r 12)"),
    ("hub_disc_t", "4 mm",    "J1 hub anti-lift disc thickness (top 88, keeper lip 88.2)"),
    ("hub_fl_d",   "44 mm",   "J1 hub flange (inside the bearing bore)"),
    ("hub_fl_t",   "8 mm",    "J1 hub flange thickness (heat inserts from the top)"),
    ("hub_scr_r",  "15 mm",   "3x M3 hub screws radius"),
    ("nut_af",     "5.6 mm",  "M3 nut pocket across flats (nut 5.5)"),
    ("nut_t",      "2.7 mm",  "M3 nut pocket height (nut 2.4)"),
    ("hub_nut_top", "2 mm",   "hub flange: plastic over the nuts (M3x20 tip at 102, nut 102.6..105)"),
    ("shaft_top",  "97.7 mm", "J1 shaft tip (base.FCStd shaft_top)"),
    ("wg_k",       "0.1",     "J1 wedge taper 1:10 (self-locking; 1 mm of lift = 0.1 mm squeeze)"),
    ("wg_t_top",   "1.4 mm",  "J1 wedge thickness level with the shaft tip"),
    ("wg_len",     "12 mm",   "J1 wedge bar below the block (shaft flat ~15 long)"),
    ("wg_lift",    "1.5 mm",  "J1 wedge block above the shaft tip at zero play (it drops onto the tip loose)"),
    ("wg_w",       "5.7 mm",  "J1 wedge width (slot 6.0, shaft flat 5.3 wide)"),
    ("wg_slot_w",  "6 mm",    "J1 wedge slot width in the hub"),
    ("wg_blk_r",   "3.9 mm",  "J1 wedge block radius (hub bore r 4.04)"),
    ("wg_floor",   "1 mm",    "J1 wedge block: floor under the nut"),
    ("wg_ceil",    "1.6 mm",  "J1 wedge block: plastic over the nut"),
    ("m3_clear",   "3.4 mm",  "M3 clearance"),
    ("m3_head_d",  "6.5 mm",  "M3 head counterbore"),
    ("m3_head_h",  "3.2 mm",  "M3 head counterbore depth"),
    ("shaft_d",    "7.98 mm", "PG27 shaft (pg27.FCStd)"),
    ("flat_depth", "0.98 mm", "D-flat depth: 7.0 mm across the flat on the 7.98 shaft (measured)"),
    ("d_clr",      "0.05 mm", "hub bore clearance (the wedge takes the play out)"),
    ("face_off",   "0 mm",    "spare: move the J2/J3 faces outward"),
    ("motor_sq",   "42.3 mm", "NEMA17 body square (pg27.FCStd)"),
    ("gb_d",       "35.9 mm", "PG27 gearbox OD (pg27.FCStd)"),
    ("cr_in",      "21.5 mm", "motor cradle: wall inner face |x| (body half-width 21.15)"),
    ("cr_wall",    "4 mm",    "motor cradle: wall thickness"),
    ("cr_floor",   "6 mm",    "motor cradle: floor thickness (on the bed with the plate)"),
    ("cr_len",     "66 mm",   "motor cradle: reach from the gearbox face (motor ends at 74)"),
    ("cr_top_off", "10 mm",   "motor cradle: wall top below the shoulder axis (keeps the connector clear)"),
    ("cr_gap",     "0.3 mm",  "motor cradle: gap under the gearbox and body - foam tape, no preload"),
    ("cr_pad1",    "42 mm",   "motor cradle: 1st body pad centre from the gearbox face"),
    ("cr_pad2",    "60 mm",   "motor cradle: 2nd body pad centre from the gearbox face"),
]

ss = doc.addObject("Spreadsheet::Sheet", "Params")
for c, t in (("A1", "parameter"), ("B1", "value"), ("C1", "note")):
    ss.set(c, t)
rows = PARAMS + [
    ("plate_bot", "=bear_top - seat_h", "turret underside"),
    ("plate_top", "=plate_bot + plate_t", "turret plate top"),
    ("shoulder_z", "=plate_top + axis_up", "shoulder axis height above the table (IK D1)"),
    ("face_y", "=cheek_in + cheek_t + face_off", "J2/J3 gearbox face |y|"),
    ("flat_x", "=shaft_d / 2 - flat_depth", "J1 shaft flat: distance from the axis"),
    ("wg_blk_bot", "=shaft_top + wg_lift", "J1 wedge block bottom (zero play)"),
    ("wg_blk_top", "=wg_blk_bot + wg_floor + nut_t + wg_ceil", "J1 wedge block top (turret underside 107)"),
    ("wg_bot", "=wg_blk_bot - wg_len", "J1 wedge bar bottom (zero play)"),
]
for i, (alias, value, note) in enumerate(rows, start=2):
    ss.set(f"A{i}", alias)
    ss.set(f"B{i}", value)
    ss.setAlias(f"B{i}", alias)
    ss.set(f"C{i}", note)
doc.recompute()

P = "Params."


def expr(o, prop, e):
    o.setExpression(prop, e)


def place(o, x="0 mm", y="0 mm", z="0 mm"):
    expr(o, ".Placement.Base.x", x)
    expr(o, ".Placement.Base.y", y)
    expr(o, ".Placement.Base.z", z)


def cyl(name, r, h, z="0 mm", x="0 mm", y="0 mm", axis=None):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", h)
    if axis == "y":            # cylinder along +Y starting at y
        o.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), -90)
    place(o, x, y, z)
    return o


def box(name, lx, ly, lz, x, y, z):
    o = doc.addObject("Part::Box", name)
    for k, v in (("Length", lx), ("Width", ly), ("Height", lz)):
        expr(o, k, v)
    place(o, x, y, z)
    return o


def taper(name, x_in, x_out_bot, x_out_top, half_w, z0, z1):
    """Prism standing on Z from z0 to z1: x from x_in to an outer face that runs
    from x_out_bot (at z0) to x_out_top (at z1), |y| <= half_w (Part::Wedge, its Y turned onto Z)."""
    o = doc.addObject("Part::Wedge", name)
    for k, v in (("Xmin", x_in), ("X2min", x_in), ("Xmax", x_out_bot), ("X2max", x_out_top),
                 ("Ymin", z0), ("Ymax", z1), ("Zmin", f"-{half_w}"), ("Z2min", f"-{half_w}"),
                 ("Zmax", half_w), ("Z2max", half_w)):
        expr(o, k, v)
    o.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
    return o


def hexagon(name, af, h, z, x="0 mm", y="0 mm", rot=0):
    """Nut pocket: hexagon across flats af, corners on the local X axis (turned rot deg about Z)."""
    o = doc.addObject("Part::Prism", name)
    o.Polygon = 6
    expr(o, "Circumradius", f"{af} / sqrt(3)")
    expr(o, "Height", h)
    o.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), rot)
    place(o, x, y, z)
    return o


def nut_slot(name, r, ang, af, h, z, out):
    """Hex pocket centred at radius r / angle ang plus a slot of width af running outward to
    radius out, so the nut slides in from the side and stops centred on the screw."""
    o = doc.addObject("Part::Box", name + "_Slot")
    expr(o, "Length", f"{out} - {r}")
    expr(o, "Width", af)
    expr(o, "Height", h)
    o.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), ang)
    place(o, f"{r} * cos({ang} deg) + {af} / 2 * sin({ang} deg)",
          f"{r} * sin({ang} deg) - {af} / 2 * cos({ang} deg)", z)
    return [hexagon(name + "_Hex", af, h, z, f"{r} * cos({ang} deg)", f"{r} * sin({ang} deg)", ang), o]


def hide(*objs):
    for o in objs:
        o.Visibility = False


def fuse(name, objs):
    o = doc.addObject("Part::MultiFuse", name)
    o.Shapes = objs
    hide(*objs)
    return o


def cut(name, b, t):
    o = doc.addObject("Part::Cut", name)
    o.Base, o.Tool = b, t
    hide(b, t)
    return o


def link(name, obj, rot_axis, rot_deg, x="0 mm", y="0 mm", z="0 mm"):
    lk = doc.addObject("App::Link", name)
    lk.LinkedObject = obj
    lk.Placement.Rotation = App.Rotation(rot_axis, rot_deg)
    place(lk, x, y, z)
    return lk


# PG27 frame: shaft along +Z. J2 shaft points -Y (X +90), J3 shaft points +Y (X -90).
X, Y = App.Vector(1, 0, 0), App.Vector(0, 1, 0)

# ---------------------------------------------------------------- body ---
plate = cyl("Plate", f"{P}plate_d / 2", f"{P}plate_t", f"{P}plate_bot")

cheek_parts = []
for side, tag in ((1, "J2"), (-1, "J3")):
    y0 = f"{P}cheek_in" if side > 0 else f"-{P}cheek_in - {P}cheek_t"
    # tombstone: block from the plate up to the axis, half-disc around the axis
    cheek_parts.append(box(f"Cheek{tag}_Block", f"2 * {P}cheek_r", f"{P}cheek_t",
                           f"{P}shoulder_z - {P}plate_top + 1 mm", f"-{P}cheek_r", y0, f"{P}plate_top - 1 mm"))
    cheek_parts.append(cyl(f"Cheek{tag}_Top", f"{P}cheek_r", f"{P}cheek_t", f"{P}shoulder_z", "0 mm", y0, axis="y"))

# levelling ground pin: the J2 cheek grows an ear back to x = lev_x (full cheek thickness) and only
# a small boss around the pin sticks inward. Nothing sits around the shoulder axis on the inner face,
# so the J2 screw-head counterbores (r 14) stay open and reachable between the cheeks.
lug_y = f"{P}cheek_in - {P}lug_t"
lug_parts = [
    box("Ear_Bar", f"-{P}lev_x", f"{P}cheek_t", f"2 * {P}lug_pin_r",
        f"{P}lev_x", f"{P}cheek_in", f"{P}shoulder_z - {P}lug_pin_r"),
    cyl("Ear_End", f"{P}lug_pin_r", f"{P}cheek_t", f"{P}shoulder_z", f"{P}lev_x", f"{P}cheek_in", axis="y"),
    cyl("Lug_Pin", f"{P}lug_pin_r", f"{P}lug_t + 0.5 mm", f"{P}shoulder_z", f"{P}lev_x", lug_y, axis="y"),
]

# motor cradles: U-channel under each J2/J3 motor, fused into the plate and the cheek
cradle_parts, cradle_cuts = [], []
for side, tag in ((1, "J2"), (-1, "J3")):
    def yspan(a, b):
        """(y origin, length) of the |y| range a..b on this side."""
        return (f"{a}" if side > 0 else f"-({b})"), f"({b}) - ({a})"

    end = f"{P}face_y + {P}cr_len"
    wall_top = f"{P}shoulder_z - {P}cr_top_off"
    pad_top = f"{P}shoulder_z - {P}motor_sq / 2 - {P}cr_gap"
    y0, ly = yspan(f"{P}cheek_in", end)
    cradle_parts.append(box(f"Cr{tag}_Floor", f"2 * ({P}cr_in + {P}cr_wall)", ly, f"{P}cr_floor",
                            f"-{P}cr_in - {P}cr_wall", y0, f"{P}plate_bot"))
    for sx, wt in ((1, "P"), (-1, "N")):
        cradle_parts.append(box(f"Cr{tag}_Wall{wt}", f"{P}cr_wall", ly, f"{wall_top} - {P}plate_bot",
                                f"{P}cr_in" if sx > 0 else f"-{P}cr_in - {P}cr_wall", y0, f"{P}plate_bot"))
    # saddle under the gearbox, seat cut below
    y0, ly = yspan(f"{P}face_y + 6 mm", f"{P}face_y + 26 mm")
    cradle_parts.append(box(f"Cr{tag}_Saddle", f"2 * {P}cr_in + 1 mm", ly,
                            f"{P}shoulder_z - 8 mm - {P}plate_bot - {P}cr_floor + 0.01 mm",
                            f"-{P}cr_in - 0.5 mm", y0, f"{P}plate_bot + {P}cr_floor - 0.01 mm"))
    cradle_cuts.append(cyl(f"Cr{tag}_Seat", f"{P}gb_d / 2 + {P}cr_gap", f"{P}cr_len",
                           f"{P}shoulder_z", "0 mm", f"{P}face_y + 0.5 mm" if side > 0 else f"-{P}face_y - {P}cr_len - 0.5 mm",
                           axis="y"))
    # two pads under the motor body, each with a cable-tie slot through both walls
    for k, c in ((1, f"{P}cr_pad1"), (2, f"{P}cr_pad2")):
        y0, ly = yspan(f"{P}face_y + {c} - 4 mm", f"{P}face_y + {c} + 4 mm")
        cradle_parts.append(box(f"Cr{tag}_Pad{k}", f"2 * {P}cr_in + 1 mm", ly,
                                f"{pad_top} - {P}plate_bot - {P}cr_floor + 0.01 mm",
                                f"-{P}cr_in - 0.5 mm", y0, f"{P}plate_bot + {P}cr_floor - 0.01 mm"))
        y0, ly = yspan(f"{P}face_y + {c} - 2.5 mm", f"{P}face_y + {c} + 2.5 mm")
        cradle_cuts.append(box(f"Cr{tag}_Tie{k}", f"2 * ({P}cr_in + {P}cr_wall) + 2 mm", ly, "2.5 mm",
                               f"-{P}cr_in - {P}cr_wall - 1 mm", y0, f"{pad_top} - 6 mm"))

body_solid = fuse("TurretSolid", [plate] + cheek_parts + lug_parts + cradle_parts)

# underside: bearing recess; motor cut-outs from pg27.FCStd; lug pin; hub screws
recess = cyl("BearingRecess", f"{P}bear_d / 2 + {P}bear_fit", f"{P}seat_h + 0.01 mm", f"{P}plate_bot - 0.01 mm")
mc_j2 = link("J2_MountCut", pg.getObject("PG27_MountCut"), X, 90, "0 mm", f"{P}face_y", f"{P}shoulder_z")
mc_j3 = link("J3_MountCut", pg.getObject("PG27_MountCut"), X, -90, "0 mm", f"-{P}face_y", f"{P}shoulder_z")
lug_pin = cyl("LugPin", f"{P}pin_d / 2", f"{P}lug_t + {P}cheek_t + 2 mm", f"{P}shoulder_z", f"{P}lev_x",
              f"{P}cheek_in - {P}lug_t - 1 mm", axis="y")
# hub screws come from above (M3x20, head on the plate top) so the hub can go on before the turret
inserts = [cyl(f"HubScrewHole{k}", f"{P}m3_clear / 2", f"{P}plate_t + 1 mm", f"{P}bear_top - 0.5 mm",
               f"{P}hub_scr_r * cos({90 + 120 * k} deg)", f"{P}hub_scr_r * sin({90 + 120 * k} deg)")
           for k in range(3)]
inserts.append(cyl("WedgeScrewHole", f"{P}m3_clear / 2", f"{P}plate_t + 1 mm", f"{P}bear_top - 0.5 mm"))
tools = fuse("TurretTools", [recess, mc_j2, mc_j3, lug_pin] + inserts + cradle_cuts)
turret = cut("TurretBody", body_solid, tools)
turret.Label = "Turret body (print)"

# ------------------------------------------------------------- J1 hub ---
# Round bore + a tapered slot over the shaft's flat holding the J1 wedge: the wedge's inner face
# lies on the flat, its outer face on the slot's 1:10 incline, which narrows upward. A screw from
# the turret top pulls the wedge up by its block (over the shaft tip), squeezing the flat - no play,
# and re-tightenable from above. The 3 turret screws go into M3 nuts slid into side slots in the
# flange (a nut under plastic can't pull out the way a heat insert on the face did).
def x_out(z):
    """the slot's incline at height z (zero play)"""
    return f"({P}flat_x + {P}wg_t_top - (({z}) - {P}shaft_top) * {P}wg_k)"


hub_fl = cyl("HubFlange", f"{P}hub_fl_d / 2", f"{P}hub_fl_t", f"{P}bear_top - {P}hub_fl_t")
hub_tube = cyl("HubTube", f"{P}hub_d / 2", f"{P}bear_top - {P}hub_fl_t - {P}hub_bot + 0.01 mm", f"{P}hub_bot")
hub_disc = cyl("HubDisc", f"{P}hub_disc_r", f"{P}hub_disc_t", f"{P}hub_bot")
hub_solid = fuse("HubSolid", [hub_fl, hub_tube, hub_disc])
bore = cyl("HubBore", f"{P}shaft_d / 2 + {P}d_clr", f"{P}bear_top - {P}hub_bot + 1 mm", f"{P}hub_bot - 0.5 mm")
z0, z1 = f"{P}hub_bot - 1 mm", f"{P}bear_top + 1 mm"
wslot = taper("HubWedgeSlot", f"{P}flat_x - 0.2 mm", x_out(z0), x_out(z1), f"{P}wg_slot_w / 2", z0, z1)
hub_holes = [bore, wslot]
nut_z = f"{P}bear_top - {P}hub_nut_top - {P}nut_t"
for k in range(3):
    ang = 90 + 120 * k
    x, y = f"{P}hub_scr_r * cos({ang} deg)", f"{P}hub_scr_r * sin({ang} deg)"
    hub_holes.append(cyl(f"HubScrew{k}", f"{P}m3_clear / 2", f"{P}hub_fl_t + 1 mm",
                         f"{P}bear_top - {P}hub_fl_t - 0.5 mm", x, y))
    hub_holes += nut_slot(f"HubNut{k}", f"{P}hub_scr_r", ang, f"{P}nut_af", f"{P}nut_t", nut_z,
                          f"{P}hub_fl_d / 2 + 1 mm")
hub = cut("J1Hub", hub_solid, fuse("HubTools", hub_holes))
hub.Label = "J1 hub (print)"

# the wedge, shown at zero play: bar on the flat + block over the shaft tip with a side-loaded M3 nut
c = "0.02 mm"
wg_bar = taper("WedgeBar", f"{P}flat_x + {c}", f"{x_out(P + 'wg_bot')} - {c}", f"{x_out(P + 'wg_blk_top')} - {c}",
               f"{P}wg_w / 2", f"{P}wg_bot", f"{P}wg_blk_top")
wg_cyl = cyl("WedgeBlockCyl", f"{P}wg_blk_r", f"{P}wg_blk_top - {P}wg_blk_bot", f"{P}wg_blk_bot")
wg_trim = taper("WedgeBlockTrim", "-10 mm", f"{x_out(P + 'wg_blk_bot')} - {c}", f"{x_out(P + 'wg_blk_top')} - {c}",
                "10 mm", f"{P}wg_blk_bot", f"{P}wg_blk_top")
wg_blk = doc.addObject("Part::MultiCommon", "WedgeBlock")
wg_blk.Shapes = [wg_cyl, wg_trim]
hide(wg_cyl, wg_trim)
wg_nut_z = f"{P}wg_blk_bot + {P}wg_floor"
wg_cuts = [hexagon("WedgeNut_Hex", f"{P}nut_af", f"{P}nut_t", wg_nut_z),
           box("WedgeNut_Slot", "10 mm", f"{P}nut_af", f"{P}nut_t", "-10 mm", f"-{P}nut_af / 2", wg_nut_z),
           cyl("WedgeScrew", f"{P}m3_clear / 2", f"{P}wg_blk_top - {P}wg_blk_bot + 1 mm", f"{P}wg_blk_bot - 0.5 mm")]
wedge = cut("J1Wedge", fuse("WedgeSolid", [wg_bar, wg_blk]), fuse("WedgeTools", wg_cuts))
wedge.Label = "J1 wedge (print block-down)"

# centring plug for drilling the wedge screw hole through an already printed turret: hub screwed
# to the turret on the bench, plug pushed up the hub bore from below, drill through it (not assembled)
guide = cut("J1DrillGuide",
            fuse("GuideSolid", [cyl("GuidePlug", f"{P}shaft_d / 2 + {P}d_clr - 0.1 mm", "22 mm", "-58 mm"),
                                cyl("GuideCollar", "7 mm", "2 mm", "-60 mm")]),
            cyl("GuideHole", f"{P}m3_clear / 2", "26 mm", "-61 mm"))
guide.Label = "Drill guide for the wedge screw hole (print collar-down)"
hide(guide)   # parked under the table, out of the assembly

# screw heads on the plate top (context + interference sweeps of the arm): 3x M3x20 into the hub
# nuts, and the wedge screw M3x25 on 2 mm of washers in the middle
hub_heads = fuse("J1HubScrews", [cyl(f"HubScrewHead{k}", "2.75 mm", "3 mm", f"{P}plate_top",
                                     f"{P}hub_scr_r * cos({90 + 120 * k} deg)",
                                     f"{P}hub_scr_r * sin({90 + 120 * k} deg)") for k in range(3)]
                 + [cyl("WedgeWashers", "3.5 mm", "2 mm", f"{P}plate_top"),
                    cyl("WedgeScrewHead", "2.75 mm", "3 mm", f"{P}plate_top + 2 mm")])
hub_heads.Label = "J1 screws: 3x M3x20 (hub), M3x25 + 2 mm washers (wedge)"

# ------------------------------------------------- motors and context ---
j2 = link("J2_Motor", pg.getObject("PG27"), X, 90, "0 mm", f"{P}face_y", f"{P}shoulder_z")
j3 = link("J3_Motor", pg.getObject("PG27"), X, -90, "0 mm", f"-{P}face_y", f"{P}shoulder_z")
j2.Label, j3.Label = "J2 - 17HS15-1684S-PG27 (shoulder)", "J3 - 17HS15-1684S-PG27 (forearm crank)"
ctx = doc.addObject("App::DocumentObjectGroup", "Base_context")
for n in ("BaseHousing", "Bearing_51211", "J1_Motor", "J1Keeper"):
    c = link("Ctx_" + n, base.getObject(n), X, 0)
    c.LinkTransform = True  # keep the target's own placement (J1_Motor is itself a placed link)
    ctx.addObject(c)

doc.recompute()
bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
if bad:
    sys.exit(f"recompute failed: {bad}")
doc.save()

for part, stem in ((turret, "turret_body"), (hub, "turret_j1hub"), (wedge, "turret_j1wedge"),
                   (guide, "turret_j1drill_guide")):
    Import.export([part], os.path.join(here, stem + ".step"))
    Mesh.export([part], os.path.join(here, stem + ".stl"))

print("shoulder_z (IK D1) =", ss.get("shoulder_z"), " face_y =", ss.get("face_y"))
for o in (turret, hub, wedge, guide):
    s = o.Shape
    print(f"{o.Name:10s} vol {s.Volume / 1000:6.1f} cm3 valid {s.isValid()} solids {len(s.Solids)} bb {s.BoundBox}")


def overlap(a, b):
    return round(a.Shape.common(b.Shape).Volume, 2)


ctx_objs = {o.LinkedObject.Name: o for o in ctx.Group}
for a, b in ((turret, j2), (turret, j3), (turret, hub), (turret, ctx_objs["Bearing_51211"]),
             (turret, ctx_objs["BaseHousing"]), (hub, ctx_objs["J1_Motor"]),
             (hub, ctx_objs["BaseHousing"]), (hub, ctx_objs["Bearing_51211"]), (hub, ctx_objs["J1Keeper"]),
             (turret, ctx_objs["J1Keeper"]), (hub_heads, j2), (hub_heads, j3),
             (wedge, hub), (wedge, turret), (wedge, ctx_objs["J1_Motor"])):
    print(f"overlap {a.Name} / {b.Label}: {overlap(a, b)} mm3")
