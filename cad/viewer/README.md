# Interactive arm viewer

`roboruka.html` shows the scheme-C arm built from the CAD itself: `parts.js` holds every
part of `cad/*.FCStd` as a mesh in its own joint frame, plus the motor placements and the
geometry the kinematics need. Only the tool bodies (775, 52 mm spindle) and the gripper
module are simple stand-ins - they are not in the CAD. three.js r128 (MIT) is vendored in
`vendor/`, so the page opens offline straight from the repo:

```bash
xdg-open cad/viewer/roboruka.html
```

X-ray: a click selects a part and draws it again over everything (a second render pass on
layer 1 after clearing depth), shift+wheel sets that part's opacity, a right click makes a
part solid again. The rail's "Рентген" section has the selected part's description and one
opacity slider per group. A new part gets its group from `GROUP_OF` in the page (CAD part
name -> group key); anything not listed lands in "Кисть та інструмент".

Homing ("Хомінг", and the start of "Демо-цикл") runs the firmware's cycle from `CMakeLists.txt`:
J2 + J3 towards +, then J1; seek, 3 deg pull-off, slow locate, pull-off. The limit-switch rockers
and levers turn with the joints: `export_parts.py` works out, from the CAD fingers and rockers, the
rocker's angle against the joint angle near each trip point (`limits` in `parts.js`), and the switch
counts as clicked when that angle is at or below the click angle from `endstop_dims.py`.

After changing any `cad/*.py` model, rebuild its `.FCStd` and then refresh the meshes:

```bash
<FreeCAD.AppImage> freecadcmd cad/viewer/export_parts.py
```

Hosted at **https://web.ibotz.space/roboruka/** (behind the usual *.ibotz.space Google login):
zen4 runs a static nginx container (`web-static`, port 8091, serves `~/www`) and ibotz2's
nginx proxies to it over the VPN - `web.ibotz.space.nginx` is that site's config. Publish a
new version with:

```bash
cad/viewer/deploy_web.sh
```

The same page is also a private claude.ai artifact: https://claude.ai/artifact/T8ELjPK7bbDcdPbRnszxEH
