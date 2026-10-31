# Interactive arm viewer

`roboruka.html` shows the scheme-C arm built from the CAD itself: `parts.js` holds every
part of `cad/*.FCStd` as a mesh in its own joint frame, plus the motor placements and the
geometry the kinematics need. Only the tool bodies (775, 52 mm spindle) and the gripper
module are simple stand-ins - they are not in the CAD. three.js r128 (MIT) is vendored in
`vendor/`, so the page opens offline straight from the repo:

```bash
xdg-open cad/viewer/roboruka.html
```

After changing any `cad/*.py` model, rebuild its `.FCStd` and then refresh the meshes:

```bash
<FreeCAD.AppImage> freecadcmd cad/viewer/export_parts.py
```

The same page is published as a private artifact: https://claude.ai/artifact/T8ELjPK7bbDcdPbRnszxEH
