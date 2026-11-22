"""
limits.py - limit switches for J2 and J3: the two switch boards and the printed bracket
that carries them on the turret, plus the checks that the fingers work them.

Builds cad/limits.FCStd and the print files
  limit_plate.stl/.step  - bracket on the turret plate between the cheeks, with an arm out over
                           the plate's rear edge for the J1 flag. Print flat, no supports.
  limit_flag.stl/.step   - J1 flag: a saddle that slides onto the end of that arm, M3x12 + nut.
                           Print on its outer face.
  limit_collar_front.stl - half collar round the base housing with the seat for the J1 board,
  limit_collar_rear.stl  - the other half with the pad for the SKR Pico's plate (electronics.py);
                           4x M3x20 + nuts pull them together. Print both as modelled.
  limit_rocker.stl       - the rocker between a finger and a switch lever, 2 of them (J1, J2);
  limit_rocker_j3.stl    - J3's, its nose 1.5 mm nearer the pin. Print on the flat underside.
  limit_cover.stl        - flat cover over each switch and its rocker, 3 of them; held by the board's
                           screw in hole 17, the rocker's pin and stop under it. Print top face down,
                           the boss, pin and stop up.
Needs upper_arm.FCStd (and the files it uses) in the same folder; endstop_dims.py holds the
board's dimensions and the installation numbers, read that first.

Run headless:
    <FreeCAD.AppImage> freecadcmd cad/limits.py --pass cad/limits.FCStd

Layout (turret frame, shoulder axis along Y at z = shoulder_z): both boards lie flat, parts up,
24 mm under the axis - below everything that turns there. J2's board is behind the J1 axis with
its lever edge to +y; the fingers on the J2-side plate (y 9..12) pass 6.7 mm from that edge.
J3's board is the same thing turned half a turn: in front, lever edge to -y, worked by the fingers
on the crank's root ring (y -20.5..-25.5). One switch per joint trips at both ends of travel.
J1's board stands on a collar clamped round the base housing (z 44..84), lever edge up;
the flag hangs from the bracket's arm behind the turret and passes 6.7 mm over that edge.
No finger touches a lever: each one runs onto the V nose of a rocker that lies along the lever
edge on a pin and presses the middle of the lever with its rib (endstop_dims.py says why).

Fitting:
  1. Take out the two hub screws at the front (x = +-13, y = -7.5), put the bracket down between
     the cheeks and put the screws back as M3x25 (the M3x20 ones are 1.5 mm short now). The third
     hub screw stays as it is.
     Before that: an M3 nut into each of the four pockets in the bracket's underside (they hold it by
     its flats; the turret plate keeps it in).
  2. The boards on the seats, parts up. Hole 36: M3x8 (not longer: a longer one stands on the turret
     plate before it is tight). A rocker on the floor beside each board, nose out, its hole over the
     slot; the cover on top, its pin down through the rocker's hole into the slot, its boss on the
     PCB; M3x16 through the cover in hole 17. Loose. (J3 gets limit_rocker_j3.)
  3. Arm on. Turn the joint by hand until a finger sits on the flat top of the rocker's nose. Slide
     the board away from the finger until the LED goes out, then back until it comes on, then 0.5 mm
     more; tighten. Turn the finger off the nose: the LED must go out (if not, the board is too
     close - move it 0.3 mm away).
  4. Leave 0.5 mm between the crank and the J3 cheek when clamping the crank: the fingers pass
     0.9 mm from the board seats.
  5. J1: flag onto the arm's end from behind (M3x12 down into the nut under the arm). The two collar
     halves round the housing with their tops 1 mm under its top edge, 4x M3x20 + nuts. Then the
     board on the front half: nuts dropped into the channels from above, M3x8 in hole 36; the rocker
     on the floor above the board, the cover's pin through it, M3x16 through the cover in hole 17. Turn the collar until the board
     is opposite the flag with the arm pointing where "straight ahead" should be, set the board's
     height the same way as in 3, tighten everything.
"""

import math
import os
import sys

import FreeCAD as App
import Part
import Import
import Mesh

out = os.path.abspath(next(a for a in sys.argv if a.endswith(".FCStd")))
here = os.path.dirname(out)
sys.path.insert(0, here)
import endstop_dims as ES  # noqa: E402

for f in ("pg27", "base", "turret", "upper_arm"):
    App.openDocument(os.path.join(here, f + ".FCStd"))
tur, ua, bas = App.getDocument("turret"), App.getDocument("upper_arm"), App.getDocument("base")
doc = App.newDocument("Limits")
doc.saveAs(out)
V = App.Vector

tp = tur.getObject("Params")
SH_Z = tp.shoulder_z.Value            # shoulder axis
TOP = tp.plate_top.Value              # turret plate top
CHEEK = tp.cheek_in.Value             # cheek inner faces |y|
HUB_R = tp.hub_scr_r.Value
HR = bas.getObject("Params").body_od.Value / 2   # base housing radius
BODY_H = bas.getObject("Params").body_h.Value    # its top
PCB_TOP = SH_Z - ES.PCB_DEPTH
SEAT = PCB_TOP - ES.BOARD_T           # the boards rest on this
BASE_T, POCKET = 2.5, 1.0             # bracket floor; depth of the pockets under the two hub screw heads
CH_W, CH_H = 5.9, 2.9                 # nut channel: holds the nut by its flats (5.5), so it cannot turn
NUT_TOP, NUT_C = 3.4, 3.4             # board nut pockets: open underneath, this deep; nut corner + clearance
SLOT_W = 3.3
X_END = ES.TIP_END + ES.BOARD_L       # the boards' connector end, |x|
Y2 = ES.J2_FACE - ES.STANDOFF         # J2 board's lever edge
Y3 = ES.J3_FACE + ES.STANDOFF         # J3 board's lever edge
MIRROR_Y = Y2 + Y3                    # the J3 side is the J2 side turned half a turn about (0, MIRROR_Y / 2)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def show(name, shape, label):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.Label = label
    return o


# ------------------------------------------------------------ the board ---
# built in the photo's frame: x along the board, lever edge at y = 0 with the board at y < 0, z up
def board_parts(xc):
    L, W = ES.BOARD_L, ES.BOARD_W
    pcb = box(0, L, -W, 0, -ES.BOARD_T, 0)
    for hx, hy in ES.HOLES + ((2.0, 2.7), (2.0, W - 2.7)):
        pcb = pcb.cut(cyl(ES.HOLE_D / 2, hx, -hy, -ES.BOARD_T - 1, 1))
    x0, x1, y0, y1, h = ES.SW
    sw = box(x0, x1, -y1, -y0, 0, h)
    cx0, cx1, cy0, cy1, ch = ES.CONN
    conn = box(cx0, cx1, -cy1, -cy0, 0, ch)
    # keep-outs for the checks only: the plug with its lead, the solder joints underneath
    plug = box(cx0, cx1, -cy1, -cy0, ch, ES.PLUG_H)
    solder = box(x0, x1, -ES.TERM_Y - 3, -ES.TERM_Y, -ES.BOARD_T - ES.SOLDER, -ES.BOARD_T).fuse(
        box(cx0, cx1, -cy1, -cy0, -ES.BOARD_T - ES.SOLDER, -ES.BOARD_T))
    ar, ac = ES.SL_REST_ANG, ES.sl_click_ang(xc)
    rest, pressed = rocker(xc, ar), rocker(xc, 0)
    # a finger still reaching into the rocker turned out to where it clicks has turned it further: clicked
    probe = rocker(xc, ac).common(box(xc - 10, xc + 10, ES.STANDOFF, ES.STANDOFF + 10, -1, 10))
    return {"pcb": pcb, "sw": sw, "lever": lever(xc, ar), "lever_in": lever(xc, 0), "conn": conn, "plug": plug,
            "solder": solder, "probe": probe, "slider": rest, "slider_in": pressed, "cover": cover()}


def turn(shape, ang):
    """turned ang deg out (counterclockwise) about the rocker's pin"""
    s = shape.copy()
    s.rotate(V(ES.SL_PIVOT[0], ES.SL_PIVOT[1], 0), V(0, 0, 1), ang)
    return s


def rocker(xc, ang):
    """the rocker with its nose at board x xc, turned ang deg out from square (square: a finger on the nose flat)"""
    (px, py), hw, z0, zn, z1 = ES.SL_PIVOT, ES.SL_HW, ES.SL_Z0, ES.SL_ZN, ES.SL_Z1
    b = ES.SL_PRESSED
    y1 = b + ES.SL_RIB                       # the bar's back
    yn = y1 + ES.SL_BAR                      # its front: the nose's base
    f = ES.SL_FLAT / 2
    pts = [V(xc - hw, yn - 0.01, z0), V(xc + hw, yn - 0.01, z0), V(xc + f, yn + ES.SL_NOSE, z0), V(xc - f, yn + ES.SL_NOSE, z0)]
    nose = Part.Face(Part.makePolygon(pts + pts[:1])).extrude(V(0, 0, zn - z0))
    s = box(px, xc + hw, y1, yn, z0, z1).fuse([
        nose, cyl(ES.SL_BOSS_R, px, py, z0, z1),
        box(xc - ES.SL_RIB_W / 2, xc + ES.SL_RIB_W / 2, b, y1 + 0.01, z0, z1)])
    s = s.cut(cyl(ES.SL_HOLE_D / 2, px, py, z0 - 1, z1 + 1)).removeSplitter()
    return turn(s, ang)


def lever(xc, ang):
    """the switch lever lying on the rib of a rocker turned ang deg out: a strip hinged at LEV_HINGE_X, its outer face on
    the line to the rib, with the hook (a round LEV_HOOK_R proud of that line) at its end"""
    r = turn(Part.Vertex(V(xc, ES.SL_PRESSED, 0)), ang).Point
    hx, hy = ES.LEV_HINGE_X, ES.LEV_HINGE_OUT
    phi = math.atan2(r.y - 0.15 - hy, r.x - hx)
    n = (ES.LEV_HOOK_X - hx) / math.cos(phi)
    s = box(0, n, -0.3, 0, ES.LEV_Z0, ES.LEV_Z1).fuse(cyl(ES.LEV_HOOK_R, n, 0, ES.LEV_Z0, ES.LEV_Z1))
    s.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(phi))
    s.translate(V(hx, hy, 0))
    return s.removeSplitter()


def cover():
    """flat plate over the switch and the rocker, a boss down to the PCB on hole 17 (board frame); under it the rocker's
    pin, down into the bracket's floor, and the stop that holds the rocker at rest. Printed top face down, the boss,
    pin and stop up"""
    (x0, x1), (z0, z1), y0 = ES.COVER_X, ES.COVER_Z, ES.COVER_Y0
    px, py = ES.SL_PIVOT
    c = box(x0, x1, y0, ES.STANDOFF - 0.5, z0, z1)
    hx, hy = ES.HOLES[0]
    stop = box(px + ES.COVER_STOP_X[0], px + ES.COVER_STOP_X[1], 3.8, ES.STANDOFF - 0.5, 1.0, z0 + 0.01)
    stop = stop.cut(rocker(ES.SL_XC, ES.SL_REST_ANG))
    c = c.fuse([cyl(ES.COVER_BOSS_D / 2, hx, -hy, 0, z0 + 0.01), cyl(ES.SL_PIN_D / 2, px, py, -1.0, z0 + 0.01), stop])
    c = c.cut(cyl(1.7, hx, -hy, -1, z1 + 1))
    return c.removeSplitter()


def guide(zb, xc):
    """the floor under a rocker (board frame, from zb up to SL_FLOOR) and the slot in it for the cover's pin, which
    lets the board be set across its lever edge. Nothing stands beside the lever"""
    px, py = ES.SL_PIVOT
    block = box(px - 3.4, xc + ES.SL_HW + 0.6, 0.6, ES.STANDOFF - 0.5, zb, ES.SL_FLOOR)
    r = ES.SL_PIN_D / 2 + 0.2
    slot = box(px - r, px + r, py - r - 1.2, ES.STANDOFF + 1, -1.5, ES.SL_FLOOR + 1)
    return block.cut(slot), slot


def place(shape, j3):
    s = shape.copy()
    if j3:   # half a turn about Z
        s.rotate(V(0, 0, 0), V(0, 0, 1), 180)
        s.translate(V(X_END + ES.J3_SHIFT, Y3, PCB_TOP))
    else:
        s.translate(V(-X_END, Y2, PCB_TOP))
    return s


bp = board_parts(ES.SL_XC)
bp3 = board_parts(ES.SL_XC + ES.J3_SHIFT)     # J3's nose sits where J2's is mirrored, so nearer its pin
boards = {}
for tag, j3 in (("J2", False), ("J3", True)):
    boards[tag] = {k: place(v, j3) for k, v in (bp3 if j3 else bp).items()}
    o = show(f"Endstop{tag}", Part.makeCompound([boards[tag][k] for k in ("pcb", "sw", "lever", "conn")]),
             f"{tag} limit switch board (bought)")

# J1: board upright in front of the J1 axis - board x -> +y, its lever edge up, parts to +x
Y0_J1 = ES.J1_HINGE_Y - ES.LEV_HINGE_X
M_J1 = App.Matrix(0, 0, 1, ES.J1_PCB_X, 1, 0, 0, Y0_J1, 0, 1, 0, ES.J1_EDGE, 0, 0, 0, 1)
boards["J1"] = {k: v.transformGeometry(M_J1) for k, v in bp.items()}
show("EndstopJ1", Part.makeCompound([boards["J1"][k] for k in ("pcb", "sw", "lever", "conn")]),
     "J1 limit switch board (bought)")
for tag in boards:
    show(f"Slider{tag}", boards[tag]["slider"], f"{tag} limit switch rocker (print, limit_rocker{'_j3' if tag == 'J3' else ''}.stl)")
    show(f"Cover{tag}", boards[tag]["cover"], f"{tag} limit switch cover (print, limit_cover.stl)")

# ---------------------------------------------------------- the bracket ---
def half(sgn):
    """Seat block, nut pockets, slots and the rest pad of the J2 board (sgn = 1); the J3 side
    is that turned half a turn. The nuts go into pockets in the bracket's underside before it goes
    on the turret (the turret plate then holds them in); they slide along with the screw when the
    board is set, and the flats stop them turning. M3x8 reaches 2 mm into the nut; a longer screw
    only meets the turret plate."""
    def bx(x0, x1, y0, y1, z0, z1):
        if sgn > 0:
            return box(x0, x1, y0, y1, z0, z1)
        return box(-x1 + ES.J3_SHIFT, -x0 + ES.J3_SHIFT, MIRROR_Y - y1, MIRROR_Y - y0, z0, z1)

    xb = lambda x: x - X_END              # board x -> turret x  # noqa: E731
    yb = lambda y: Y2 - y                 # board y -> turret y  # noqa: E731
    block = bx(xb(13.0), xb(ES.BOARD_L), yb(ES.TERM_Y - 0.7), yb(-1.6), TOP + BASE_T - 0.01, SEAT)
    pad = bx(xb(0.3), xb(2.8), yb(ES.BOARD_W - 1.0), yb(1.0), TOP + BASE_T - 0.01, SEAT)
    solids, cuts = [block, pad], []
    for hx, hy in ES.HOLES:
        y0, y1 = yb(hy + ES.ADJ[1]) - NUT_C, yb(hy + ES.ADJ[0]) + NUT_C       # the nut's travel, corners along y
        # roof over the pocket where it runs out from under the seat block (towards the solder side)
        solids.append(bx(xb(hx) - CH_W / 2 - 1.5, xb(hx) + CH_W / 2 + 1.5, y0 - 1.2, yb(ES.TERM_Y - 0.7) + 0.01,
                         TOP + BASE_T - 0.01, TOP + NUT_TOP + 1.2))
        cuts.append(bx(xb(hx) - CH_W / 2, xb(hx) + CH_W / 2, y0, y1, TOP - 1, TOP + NUT_TOP))
        # slot: the screw can move ADJ[0] towards the finger (-y on the board) and ADJ[1] away
        cuts.append(bx(xb(hx) - SLOT_W / 2, xb(hx) + SLOT_W / 2, yb(hy + ES.ADJ[1]) - SLOT_W / 2,
                       yb(hy + ES.ADJ[0]) + SLOT_W / 2, TOP + NUT_TOP - 0.5, SEAT + 1))
    return solids, cuts


z0, z1 = TOP, TOP + BASE_T
solids = [box(-20, 20, -CHEEK + 0.2, CHEEK - 0.2, z0, z1),                    # between the cheeks: locates it in y
          box(-X_END - 0.6, -20 + 0.01, Y2 - ES.BOARD_W - 0.6, Y2 + 1.6, z0, z1),          # tongue under the J2 board
          box(20 - 0.01, X_END + ES.J3_SHIFT + 0.6, Y3 - 1.6, Y3 + ES.BOARD_W + 0.6, z0, z1)]  # tongue under the J3 board
cuts = [cyl(4.5, 0, 0, z0 - 1, SEAT + 1)]                                      # over the turret's centre hole (old wedge screw)
for k in range(3):
    a = math.radians(90 + 120 * k)
    x, y = HUB_R * math.cos(a), HUB_R * math.sin(a)
    if y > 0:
        cuts.append(cyl(4.5, x, y, z0 - 1, z1 + 1))                            # this hub screw stays on the turret
    else:
        cuts += [cyl(1.7, x, y, z0 - 1, z1 + 1), cyl(3.5, x, y, z1 - POCKET, SEAT + 1)]   # head: room up through the seat block
for sgn in (1, -1):
    s, c = half(sgn)
    solids += s
    cuts += c
for j3 in (False, True):    # the guide blocks stand on the bed: where they reach past the base there is nothing under them
    g_blk, g_chan = guide(TOP - PCB_TOP, ES.SL_XC + (ES.J3_SHIFT if j3 else 0))
    solids.append(place(g_blk, j3))
    cuts.append(place(g_chan, j3))
# J1: arm out over the rear edge of the turret plate; its thick end carries the flag
FR0, FR1 = ES.J1_FLAG_R
ARM_W, BOSS_T = 10.0, 5.0
solids += [box(-FR1, -X_END, -ARM_W / 2, ARM_W / 2, z0, z1), box(-FR1, -FR0, -ARM_W / 2, ARM_W / 2, z0, z0 + BOSS_T)]
FX = -(FR0 + FR1) / 2
cuts += [cyl(1.7, FX, 0, z0 - 1, z0 + BOSS_T + 1), box(FX - 2.85, FX + 2.85, -3.3, 3.3, z0 - 1, z0 + 2.8)]
plate = solids[0].fuse(solids[1:]).removeSplitter()
plate = plate.cut(cuts[0].fuse(cuts[1:])).removeSplitter()
lp = show("LimitPlate", plate, "Limit switch bracket (print)")

# ------------------------------------------------------------ J1 flag ---
# saddle over the arm's end: block from the lever up to above the arm, slot for the arm's end right
# through it, so it can only slide along the arm and the screw stops that
FZ0, FZ1 = ES.J1_EDGE + ES.STANDOFF, TOP + BOSS_T + 3.0
fw = ES.J1_FLAG_W / 2
flag = box(-FR1, -FR0, -fw, fw, FZ0, FZ1)
flag = flag.cut(box(-FR1 - 1, -FR0 + 1, -ARM_W / 2 - 0.15, ARM_W / 2 + 0.15, TOP - 0.5, TOP + BOSS_T + 0.2))
flag = flag.cut(cyl(1.7, FX, 0, TOP + BOSS_T, FZ1 + 1))
c = ES.FINGER_CH
for sg in (1, -1):   # the two long bottom edges: it rides onto the lever from either end
    w = Part.makePolygon([V(0, sg * fw, FZ0), V(0, sg * (fw - c), FZ0), V(0, sg * fw, FZ0 + c), V(0, sg * fw, FZ0)])
    flag = flag.cut(Part.Face(w).extrude(V(FR1 - FR0 + 2, 0, 0)).translated(V(-FR1 - 1, 0, 0)))
flag = flag.removeSplitter()
fl = show("LimitFlag", flag, "J1 limit flag (print, M3x12 + nut)")

# ---------------------------------------------------------- J1 collar ---
CT, CZ1 = ES.J1_COLLAR_T, BODY_H - 1.0
CZ0 = CZ1 - ES.J1_COLLAR_H
SEAT_X = ES.J1_PCB_X - ES.BOARD_T                       # the PCB's back
ring = Part.makeCylinder(HR + CT, CZ1 - CZ0, V(0, 0, CZ0))
ears = [box(-8, 8, sg * (HR + 2), sg * (HR + 15), CZ0, CZ1) if sg > 0 else box(-8, 8, -(HR + 15), -(HR + 2), CZ0, CZ1)
        for sg in (1, -1)]
riser = box(48.5, SEAT_X, Y0_J1 - 0.6, Y0_J1 + ES.BOARD_L + 0.6, CZ1 - 14.0, ES.J1_EDGE + 0.6)
# the SKR Pico's pad at the back: electronics.py screws the board plate to its flat face
pad = box(-ES.SKR_PAD_X, -40, -ES.SKR_PAD_W, ES.SKR_PAD_W, CZ0, ES.SKR_PAD_Z1)
j1_blk, j1_chan = guide(48.5 - ES.J1_PCB_X, ES.SL_XC)
# printed standing: what reaches out past the riser (towards the board's components) gets a 45 deg underside
_w = [V(0, -2, -1.6), V(0, 0.6, -1.6), V(0, 12.2, 10), V(0, -2, 10)]
j1_chan = j1_chan.fuse(Part.Face(Part.makePolygon(_w + _w[:1])).extrude(V(ES.BOARD_L + 2, 0, 0)).translated(V(-1, 0, 0)))
col = ring.fuse(ears + [riser, pad, j1_blk.transformGeometry(M_J1)])
col = col.cut(Part.makeCylinder(HR, BODY_H + 0.6 - CZ0 + 1, V(0, 0, CZ0 - 1)))      # the housing; above it the seat may reach in
ccuts = [box(-0.5, 0.5, -HR - 20, HR + 20, CZ0 - 1, ES.J1_EDGE + 2),                 # split into halves
         j1_chan.transformGeometry(M_J1),
         # room for the solder joints behind the PCB: under the seat strip, and behind the header
         box(SEAT_X - 2.5, SEAT_X + 1, Y0_J1 + 3.2, Y0_J1 + ES.BOARD_L + 1, ES.J1_EDGE - ES.TERM_Y - 4.0, ES.J1_EDGE - ES.TERM_Y + 0.7),
         box(SEAT_X - 2.5, SEAT_X + 1, Y0_J1 + 3.2, Y0_J1 + 12.4, ES.J1_EDGE - ES.CONN[3] - 1.0, ES.J1_EDGE - 1.0)]
for hx, hy in ES.HOLES:
    y, z = Y0_J1 + hx, ES.J1_EDGE - hy
    ccuts += [box(SEAT_X - 2.0 - CH_H, SEAT_X - 2.0, y - CH_W / 2, y + CH_W / 2, z - ES.ADJ[1] - 3.6, ES.J1_FLAG_Z0 + 1),   # nut channel, open on top
              box(48, SEAT_X + 1, y - SLOT_W / 2, y + SLOT_W / 2, z - ES.ADJ[1] - SLOT_W / 2, z - ES.ADJ[0] + SLOT_W / 2)]  # slot, right through
for sg in (1, -1):
    y = sg * (HR + 8.5)
    for z in ES.J1_COLLAR_SCR_Z:
        ccuts += [Part.makeCylinder(1.7, 20, V(-10, y, z), V(1, 0, 0)),
                  box(-9, -5.2, y - 2.85, y + 2.85, z - 3.3, z + 3.3)]   # nut pocket in the rear half
    y = sg * ES.SKR_SCR_Y
    ccuts += [Part.makeCylinder(1.7, ES.SKR_PAD_X - 48, V(-ES.SKR_PAD_X - 1, y, ES.SKR_SCR_Z), V(1, 0, 0)),
              box(-ES.SKR_PAD_X + 3.4, -ES.SKR_PAD_X + 6.0, y - 2.95, y + 2.95, ES.SKR_SCR_Z - 3.3, ES.SKR_PAD_Z1 + 1)]   # pad nut, from above
col = col.cut(ccuts[0].fuse(ccuts[1:])).removeSplitter()
halves = sorted(col.Solids, key=lambda h: -h.BoundBox.XMax)
if len(halves) != 2:
    sys.exit(f"collar: expected 2 solids, got {len(halves)}")
cf = show("LimitCollarFront", halves[0], "J1 collar, front half with the board seat (print)")
cr = show("LimitCollarRear", halves[1], "J1 collar, rear half (print)")

# ------------------------------------------------------------ context ---
ctx = doc.addObject("App::DocumentObjectGroup", "Context")
for d, n in ((tur, "TurretBody"), (tur, "J1HubScrews"), (ua, "UpperArm"), (ua, "Crank"), (bas, "BaseHousing")):
    lk = doc.addObject("App::Link", "Ctx_" + n)
    lk.LinkedObject = d.getObject(n)
    lk.LinkTransform = True
    ctx.addObject(lk)
doc.recompute()
doc.save()

def export(shape, stem, rot=None):
    s = shape.copy()
    if rot:
        s.rotate(V(0, 0, 0), rot[0], rot[1])
    s.translate(V(0, 0, -s.BoundBox.ZMin))
    Import.export([Part.show(s, stem)], os.path.join(here, stem + ".step"))
    m = Mesh.Mesh()
    m.addFacets(s.tessellate(0.05))
    m.write(os.path.join(here, stem + ".stl"))
    doc.removeObject(stem)


export(plate, "limit_plate")
export(flag, "limit_flag", (V(0, 1, 0), -90))     # outer face (the one away from the turret) on the bed
export(halves[0], "limit_collar_front")
export(halves[1], "limit_collar_rear")
export(bp["slider_in"], "limit_rocker")                       # J1, J2: on its flat underside
export(bp3["slider_in"], "limit_rocker_j3")                   # J3
export(bp["cover"], "limit_cover", (V(1, 0, 0), 180))         # top face on the bed, the bosses up
for o in (fl, cf, cr):
    print(f"{o.Name} vol {o.Shape.Volume / 1000:.2f} cm3 valid {o.Shape.isValid()} solids {len(o.Shape.Solids)}")
print(f"LimitPlate vol {plate.Volume / 1000:.2f} cm3 valid {plate.isValid()} solids {len(plate.Solids)}")
print(f"board screws J2/J3: cover top to the nut pocket's top {ES.COVER_Z[1] + PCB_TOP - TOP - NUT_TOP:.1f} mm (+2.4 nut), "
      f"to the bracket's underside {ES.COVER_Z[1] + PCB_TOP - TOP:.1f} mm")
print(f"board screws J1: cover top to the nut channel's inner face {ES.J1_PCB_X + ES.COVER_Z[1] - (SEAT_X - 2.0 - CH_H):.1f} mm, "
      f"to the riser's back {ES.J1_PCB_X + ES.COVER_Z[1] - 48.5:.1f} mm")

# -------------------------------------------------------------- checks ---
def posed(shape, ang):
    r = shape.copy()
    r.rotate(V(0, 0, 0), V(0, 1, 0), -ang)
    r.translate(V(0, 0, SH_Z))
    return r


arm = Part.makeCompound([ua.getObject(n).Shape
                         for n in ("UpperArmJ2", "UpperArmJ2Cap", "UpperArmJ3", "Spacer0", "Spacer1", "Spacer2")])
crank = Part.makeCompound([ua.getObject(n).Shape for n in ("J3Crank", "J3CrankCap")])
static = {"LimitPlate": plate, "TurretBody": tur.getObject("TurretBody").Shape,
          "J1HubScrews": tur.getObject("J1HubScrews").Shape}
for tag in boards:
    static[f"Endstop{tag}"] = Part.makeCompound([boards[tag][k] for k in ("pcb", "sw", "conn", "plug", "solder")])
    static[f"Slider{tag}"] = boards[tag]["slider"]
    static[f"SliderIn{tag}"] = boards[tag]["slider_in"]
    static[f"Cover{tag}"] = boards[tag]["cover"]
    static[f"Lever{tag}"] = boards[tag]["lever"]
    static[f"LeverIn{tag}"] = boards[tag]["lever_in"]
static.update({"LimitFlag": flag, "LimitCollarFront": halves[0], "LimitCollarRear": halves[1],
               "BaseHousing": bas.getObject("BaseHousing").Shape})

print("static fit:")
bad = 0
# (the bracket against the hub screws is left out: the model still has the two M3x20 with their heads
# on the turret, where the bracket's screw seats now are)
for a, b in (("LimitPlate", "TurretBody"), ("EndstopJ2", "LimitPlate"),
             ("EndstopJ3", "LimitPlate"), ("EndstopJ2", "J1HubScrews"), ("EndstopJ3", "J1HubScrews"),
             ("EndstopJ2", "EndstopJ3"), ("LimitFlag", "LimitPlate"), ("LimitFlag", "TurretBody"),
             ("LimitCollarFront", "BaseHousing"), ("LimitCollarRear", "BaseHousing"),
             ("LimitCollarFront", "LimitCollarRear"), ("EndstopJ1", "LimitCollarFront"), ("EndstopJ1", "BaseHousing"),
             ("SliderJ2", "LimitPlate"), ("SliderInJ2", "LimitPlate"), ("SliderJ3", "LimitPlate"), ("SliderInJ3", "LimitPlate"),
             ("SliderJ1", "LimitCollarFront"), ("SliderInJ1", "LimitCollarFront"),
             ("SliderJ2", "EndstopJ2"), ("SliderInJ2", "EndstopJ2"), ("SliderJ3", "EndstopJ3"), ("SliderInJ3", "EndstopJ3"),
             ("SliderJ1", "EndstopJ1"), ("SliderInJ1", "EndstopJ1"),
             ("CoverJ2", "LimitPlate"), ("CoverJ3", "LimitPlate"), ("CoverJ1", "LimitCollarFront"),
             ("CoverJ2", "EndstopJ2"), ("CoverJ3", "EndstopJ3"), ("CoverJ1", "EndstopJ1"),
             ("CoverJ2", "SliderJ2"), ("CoverJ2", "SliderInJ2"), ("CoverJ3", "SliderJ3"), ("CoverJ3", "SliderInJ3"),
             ("CoverJ1", "SliderJ1"), ("CoverJ1", "SliderInJ1"), ("CoverJ2", "J1HubScrews"), ("CoverJ3", "J1HubScrews"),
             # the lever: nothing but the rocker's rib may touch it, at rest or with a finger on the nose
             ("LeverJ2", "LimitPlate"), ("LeverInJ2", "LimitPlate"), ("LeverJ3", "LimitPlate"), ("LeverInJ3", "LimitPlate"),
             ("LeverJ1", "LimitCollarFront"), ("LeverInJ1", "LimitCollarFront"),
             ("LeverJ2", "SliderJ2"), ("LeverInJ2", "SliderInJ2"), ("LeverJ3", "SliderJ3"), ("LeverInJ3", "SliderInJ3"),
             ("LeverJ1", "SliderJ1"), ("LeverInJ1", "SliderInJ1"),
             ("LeverJ2", "CoverJ2"), ("LeverInJ2", "CoverJ2"), ("LeverJ3", "CoverJ3"), ("LeverInJ3", "CoverJ3"),
             ("LeverJ1", "CoverJ1"), ("LeverInJ1", "CoverJ1")):
    v = static[a].common(static[b]).Volume
    if v > 0.01:
        bad += 1
        print(f"  overlap {a} x {b}: {v:.1f} mm3")
if not bad:
    print("  none")

# the joints, 6 deg past the trip points the fingers were made for (the finger's chamfer puts the real ones
# 2.5-3 deg further out); the crank and the arm don't meet the static parts together
worst, pressed = {}, {"J2": [], "J3": []}
STEP = 0.5
for tag, shape, lo, hi, off in (("J2", arm, ES.J2_LIM[0] - 6, ES.J2_LIM[1] + 6, 0),
                                ("J3", crank, ES.J3_LIM[0] - 6, ES.J3_LIM[1] + 6, 180)):
    n = int(round((hi - lo) / STEP))
    for i in range(n + 1):
        ang = lo + i * STEP
        mv = posed(shape, ang + off)
        if i % 4 == 0:   # every 2 deg is plenty for the solids
            for sn, st in static.items():
                if sn in ("TurretBody", "BaseHousing", "LimitCollarFront", "LimitCollarRear", "EndstopJ1",
                          "SliderJ1", "SliderInJ1", "SliderJ2", "SliderJ3", "CoverJ1",
                          "LeverJ1", "LeverInJ1"):
                    continue   # the turret: upper_arm.py checks it; the rest belongs to J1, below
                v = mv.common(st).Volume
                if v > 0.01 and v > worst.get((tag, sn), (0, 0))[0]:
                    worst[(tag, sn)] = (v, ang)
        for bt in boards:
            if mv.common(boards[bt]["probe"]).Volume > 0.001:
                pressed[tag].append((bt, ang))
# J1: everything on the turret against everything on the base, a full turn
pgd = App.getDocument("pg27")
onturret = [tur.getObject("TurretBody").Shape, plate, flag, static["EndstopJ2"], static["EndstopJ3"], static["CoverJ2"], static["CoverJ3"]]
for n in ("J2_Motor", "J3_Motor"):
    body = pgd.getObject("Motor_NEMA17").Shape.fuse([pgd.getObject(k).Shape for k in ("Flange", "Gearbox")])
    body.Placement = tur.getObject(n).Placement.multiply(body.Placement)
    onturret.append(body)
onturret = Part.makeCompound(onturret)
onbase = {k: static[k] for k in ("LimitCollarFront", "LimitCollarRear", "EndstopJ1", "SliderInJ1", "CoverJ1", "LeverJ1")}
j1_pressed = []
for i in range(int(360 / STEP) + 1):
    ang = -180 + i * STEP
    mv = onturret.copy()
    mv.rotate(V(0, 0, 0), V(0, 0, 1), ang)
    if i % 8 == 0:
        for sn, st in onbase.items():
            v = mv.common(st).Volume
            if v > 0.01 and v > worst.get(("J1", sn), (0, 0))[0]:
                worst[("J1", sn)] = (v, ang)
    if abs(ang) > 150:
        fm = flag.copy()
        fm.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        if fm.common(boards["J1"]["probe"]).Volume > 0.001:
            j1_pressed.append(ang)
print("interference sweep (arm and crank against the boards, the bracket, the hub screws; the turret a full turn over the J1 collar):")
if not worst:
    print("  none")
for (tag, sn), (v, ang) in worst.items():
    print(f"  {tag} parts x {sn}: {v:.1f} mm3 at {tag}={ang}")
print("switch pressed (finger far enough onto the rocker's nose to click it):")
for tag in ("J2", "J3"):
    own = sorted(a for b, a in pressed[tag] if b == tag)
    other = [a for b, a in pressed[tag] if b != tag]
    runs, start = [], None
    for k, a in enumerate(own):
        if start is None:
            start = a
        if k == len(own) - 1 or own[k + 1] - a > STEP * 1.5:
            runs.append((start, a))
            start = None
    print(f"  {tag}: " + (", ".join(f"{a:g}..{b:g}" for a, b in runs) or "never")
          + (f"   !! also presses the other board at {other}" if other else ""))
neg, posv = [a for a in j1_pressed if a < 0], [a for a in j1_pressed if a > 0]
print("  J1: " + (f"-180..{max(neg):g}, {min(posv):g}..180" if neg and posv else f"!! {j1_pressed}"))
