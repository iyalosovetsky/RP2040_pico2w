# Interactive arm viewer

`roboruka.html` is a self-contained three.js model of the scheme-C arm (PG27 joints,
51211 base, 609Z pivots, interchangeable tools on the J4 flange). J4 sits either
vertically (Z bracket: turns the tool about the vertical) or across the arm like J3
(Y bracket: tilts the tool, J4 axis through the tool's centre of mass). It opens offline
straight from the repo - three.js r128 (MIT) is vendored in `vendor/`:

```bash
xdg-open cad/viewer/roboruka.html
```

Dimensions follow `cad/base.FCStd` and `cad/turret.FCStd` (shoulder axis at 155 mm);
links further out are still the proposed L2 = L3 = 140, crank 35 until they are modelled.
The same page is published as a private artifact: https://claude.ai/artifact/T8ELjPK7bbDcdPbRnszxEH
