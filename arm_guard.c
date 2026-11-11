/*

  arm_guard.c - overload guard for the robot arm's joints, built on TMC2209 StallGuard4

  Part of grblHAL

  grblHAL is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  grblHAL is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with grblHAL. If not, see <http://www.gnu.org/licenses/>.

  Why: the joints are 27:1 gearmotors on printed parts. A joint that runs into something
  (a wrong G-code, a jog before homing, a missed limit switch) keeps pushing with whatever
  torque the motor current allows. The motor current is the fuse (see the ROBOT_ARM defaults
  in CMakeLists.txt); this plugin is the alarm that goes off before the fuse blows.

  What the TMC2209 can and can't tell us:
  - It has no readable motor current. What it has is SG_RESULT (StallGuard4): 0..510, derived
    from the motor's back-EMF in StealthChop mode. High = lightly loaded, falling towards 0 as
    the load angle approaches a stall. The chip itself calls a stall when SG_RESULT <= 2 * SGTHRS.
  - SG_RESULT only means something while the motor turns fast enough to produce back-EMF, and
    only in StealthChop. At standstill and in SpreadCycle there is nothing to read, so a joint
    that is merely holding against gravity is not monitored - the hold current is a plain setting.
  - On this board the drivers' DIAG outputs share the endstop inputs (jumpers), and those are
    taken by the limit switches. So SG_RESULT is polled over the TMC UART instead.

  How it works: every ARM_GUARD_POLL_MS the joint speeds are taken from the step counters
  (no UART traffic for a joint that stands still). For each joint in StealthChop that has been
  above $458 for two polls in a row, SG_RESULT is read. If the joint is enabled in $457 and
  SG_RESULT stays at or below 2 x its StallGuard threshold ($200 + axis, the Trinamic plugin's
  own per-axis "StallGuard4 fast threshold", also set by M914) for ARM_GUARD_TRIP_SAMPLES polls,
  motion is killed with alarm 17 (motor fault), the same way a hard limit does it.

  The "?" report gets |SG:<x>,<y>,<z>,<a> - per joint the LOWEST SG_RESULT seen since the previous
  report ("-" = no valid reading), only while at least one joint has a reading. The lowest value is
  reported, not the latest, so a short dip isn't lost between two status polls.

  Tuning, with the arm assembled and the tool it will carry:
    1. $457=0. Jog each joint through its range at working speed and note the lowest |SG: values.
    2. Set $20x (x = 0..3 for J1..J4) to a bit under half of that lowest value.
    3. Enable the joint in $457 and check that pushing against the arm by hand trips the alarm
       and that normal moves don't.
  SG_RESULT changes with motor current and speed: redo this after changing $14x or the feed rates.

  Two more checks live here because they guard the same arm; both need the joints homed on the
  limit switches (cad/limits.py, defaults in CMakeLists.txt):

  - Angle between the links. The parallelogram only allows 30..140 deg between upper arm and forearm
    (180 + J3 - J2), and no per-joint limit can express that: each joint may be inside its own range
    while the forearm folds into the upper arm. With $459 on (default) and J2 and J3 homed, a target
    outside that range is refused the same way a soft limit violation is ($20 must be on for grbl to
    ask). Joint angle = machine position + the angle of the joint's home trip point.
  - Homing with a switch already pressed is refused. A switch trips at both ends of a joint's travel,
    so a joint that starts on its switch could be at either end, and grbl would take it for home and
    back off - further out if it was the other end. Jog the joint off the switch first.

  $-settings:
    $457 - axis mask, joints that raise the alarm (default 0: report only).
    $458 - joint speed in deg/min below which SG_RESULT is ignored (default 600).
    $459 - check the angle between the links (default 1).

*/

#include "driver.h"

#if ARM_GUARD_ENABLE

#include <math.h>
#include <string.h>

#include "grbl/hal.h"
#include "grbl/protocol.h"
#include "grbl/task.h"
#include "grbl/report.h"
#include "grbl/nvs_buffer.h"
#include "grbl/motion_control.h"
#include "grbl/state_machine.h"
#include "grbl/machine_limits.h"
#include "motors/trinamic.h"

#if TRINAMIC_ENABLE != 2209 || !TRINAMIC_UART_ENABLE
#error "arm_guard.c needs UART controlled TMC2209 drivers (StallGuard4)."
#endif

#ifndef ARM_GUARD_POLL_MS
#define ARM_GUARD_POLL_MS 40            // A UART read takes ~1.5 ms: 4 moving joints = ~15% of the foreground.
#endif
#ifndef ARM_GUARD_TRIP_SAMPLES
#define ARM_GUARD_TRIP_SAMPLES 2        // Consecutive low readings needed to trip (2 x 40 ms = 2.4 deg at 30 deg/s).
#endif
#ifndef ARM_GUARD_MIN_SPEED_DEFAULT
#define ARM_GUARD_MIN_SPEED_DEFAULT 600.0f  // deg/min at the joint = ~45 rpm at the motor.
#endif
#define ARM_GUARD_MIN_SPEED_MIN 60.0f
#define ARM_GUARD_MIN_SPEED_MAX 6000.0f
#define ARM_GUARD_BACKOFF_POLLS 50      // Leave a driver alone for 2 s when it doesn't answer (no motor power).
// from cad/endstop_dims.py: J2_LIM[1], J3_LIM[1] (the trip points the joints home on) and the link range of cad/forearm.py
#ifndef ARM_J2_HOME_DEG
#define ARM_J2_HOME_DEG 151.5f
#endif
#ifndef ARM_J3_HOME_DEG
#define ARM_J3_HOME_DEG 36.5f
#endif
#define ARM_LINK_MIN_DEG 30.0f
#define ARM_LINK_MAX_DEG 140.0f
#define ARM_LINK_AXES (Y_AXIS_BIT|Z_AXIS_BIT)
#define SG_NONE 0xFFFF
#define SG_POISON 0xFFFFFFFF

#define Setting_ArmGuard_Axes     Setting_UserDefined_7
#define Setting_ArmGuard_MinSpeed Setting_UserDefined_8
#define Setting_ArmGuard_LinkCheck Setting_UserDefined_9

typedef struct {
    axes_signals_t axes;
    float min_speed;
    uint8_t link_check;
} arm_guard_settings_t;

static arm_guard_settings_t guard = {
    .axes.mask = 0,
    .min_speed = ARM_GUARD_MIN_SPEED_DEFAULT,
    .link_check = 1
};
static travel_limits_ptr check_travel_limits;
static home_machine_ptr home_machine;
static nvs_address_t nvs_address;
static const tmchal_t *tmc[N_AXIS] = {0};
static uint16_t sg_min[N_AXIS];
static on_realtime_report_ptr on_realtime_report;
static on_report_options_ptr on_report_options;

// Called by the Trinamic plugin (via tmc_uart.c) for every driver it has configured.
void arm_guard_driver_postinit (motor_map_t motor, const tmchal_t *driver)
{
    if(motor.id == motor.axis && motor.axis < N_AXIS)
        tmc[motor.axis] = driver;
}

// The HAL's get_sg_result() returns the shadow register even when the driver didn't answer,
// so poison the shadow first: a reply overwrites it (SG_RESULT is 10 bits), a timeout doesn't.
static bool read_sg (uint_fast8_t axis, uint16_t *sg)
{
    TMC2209_datagram_t *reg = (TMC2209_datagram_t *)tmc[axis]->get_register_addr(axis, TMC2209Reg_SG_RESULT);

    if(reg == NULL)
        return false;

    reg->payload.value = SG_POISON;
    *sg = (uint16_t)tmc[axis]->get_sg_result(axis);

    return reg->payload.value != SG_POISON;
}

// 2 x the Trinamic plugin's per-axis StallGuard4 threshold, i.e. the level the chip itself
// would call a stall. 0 = no threshold set.
static uint16_t stall_level (uint_fast8_t axis)
{
    static const setting_detail_t *sgthrs = NULL;

    float value;

    if(sgthrs == NULL)
        sgthrs = setting_get_details(Setting_AxisExtended0, NULL);

    value = setting_get_float_value(sgthrs, axis);

    return isnan(value) || value <= 0.0f ? 0 : (uint16_t)(2.0f * value);
}

static void trip (uint_fast8_t axis, uint16_t sg)
{
    char msg[48];

    strcpy(msg, "Arm guard: overload on ");
    strcat(msg, axis_letter[axis]);
    strcat(msg, ", SG ");
    strcat(msg, uitoa(sg));
    report_message(msg, Message_Warning);

    if(!(state_get() & (STATE_ALARM|STATE_ESTOP))) {
        mc_reset();
        system_set_exec_alarm(Alarm_MotorFault);
    }
}

static void guard_poll (void *data)
{
    static uint32_t last_ms = 0;
    static int32_t last_pos[N_AXIS] = {0};
    static uint8_t fast[N_AXIS] = {0}, low[N_AXIS] = {0}, backoff[N_AXIS] = {0};

    uint32_t now = hal.get_elapsed_ticks(), dt = now - last_ms;
    uint_fast8_t idx = N_AXIS;

    task_add_delayed(guard_poll, NULL, ARM_GUARD_POLL_MS);

    if(dt == 0)
        return;

    last_ms = now;

    do {
        uint16_t sg, level;
        int32_t pos = sys.position[--idx], delta = pos - last_pos[idx];
        float speed = fabsf((float)delta) * 60000.0f / (settings.axis[idx].steps_per_mm * (float)dt); // deg/min

        last_pos[idx] = pos;

        if(backoff[idx]) {
            backoff[idx]--;
            fast[idx] = low[idx] = 0;
            continue;
        }

        if(tmc[idx] == NULL || speed < guard.min_speed || !tmc[idx]->get_en_pwm_mode(idx)) {
            fast[idx] = low[idx] = 0;
            continue;
        }

        // SG_RESULT is filtered over the last full steps: skip the first poll after the joint got up
        // to speed. This also swallows the jump in the step counter when homing sets the position.
        if(fast[idx] == 0) {
            fast[idx] = 1;
            continue;
        }

        if(!read_sg(idx, &sg)) {
            backoff[idx] = ARM_GUARD_BACKOFF_POLLS;
            continue;
        }

        if(sg < sg_min[idx])
            sg_min[idx] = sg;

        if(bit_istrue(guard.axes.mask, bit(idx)) && (level = stall_level(idx)) && sg <= level) {
            if(++low[idx] >= ARM_GUARD_TRIP_SAMPLES) {
                low[idx] = 0;
                trip(idx, sg);
            }
        } else
            low[idx] = 0;

    } while(idx);
}

// target is in machine coordinates: degrees below each joint's home trip point
static bool checkTravelLimits (float *target, axes_signals_t axes, bool is_cartesian, work_envelope_t *envelope)
{
    bool ok = check_travel_limits(target, axes, is_cartesian, envelope);

    if(ok && guard.link_check && (sys.homed.mask & ARM_LINK_AXES) == ARM_LINK_AXES) {

        float link = 180.0f + (target[Z_AXIS] + ARM_J3_HOME_DEG) - (target[Y_AXIS] + ARM_J2_HOME_DEG);

        if(!(ok = link >= ARM_LINK_MIN_DEG - 0.01f && link <= ARM_LINK_MAX_DEG + 0.01f))
            report_message("Arm guard: angle between the links outside 30..140 deg", Message_Warning);
    }

    return ok;
}

static bool homeMachine (axes_signals_t cycle, axes_signals_t auto_square)
{
    axes_signals_t pressed = limit_signals_merge(hal.limits.get_state());

    if((pressed.mask &= cycle.mask)) {

        char msg[80];
        uint_fast8_t idx;

        strcpy(msg, "Arm guard: limit switch already pressed on");
        for(idx = 0; idx < N_AXIS; idx++) {
            if(bit_istrue(pressed.mask, bit(idx))) {
                strcat(msg, " ");
                strcat(msg, axis_letter[idx]);
            }
        }
        strcat(msg, " - jog it clear, then home");
        report_message(msg, Message_Warning);

        return false;
    }

    return home_machine(cycle, auto_square);
}

static status_code_t set_link_check (setting_id_t id, uint_fast16_t value)
{
    guard.link_check = value != 0;

    return Status_OK;
}

static uint32_t get_link_check (setting_id_t id)
{
    return guard.link_check;
}

static const setting_detail_t guard_settings_detail[] = {
    { Setting_ArmGuard_Axes, Group_MotorDriver, "Arm overload guard", NULL, Format_AxisMask, NULL, NULL, NULL, Setting_NonCore, &guard.axes.mask, NULL, NULL },
    { Setting_ArmGuard_MinSpeed, Group_MotorDriver, "Arm overload guard minimum speed", "deg/min", Format_Decimal, "###0.0", "60", "6000", Setting_NonCore, &guard.min_speed, NULL, NULL },
    { Setting_ArmGuard_LinkCheck, Group_Limits, "Arm link angle check", NULL, Format_Bool, NULL, NULL, NULL, Setting_NonCoreFn, set_link_check, get_link_check, NULL },
};

static const setting_descr_t guard_settings_descr[] = {
    { Setting_ArmGuard_Axes, "Joints that raise alarm 17 when their TMC2209 StallGuard4 reading (the |SG: field of the status report) "
                             "stays at or below 2 x the axis StallGuard4 fast threshold ($200 + axis). Joints not set are only reported." },
    { Setting_ArmGuard_MinSpeed, "Joint speed below which the StallGuard4 reading is ignored: it needs the motor's back-EMF, "
                                 "so it is not valid at standstill or when creeping." },
    { Setting_ArmGuard_LinkCheck, "Refuse targets that put the angle between upper arm and forearm (180 + J3 - J2) outside 30..140 deg. "
                                  "Needs J2 and J3 homed and soft limits enabled." },
};

static void guard_settings_save (void)
{
    hal.nvs.memcpy_to_nvs(nvs_address, (uint8_t *)&guard, sizeof(arm_guard_settings_t), true);
}

static void guard_settings_restore (void)
{
    guard.axes.mask = 0;
    guard.min_speed = ARM_GUARD_MIN_SPEED_DEFAULT;
    guard.link_check = 1;

    guard_settings_save();
}

static void guard_settings_load (void)
{
    if(hal.nvs.memcpy_from_nvs((uint8_t *)&guard, nvs_address, sizeof(arm_guard_settings_t), true) != NVS_TransferResult_OK ||
        (guard.axes.mask & ~AXES_BITMASK) || guard.link_check > 1 ||
         !(guard.min_speed >= ARM_GUARD_MIN_SPEED_MIN && guard.min_speed <= ARM_GUARD_MIN_SPEED_MAX))
        guard_settings_restore();
}

static void onRealtimeReport (stream_write_ptr stream_write, report_tracking_flags_t report)
{
    bool any = false;
    uint_fast8_t idx;

    for(idx = 0; idx < N_AXIS; idx++)
        any = any || sg_min[idx] != SG_NONE;

    if(any) {

        char buf[5 + N_AXIS * 6];

        strcpy(buf, "|SG:");

        for(idx = 0; idx < N_AXIS; idx++) {
            if(idx)
                strcat(buf, ",");
            strcat(buf, sg_min[idx] == SG_NONE ? "-" : uitoa(sg_min[idx]));
            sg_min[idx] = SG_NONE;
        }

        stream_write(buf);
    }

    if(on_realtime_report)
        on_realtime_report(stream_write, report);
}

static void onReportOptions (bool newopt)
{
    on_report_options(newopt);

    if(!newopt)
        report_plugin("Arm guard", "0.02");
}

void arm_guard_init (void)
{
    static setting_details_t setting_details = {
        .settings = guard_settings_detail,
        .n_settings = sizeof(guard_settings_detail) / sizeof(setting_detail_t),
        .descriptions = guard_settings_descr,
        .n_descriptions = sizeof(guard_settings_descr) / sizeof(setting_descr_t),
        .save = guard_settings_save,
        .load = guard_settings_load,
        .restore = guard_settings_restore
    };

    uint_fast8_t idx = N_AXIS;

    do {
        sg_min[--idx] = SG_NONE;
    } while(idx);

    // No .load() here: it may write flash, which hangs the board this early in boot.
    // grbl calls it later; until then the guard runs on the report-only defaults above.
    if((nvs_address = nvs_alloc(sizeof(arm_guard_settings_t))))
        settings_register(&setting_details);

    on_report_options = grbl.on_report_options;
    grbl.on_report_options = onReportOptions;

    on_realtime_report = grbl.on_realtime_report;
    grbl.on_realtime_report = onRealtimeReport;

    check_travel_limits = grbl.check_travel_limits;
    grbl.check_travel_limits = checkTravelLimits;

    home_machine = grbl.home_machine;
    grbl.home_machine = homeMachine;

    task_add_delayed(guard_poll, NULL, 1000);
}

#endif // ARM_GUARD_ENABLE
