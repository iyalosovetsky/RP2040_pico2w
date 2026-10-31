#!/usr/bin/env python3
"""
arm_ik.py - host-side kinematics for the grblHAL robot arm, scheme C (parallelogram).

The firmware is joint-space: G-code X/Y/Z/A are joint angles in degrees.
  X = J1  base yaw
  Y = J2  upper arm angle above horizontal
  Z = J3  forearm angle above horizontal (absolute: the J3 crank on the turret sets it
          directly through the parallelogram, it is NOT relative to the upper arm)
  A = J4  tool: on bracket Z it turns the tool about the vertical (yaw),
          on bracket Y it tilts the tool in the arm's plane (0 = down, 90 = forward)
The levelling rods keep the wrist fork horizontal, so the tool position depends only on
J1..J3 (plus J4's tilt on bracket Y).

Geometry is read from the CAD spreadsheets (cad/upper_arm.FCStd, forearm.FCStd,
tools.FCStd) when they are present, so the IK follows the printed parts; the values in
GEOM are the fallback. Tools are listed in TOOLS - measure your actual tool lengths.

Examples:
  arm_ik.py ik 200 0 60                                 # gripper on bracket Z, J4 = 0
  arm_ik.py ik 200 50 80 --tool spindle --mount y --pitch 30
  arm_ik.py ik 200 0 60 --port /dev/ttyACM0             # also send the move
  arm_ik.py fk 0 90 -30 0                               # tool point for joint angles
  arm_ik.py send examples/arm_pick_place.gcode --port /dev/ttyACM0
"""

import argparse
import math
import os
import re
import sys
import zipfile

CAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cad")

GEOM = {
    "shoulder_z": 155.0,  # shoulder axis above the table
    "len_l2": 140.0,      # shoulder -> elbow
    "len_l3": 140.0,      # elbow -> wrist axle
    "fk_drop": 24.0,      # wrist fork bridge bottom below the wrist axle (brackets bolt here)
    "br_t": 6.0,          # bracket plate thickness
    "shaft_reach": 20.7,  # PG27 shaft tip from the gearbox face
    "tp_t": 6.0,          # tool interface plate thickness
    "zx": 68.0,           # bracket Z: J4 axis ahead of the wrist axle
    "yx": 70.0,           # bracket Y: J4 axis ahead of the wrist axle
    "yz": -80.0,          # bracket Y: J4 axis below the wrist axle
    "y_face": 37.0,       # bracket Y: J4 gearbox face |y|
}

# Joint limits the CAD was interference-checked for (cad/forearm.py, cad/tools.py).
LIMITS = {
    "X": (-170.0, 170.0),
    "Y": (35.0, 150.0),
    "Z": (-70.0, 35.0),
    "A_z": (-180.0, 180.0),
    "A_y": (-60.0, 130.0),
}
LINK_ANGLE = (30.0, 140.0)  # angle between upper arm and forearm = 180 + (J3 - J2)

# Tools. mount z: "below" = tool point below the flange plate's underside, on the J4 axis.
# mount y: "reach" = tool point from the J4 axis along the tool; the tool axis sits beside the
# flange: flange plate face, minus the clamp's own plate, minus the clamp ring's radius.
# The lengths match the tool shapes in cad/viewer/roboruka.html - measure your real tools.
TOOLS = {
    "grip":    {"z": {"below": 90.0}},
    "m775":    {"z": {"below": 121.0}, "y": {"reach": 100.0, "ring_r": 27.1}},
    "spindle": {"z": {"below": 195.0}, "y": {"reach": 139.0, "ring_r": 32.1}},
}

# Per-joint calibration: machine = sign * kinematic + offset (set after homing).
CAL = {"X": (1, 0.0), "Y": (1, 0.0), "Z": (1, 0.0), "A": (1, 0.0)}

AXES = ("X", "Y", "Z", "A")


class IKError(Exception):
    pass


def load_cad(geom):
    """Overlay GEOM with the literal values in the CAD spreadsheets, where present."""
    found = []
    for f in ("upper_arm", "forearm", "tools"):
        path = os.path.join(CAD, f + ".FCStd")
        if not os.path.exists(path):
            continue
        xml = zipfile.ZipFile(path).read("Document.xml").decode("utf-8", "replace")
        for content, alias in re.findall(r'<Cell address="\w+" content="([^"]*)"[^>]*alias="(\w+)"', xml):
            m = re.fullmatch(r"=?\s*(-?[\d.]+)\s*mm", content)
            if alias in geom and m:
                geom[alias] = float(m.group(1))
                found.append(alias)
    return sorted(set(found))


def tool_offset(geom, tool, mount, j4):
    """Tool point relative to the wrist axle: (forward, sideways y, up), J4 in degrees."""
    spec = TOOLS[tool].get(mount)
    if spec is None:
        raise IKError(f"tool '{tool}' has no {mount.upper()} mount")
    if mount == "z":
        flange_under = geom["fk_drop"] + geom["shaft_reach"] + 0.5 + geom["tp_t"]
        return geom["zx"], 0.0, -(flange_under + spec["below"])
    p = math.radians(j4)
    plate_face = geom["y_face"] - geom["shaft_reach"] - 0.5 - geom["tp_t"]
    side = plate_face - geom["tp_t"] - spec["ring_r"]
    return (geom["yx"] + spec["reach"] * math.sin(p), side,
            geom["yz"] - spec["reach"] * math.cos(p))


def fk(geom, j1, j2, j3, j4, tool="grip", mount="z"):
    """Kinematic joint angles (deg) -> tool point (x, y, z) mm, table frame."""
    a2, a3 = math.radians(j2), math.radians(j3)
    r = geom["len_l2"] * math.cos(a2) + geom["len_l3"] * math.cos(a3)
    h = geom["shoulder_z"] + geom["len_l2"] * math.sin(a2) + geom["len_l3"] * math.sin(a3)
    dx, dy, dz = tool_offset(geom, tool, mount, j4)
    r += dx
    yaw = math.radians(j1)
    return (r * math.cos(yaw) - dy * math.sin(yaw), r * math.sin(yaw) + dy * math.cos(yaw), h + dz)


def _wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def ik_candidates(geom, x, y, z, tool="grip", mount="z", j4=0.0):
    """Tool point (mm) -> elbow-up joint solutions (deg). Two when the tool point can be
    reached facing it or with the arm reaching back over the base (J1 turned ~180)."""
    dx, dy, dz = tool_offset(geom, tool, mount, j4)
    rr = x * x + y * y - dy * dy
    if rr < 0:
        raise IKError("target is inside the tool's sideways offset")
    l2, l3 = geom["len_l2"], geom["len_l3"]
    out, reach = [], None
    for r_tool in (math.sqrt(rr), -math.sqrt(rr)):
        j1 = math.degrees(math.atan2(y, x) - math.atan2(dy, r_tool))
        r, h = r_tool - dx, z - dz - geom["shoulder_z"]      # wrist axle in the arm plane
        d = math.hypot(r, h)
        c = (d * d - l2 * l2 - l3 * l3) / (2 * l2 * l3)
        if not -1.0 <= c <= 1.0:
            reach = d
            continue
        q = math.acos(c)                                     # elbow bend
        a2 = math.atan2(h, r) + math.atan2(l3 * math.sin(q), l2 + l3 * math.cos(q))
        out.append((_wrap(j1), math.degrees(a2), math.degrees(a2 - q), j4))
    if not out:
        raise IKError(f"out of reach: wrist axle {reach:.1f} mm from the shoulder (max {l2 + l3:.0f})")
    return out


def ik(geom, x, y, z, tool="grip", mount="z", j4=0.0):
    """First solution inside the joint limits (facing the target preferred)."""
    errs = []
    for j in ik_candidates(geom, x, y, z, tool, mount, j4):
        try:
            check_limits(j, mount)
            return j
        except IKError as e:
            errs.append(str(e))
    raise IKError("no solution inside the limits: " + " | ".join(errs))


def check_limits(j, mount):
    j1, j2, j3, j4 = j
    errs = []
    for ax, v in (("X", j1), ("Y", j2), ("Z", j3), ("A_" + mount, j4)):
        lo, hi = LIMITS[ax]
        if not lo - 1e-6 <= v <= hi + 1e-6:
            errs.append(f"{ax[0]}={v:.1f} outside {lo:.0f}..{hi:.0f}")
    link = 180.0 + (j3 - j2)
    if not LINK_ANGLE[0] - 1e-6 <= link <= LINK_ANGLE[1] + 1e-6:
        errs.append(f"angle between the links {link:.1f} outside {LINK_ANGLE[0]:.0f}..{LINK_ANGLE[1]:.0f}")
    if errs:
        raise IKError("; ".join(errs))


def to_machine(j):
    return {ax: CAL[ax][0] * v + CAL[ax][1] for ax, v in zip(AXES, j)}


def from_machine(m):
    return tuple((m[ax] - CAL[ax][1]) / CAL[ax][0] for ax in AXES)


def gcode_move(m, feed=None, rapid=False):
    words = " ".join(f"{ax}{m[ax]:.3f}" for ax in AXES)
    return f"G0 {words}" if rapid else f"G1 {words} F{feed:.0f}"


def stream(port, lines, baud=115200):
    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("pyserial is required for --port: pip install pyserial")
    with serial.Serial(port, baud, timeout=30) as ser:
        ser.write(b"\r\n")
        ser.reset_input_buffer()
        for line in lines:
            line = line.split(";")[0].strip()
            if not line:
                continue
            ser.write((line + "\n").encode())
            while True:
                reply = ser.readline().decode(errors="replace").strip()
                if not reply:
                    sys.exit(f"timeout waiting for reply to: {line}")
                if reply == "ok":
                    print(f"> {line}")
                    break
                if reply.startswith(("error", "ALARM")):
                    sys.exit(f"> {line}\n{reply}")
                print(reply)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-cad", action="store_true", help="use the built-in geometry, not cad/*.FCStd")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def tool_args(p):
        p.add_argument("--tool", choices=sorted(TOOLS), default="grip")
        p.add_argument("--mount", choices=("z", "y"), default="z", help="tool bracket: z (J4 vertical) or y (J4 tilts)")

    a = sub.add_parser("ik", help="tool point -> joint G-code")
    for k in ("x", "y", "z"):
        a.add_argument(k, type=float)
    tool_args(a)
    a.add_argument("--pitch", type=float, default=0.0, help="bracket Y: tool tilt, 0 = down, 90 = forward")
    a.add_argument("--yaw", type=float, default=0.0, help="bracket Z: tool rotation about the vertical")
    a.add_argument("--feed", type=float, default=900.0, help="joint feed, deg/min (G1)")
    a.add_argument("--rapid", action="store_true", help="emit G0 instead of G1")
    a.add_argument("--port", help="serial port to send the move to, e.g. /dev/ttyACM0")

    f = sub.add_parser("fk", help="machine joint angles -> tool point")
    for ax in AXES:
        f.add_argument(ax.lower(), type=float)
    tool_args(f)

    s = sub.add_parser("send", help="stream a G-code file to the board")
    s.add_argument("file")
    s.add_argument("--port", required=True)

    args = ap.parse_args()
    geom = dict(GEOM)
    if not args.no_cad:
        load_cad(geom)

    try:
        if args.cmd == "ik":
            j4 = args.pitch if args.mount == "y" else args.yaw
            j = ik(geom, args.x, args.y, args.z, args.tool, args.mount, j4)
            line = gcode_move(to_machine(j), args.feed, args.rapid)
            print(line)
            if args.port:
                stream(args.port, [line])
        elif args.cmd == "fk":
            j = from_machine({ax: getattr(args, ax.lower()) for ax in AXES})
            x, y, z = fk(geom, *j, args.tool, args.mount)
            try:
                check_limits(j, args.mount)
                note = ""
            except IKError as e:
                note = f"  (outside the checked range: {e})"
            print(f"tool x={x:.2f} y={y:.2f} z={z:.2f} mm{note}")
        elif args.cmd == "send":
            with open(args.file) as fh:
                stream(args.port, fh.readlines())
    except IKError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
