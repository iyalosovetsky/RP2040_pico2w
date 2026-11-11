## RP2040 Driver

A grblHAL driver for the Raspberry Pi Pico RP2040 processor on a [Pi Pico or Pi Pico W board](https://www.raspberrypi.org/products/raspberry-pi-pico/).

This driver can be built with the [Web Builder](https://svn.io-engineering.com:8443/?driver=RP2040&board=PicoCNC).

__Important__ download information can be found [here](https://github.com/grblHAL/core/wiki/Compiling-grblHAL).  
The project has been updated to/now uses [SDK version 2.1.1](https://github.com/raspberrypi/pico-sdk/releases).

The default build environment is Visual Studio Code, it is surprisingly easy to set up on Raspberry Pi - see the [Getting started](https://datasheets.raspberrypi.org/pico/getting-started-with-pico.pdf) documentation for how to for this and other platforms.

> [!NOTE]
> The RP2350B_5X board uses a RP2350B processor, to build the firmware with Visual Studio Code choose the _pimoroni_pga2350_ board.
For other boards choose the _pico_, _pico\_w_, _pico2_ or _pico2\_w_ board that matches the processor or Pico board used.  
The board is selected in the lower right corner of the UI.

---

## This fork (btt_st3215 branch)

Configured for a **BTT SKR Pico 1.0** board (`BOARD_BTT_SKR_PICO_10` in [my_machine.h](my_machine.h)) driving a CNC with an independent rotary table and a Feetech/Waveshare ST3215 serial bus servo.

> See also [rotary-pico](https://github.com/iyalosovetsky/rotary-pico) — a standalone MicroPython firmware for the same BTT SKR Pico turntable/servo rig, independent of grblHAL.
>
> [Demo video](https://www.youtube.com/watch?v=oVeflQN5IRw) of the rig in action.

If you're working on this repo with [Claude Code](https://claude.com/claude-code), see [CLAUDE.md](CLAUDE.md) for this fork's architecture notes, and the `grblhal-driver-dev` skill (user-level, `~/.claude/skills/grblhal-driver-dev/`) for the general grblHAL extension patterns and gotchas this session's work uncovered — custom M-codes, `$`-settings, status report fields, and why some config has to live in `CMakeLists.txt` instead of `my_machine.h`.

### Robot arm (robot_arm branch, `ROBOT_ARM` CMake option, default ON)

The same board as a 4-joint arm: four **17HS15-1684S-PG27** NEMA17 steppers with a 26.85:1 planetary gearbox on the board's four TMC2209 drivers, plus the ST3215 servo as the gripper. Build the CNC + rotary table variant with `./build.sh --cnc` (`-DROBOT_ARM=OFF`).

| Joint | grbl axis | Driver / connector | Limit input |
|---|---|---|---|
| Base yaw | X | X | X-STOP (GPIO4) |
| Shoulder | Y | Y | Y-STOP (GPIO3) |
| Elbow | Z | Z | Z-STOP (GPIO25) |
| Wrist pitch | A | E0 (GPIO14/13/15, TMC addr 3) | E0-STOP (GPIO16) |
| Gripper | - | ST3215 on UART0 (GPIO0/1), id 1 | - |

The machine is **joint-space**: G-code X/Y/Z/A are joint angles in degrees (grbl reports X/Y/Z as "mm", read them as degrees) - X = J1 base yaw, Y = J2 upper arm above horizontal, Z = J3 forearm above horizontal (an *absolute* angle: the parallelogram drives it from the turret), A = J4 tool yaw (bracket Z) or tilt (bracket Y). Cartesian moves are converted on the host by [tools/arm_ik.py](tools/arm_ik.py), which reads the link lengths and bracket offsets straight from the `cad/*.FCStd` spreadsheets: `arm_ik.py ik <x> <y> <z> [--tool grip|m775|spindle] [--mount z|y] [--pitch <deg>] [--port /dev/ttyACM0]`, `arm_ik.py fk <X> <Y> <Z> <A>` to check a pose. It refuses targets outside the CAD-checked range (J2 35..150, J3 -70..35, 30..140 deg between the links, tilt -60..130 on bracket Y). Moves are interpolated in joint space, so a G1 between two poses is not a straight line at the tool - keep approach moves short. Set per-joint sign/offset in `CAL` after homing. See [examples/arm_pick_place.gcode](examples/arm_pick_place.gcode).

Defaults baked in via `CMakeLists.txt` (all overridable with `$`-settings after flashing):
- `$100-$103` = **238.678 steps/deg** (200 × 16 microsteps × 26+103/121 / 360).
- `$110-$113` = 1800 deg/min (30 °/s, ~7.2 kHz step rate), `$120-$123` = 60 °/s².
- `$140-$143` TMC2209 current = **700 mA RMS** (motor rated 1.68 A), `$210-$213` hold current 60 %. The current is the arm's torque fuse: at the rated current a joint stalls at roughly 7-8 N·m, the gearbox allows ~3 N·m and the links are printed; 700 mA stalls at roughly 3 N·m (datasheet estimate, not measured — raise it only as far as the payload needs).
- Drivers start in StealthChop (`M569` toggles per axis) — StallGuard4 needs it.
- `$1=255` — drivers stay enabled when idle. The PG27 gearbox back-drives; with the motors released the arm falls under its own weight.
- `$37=15` — and they stay enabled after an **alarm** too. Without it grbl releases every axis 255 ms after a hard limit trip or a reset during a move, `$1=255` or not.
- `$3=0` direction invert — set per joint once wired; homing/soft limits are off until limit switches are fitted (`$22`, `$20`, `$130-$133`).

Overload guard (in [arm_guard.c](arm_guard.c), `ARM_GUARD_ENABLE`) — the TMC2209 has no readable motor current, but in StealthChop it reports the motor's load as `SG_RESULT` (StallGuard4: 510 = no load, falling towards 0 near a stall). The drivers' DIAG outputs share the endstop inputs with the limit switches on this board, so the plugin polls `SG_RESULT` over the TMC UART for every joint that is moving:
- The `?` report gets `|SG:<x>,<y>,<z>,<a>` — per joint the lowest reading since the previous report, `-` where there is none. It only shows while something moves faster than `$458` (deg/min, default 600): at standstill and when creeping there is no back-EMF to measure, so a joint that just holds a load is **not** monitored.
- `$457` — axis mask of the joints that kill the motion with **alarm 17** when the reading stays at or below 2 × their StallGuard threshold for two polls (80 ms). Default 0: report only. The thresholds are the Trinamic plugin's own `$200-$203` (also `M914`).
- Tuning: with `$457=0` jog each joint through its range at working speed, note the lowest `|SG:` value, set `$20x` a bit under half of it, then enable the joint in `$457` and check that pushing on the arm by hand trips it. Redo this after changing the current or the feed rates — both move `SG_RESULT`.
- Not tested on the arm yet. `M122` (Trinamic plugin) still gives the full driver report: over-temperature pre-warning, shorts, open load.

After flashing over an existing configuration the old values stay in flash, and the driver mode (StealthChop) has no `$`-setting of its own: run `$RST=*` once, then re-enter what was tuned by hand (`$3`, the gripper angles `$455`/`$456`).

Gripper (in [st3215.c](st3215.c), `ST3215_GRIPPER_ENABLE`):
- `M102 [P<id>]` open to `$455`, `M103 [P<id>]` close to `$456` (degrees).
- `M101 Q`, `M102` and `M103` are now **synchronized with motion**: they execute after all queued moves finish. They do not wait for the servo itself — add `G4 P<s>` before the next move.

Gearbox backlash on the PG27 is around 1°, which at 300 mm reach is several millimetres at the tool; approach pick points from the same direction to keep it repeatable.

> **Mechanics:** parallelogram (palletizer) layout - J2 and J3 both on the turret, J3 driving the forearm through a crank and rod, two levelling rods keeping the wrist level, J4 turning or tilting an interchangeable tool. Parametric FreeCAD models, print-ready STLs and an offline 3D viewer (`cad/viewer/roboruka.html`) are in [cad/](cad/).

### Command-line build

[build.sh](build.sh) wraps the CMake/Ninja/Make flow used by the VS Code extension so the firmware can be built from a terminal:

```bash
./build.sh --clean
```

Run `./build.sh --help` for board selection, feature flags (WiFi/Ethernet/Bluetooth/mDNS/MQTT/HPGL), and `PICO_SDK_PATH` overrides. Note: if `~/.pico-sdk/cmake/pico-vscode.cmake` exists (VS Code Pico extension installed), it forces the SDK path to the version pinned in [CMakeLists.txt](CMakeLists.txt) regardless of `--sdk-path`/`PICO_SDK_PATH`.

### Rotary table — M102/M103/M104

The table motor connects to the board's 4th motor connector (GPIO14 STEP / GPIO13 DIR / GPIO15 ENABLE — see [boards/btt_skr_pico_10_map.h](boards/btt_skr_pico_10_map.h)), but it is **not** a grbl axis: `N_AXIS` stays `3` (X/Y/Z only).

grbl's G-code motion is a single coordinated multi-axis planner — every block moves all axes together and blocks execute strictly in order. There is no way to have one axis spin indefinitely while X/Y/Z keep accepting and executing independent G-code within that model; queuing the table as a 4th axis meant any "spin forever" move blocked every subsequent X/Y/Z command until it finished. [rotary_table.c](rotary_table.c) drives the table motor directly via a free-running RP2040 PWM slice, entirely outside grbl's stepper segment buffer, so it can turn continuously (or through a timed move) while X/Y/Z G-code keeps running unblocked:

```
M102 [S<pulses/s>] [P<0|1>]   ; start continuous rotation (P0 = CW, P1 = CCW)
M103                          ; stop (also stops it on a soft reset / Ctrl-X)
M104 Q<degrees> [S<pulses/s>] ; rotate by <degrees> (signed, relative), then auto-stop
```

`M104`'s auto-stop is time-based (`duration = steps / rate`, scheduled via `task_add_delayed()`) rather than an exact pulse count, so it doesn't block X/Y/Z either.

**TMC2209 setup.** Being outside `N_AXIS`, the table's TMC2209 (same shared UART bus as X/Y/Z, its own address) is never touched by grbl's own Trinamic driver setup. Left alone it takes its microstep resolution from the MS1/MS2 *pins* (used for UART address selection on this board, not microstepping) instead of the UART-configured MRES register - far coarser than X/Y/Z's 16 microsteps, and audibly rough at low `M102`/`M104` rates. `rotary_table_init()` explicitly adds it as a TMC2209 motor (`TMC2209_AddMotor`) and configures it the same way grbl's settings load does for X/Y/Z. Current and chopper algorithm are runtime `$`-settings, applied immediately on change, no reboot needed:

- `$453` - motor current, mA RMS (0-1500, capped to the fitted 42BYGH34's rating - check your own motor's rating before raising it)
- `$454` - chopper mode: `0` = StealthChop (quiet, default), `1` = SpreadCycle (louder, more torque)

> [!WARNING]
> Don't call the settings `.load()` handler (or anything that writes to the TMC2209 over UART) directly from `rotary_table_init()`/`board_init()`. It hung the board (reproduced by testing) - most likely because going through `restore()` can trigger an NVS flash write (`flash_range_erase`/`flash_range_program`) this early in boot, before whatever needs to be quiesced for that to be safe on RP2040 actually is. grbl's settings framework calls each plugin's `.load` on its own at a safe point later in boot regardless - same as [st3215.c](st3215.c), which never calls its own load function directly either - so it isn't even necessary to force it early. `TMC2209_AddMotor` already leaves the driver in a safe working state (default current, StealthChop) for the window before that happens.

Default direction invert (`$3`) and X/Y/Z limit/probe/E-stop invert are still configured live after flashing:

```
$5=7      ; invert X/Y/Z limit pins (NC-switch convention; floating pins read as triggered)
$6=1      ; invert probe
$14=64    ; invert E-stop/control signal
```

`$3` (direction invert) defaults to `7` (X/Y/Z inverted) out of the box via `DEFAULT_DIR_SIGNALS_INVERT_MASK` in [CMakeLists.txt](CMakeLists.txt) — not `my_machine.h`, because `grbl/settings.c` (which actually reads it) `#include`s `grbl/config.h` directly and never sees `my_machine.h`. The same reach problem applies to any other compile-time default that grbl *core* (not just driver.c) needs to see — put those in `CMakeLists.txt`, not `my_machine.h`.

### ST3215 bus servo — M101

[st3215.c](st3215.c) adds `M101 [P<id>] [Q<angle>]` for a Feetech/Waveshare ST3215 servo:
- `M101 Q<angle>` moves the servo (default id `1`, or the id given with `P`) to `<angle>` degrees.
- `M101` (no `Q`) reports status: `[ST3215:<id>|A:<angle>|L:<load%>|V:<voltage>|T:<temperature>]`.

The servo talks over a dedicated hardware UART (UART0, GPIO0 TX / GPIO1 RX by default — free because USB CDC is the primary console stream). ST3215 is a single-wire half-duplex bus: tie TX and RX together (with a series resistor) to the servo's signal pin.

Persistent `$`-settings (NVS-backed, survive reboots and reflashes):
- `$450` — move speed, raw ST3215 steps/s (`0` = max/uncontrolled speed)
- `$451` / `$452` — minimum / maximum allowed angle in degrees; `M101 Q` outside this range is rejected before it reaches the servo

See the header comment in [st3215.c](st3215.c) for the wiring diagram and protocol details.

---
2025-12-31
