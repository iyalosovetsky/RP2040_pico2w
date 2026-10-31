#!/usr/bin/env python3
"""
arm_ik.py - host-side kinematics for the grblHAL 4-joint robot arm (ROBOT_ARM build).

The firmware is joint-space only: G-code X/Y/Z/A are joint angles in degrees
(X = base yaw, Y = shoulder, Z = elbow, A = wrist pitch). This script turns a
Cartesian tool target into those angles and, optionally, streams the G-code to
the board over USB serial.

Geometry (edit ARM below to match your build), all lengths in mm:

            wrist ---L4--- tool tip
             /
           L3   (forearm)
           /
      elbow
         \\
          L2    (upper arm)
           \\
         shoulder  <- D1 above the table, R1 forward of the base axis
            |
          base (yaws about the vertical axis)

Kinematic angles (before per-joint offset/sign are applied):
  base     - yaw from +X toward +Y
  shoulder - upper arm elevation above horizontal (90 = straight up)
  elbow    - forearm angle relative to the upper arm (0 = straight, negative = folds down)
  wrist    - tool angle relative to the forearm
  pitch    - absolute tool angle below/above horizontal (-90 = pointing straight down)

Machine angle = sign * kinematic angle + offset, so the arm's zero/home pose and
motor direction can be matched without touching the math. Use the "fk" command to
check a pose before moving.

Examples:
  arm_ik.py ik 200 0 120 --pitch -90           # print G-code for a target
  arm_ik.py ik 200 0 120 --pitch -90 --port /dev/ttyACM0
  arm_ik.py fk 0 90 -90 0                       # where is the tool for these angles?
  arm_ik.py send pick.gcode --port /dev/ttyACM0 # stream a file (grbl ok/error handshake)
"""

import argparse
import math
import sys

ARM = {
    "D1": 100.0,  # shoulder axis height above the base plate
    "R1": 0.0,    # shoulder axis offset forward of the base yaw axis
    "L2": 150.0,  # shoulder -> elbow
    "L3": 150.0,  # elbow -> wrist
    "L4": 60.0,   # wrist -> tool tip (gripper jaws centre)
    # Per joint: machine = sign * kinematic + offset, limits in machine degrees.
    "joints": {
        "X": {"sign": 1, "offset": 0.0, "min": -170.0, "max": 170.0},  # base
        "Y": {"sign": 1, "offset": 0.0, "min": 0.0, "max": 180.0},     # shoulder
        "Z": {"sign": 1, "offset": 0.0, "min": -150.0, "max": 150.0},  # elbow
        "A": {"sign": 1, "offset": 0.0, "min": -120.0, "max": 120.0},  # wrist
    },
}

AXES = ("X", "Y", "Z", "A")


class IKError(Exception):
    pass


def ik(x, y, z, pitch, elbow_up=True, arm=ARM):
    """Cartesian tool tip (mm) + tool pitch (deg) -> kinematic joint angles (deg)."""
    base = math.degrees(math.atan2(y, x)) if (x or y) else 0.0
    p = math.radians(pitch)

    # Work in the arm's vertical plane: r = horizontal reach from the shoulder, h = height.
    r = math.hypot(x, y) - arm["R1"] - arm["L4"] * math.cos(p)
    h = z - arm["D1"] - arm["L4"] * math.sin(p)
    l2, l3 = arm["L2"], arm["L3"]

    c3 = (r * r + h * h - l2 * l2 - l3 * l3) / (2 * l2 * l3)
    if not -1.0 <= c3 <= 1.0:
        raise IKError(f"target out of reach (wrist at r={r:.1f} h={h:.1f} mm)")

    elbow = -math.acos(c3) if elbow_up else math.acos(c3)
    shoulder = math.atan2(h, r) - math.atan2(l3 * math.sin(elbow), l2 + l3 * math.cos(elbow))
    wrist = p - shoulder - elbow

    return {
        "X": base,
        "Y": math.degrees(shoulder),
        "Z": math.degrees(elbow),
        "A": math.degrees(wrist),
    }


def fk(base, shoulder, elbow, wrist, arm=ARM):
    """Kinematic joint angles (deg) -> tool tip (mm) and pitch (deg)."""
    b, s, e, w = (math.radians(v) for v in (base, shoulder, elbow, wrist))
    r = arm["R1"] + arm["L2"] * math.cos(s) + arm["L3"] * math.cos(s + e) + arm["L4"] * math.cos(s + e + w)
    h = arm["D1"] + arm["L2"] * math.sin(s) + arm["L3"] * math.sin(s + e) + arm["L4"] * math.sin(s + e + w)
    return r * math.cos(b), r * math.sin(b), h, math.degrees(s + e + w)


def to_machine(kin, arm=ARM):
    out = {}
    for ax in AXES:
        j = arm["joints"][ax]
        v = j["sign"] * kin[ax] + j["offset"]
        if not j["min"] <= v <= j["max"]:
            raise IKError(f"joint {ax} = {v:.2f} deg outside [{j['min']}, {j['max']}]")
        out[ax] = v
    return out


def from_machine(mach, arm=ARM):
    return {ax: (mach[ax] - arm["joints"][ax]["offset"]) / arm["joints"][ax]["sign"] for ax in AXES}


def gcode_move(mach, feed=None, rapid=False):
    words = " ".join(f"{ax}{mach[ax]:.3f}" for ax in AXES)
    if rapid:
        return f"G0 {words}"
    return f"G1 {words} F{feed:.0f}"


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
                print(reply)  # [MSG:...], M101 status etc.


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ik", help="Cartesian target -> joint G-code")
    a.add_argument("x", type=float)
    a.add_argument("y", type=float)
    a.add_argument("z", type=float)
    a.add_argument("--pitch", type=float, default=-90.0, help="tool pitch, deg (-90 = straight down)")
    a.add_argument("--elbow-down", action="store_true", help="use the elbow-down solution")
    a.add_argument("--feed", type=float, default=900.0, help="joint feed, deg/min (G1)")
    a.add_argument("--rapid", action="store_true", help="emit G0 instead of G1")
    a.add_argument("--port", help="serial port to send the move to, e.g. /dev/ttyACM0")

    f = sub.add_parser("fk", help="machine joint angles -> tool position")
    for ax in AXES:
        f.add_argument(ax.lower(), type=float)

    s = sub.add_parser("send", help="stream a G-code file to the board")
    s.add_argument("file")
    s.add_argument("--port", required=True)

    args = ap.parse_args()

    try:
        if args.cmd == "ik":
            mach = to_machine(ik(args.x, args.y, args.z, args.pitch, elbow_up=not args.elbow_down))
            line = gcode_move(mach, args.feed, args.rapid)
            print(line)
            if args.port:
                stream(args.port, [line])
        elif args.cmd == "fk":
            kin = from_machine({ax: getattr(args, ax.lower()) for ax in AXES})
            x, y, z, pitch = fk(kin["X"], kin["Y"], kin["Z"], kin["A"])
            print(f"tool x={x:.2f} y={y:.2f} z={z:.2f} mm  pitch={pitch:.2f} deg")
        elif args.cmd == "send":
            with open(args.file) as fh:
                stream(args.port, fh.readlines())
    except IKError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
