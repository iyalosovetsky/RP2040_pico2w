; Pick-and-place demo for the ROBOT_ARM build. Joint angles in degrees:
; X = base, Y = shoulder, Z = elbow, A = wrist. Generate poses with
;   tools/arm_ik.py ik <x> <y> <z> --pitch -90
; and stream with
;   tools/arm_ik.py send examples/arm_pick_place.gcode --port /dev/ttyACM0
G90 G21
M102                                  ; open gripper (waits for queued motion)
G4 P0.5
G1 X0 Y90 Z-90 A0 F900                ; park pose
G1 X14.036 Y63.723 Z-85.028 A-68.695  ; above pick point (200, 50, 120)
M103                                  ; close gripper once the arm has arrived
G4 P0.8                               ; give the servo time to close
G1 X0 Y90 Z-90 A0                     ; lift back to park
G1 X-30 Y63.723 Z-85.028 A-68.695     ; swing to place point
M102                                  ; release
G4 P0.5
G1 X0 Y90 Z-90 A0                     ; park
