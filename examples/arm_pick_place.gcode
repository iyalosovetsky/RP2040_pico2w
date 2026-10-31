; Pick-and-place demo for the ROBOT_ARM build, scheme C (parallelogram), gripper on
; bracket Z. Joint angles in degrees: X = J1 base, Y = J2 upper arm above horizontal,
; Z = J3 forearm above horizontal (absolute), A = J4 tool yaw. Generated with
;   tools/arm_ik.py ik <x> <y> <z>          (tool point in mm, table frame)
; and streamed with
;   tools/arm_ik.py send examples/arm_pick_place.gcode --port /dev/ttyACM0
G90 G21
M102                                         ; open gripper (waits for queued motion)
G4 P0.5
G1 X0.000 Y100.000 Z-20.000 A0.000 F900      ; park (175, 0, 104)
G1 X16.699 Y83.545 Z-26.704 A0.000 F900      ; above pick (200, 60, 90)
G1 X16.699 Y67.995 Z-50.871 A0.000 F900      ; pick (200, 60, 35)
M103                                         ; close gripper once the arm has arrived
G4 P0.8                                      ; give the servo time to close
G1 X16.699 Y83.545 Z-26.704 A0.000 F900      ; lift (200, 60, 90)
G1 X-49.086 Y87.620 Z-27.055 A0.000 F900     ; above place (130, -150, 90)
G1 X-49.086 Y72.970 Z-50.265 A0.000 F900     ; place (130, -150, 40)
M102                                         ; release
G4 P0.5
G1 X-49.086 Y87.620 Z-27.055 A0.000 F900     ; lift (130, -150, 90)
G1 X0.000 Y100.000 Z-20.000 A0.000 F900      ; park
