# Mac mini tube mount

A 3D-printable enclosure that clamps a Mac mini (127 × 127 × 50 mm) to a 1" (25.4 mm) square tube. The tube channel is built into the cradle's top, so the tube lies flat on the Mac, about 7.5 mm above it. The whole mount is 95 mm tall.
- **Horizontal tube:** the Mac hangs underneath.
- **Vertical tube:** the Mac hangs front-up, with the back-panel cables pointing down.

Four parts, all printed in PETG, with no metal hardware and no supports.

![On a vertical tube](out/macmini/vertical_tube.png)

## Print

The STLs in `out/macmini/stl/` are already in print orientation, sitting on Z = 0. They were sized for a Bambu P1S (256 mm bed).

| File | Color in renders | Print orientation |
|---|---|---|
| `cradle.stl` (with the tube channel) | orange | front face down, brim recommended |
| `gate.stl` | green | inner face down |
| `screw_4a.stl` | yellow | wheel down |
| `pad.stl` | purple | grip face down |

Print `test_thread.stl` and `test_tube.stl` first. They're small coupons that check the thread fit and the tube/gate fit on your printer before you commit to the big parts.

## Assemble

1. Slide the Mac into the cradle from the front until the roof tab clicks over its front edge. The back lip stops it at the rear.
2. Snap the pad onto the tip of screw 4a, then thread 4a into the gate.
3. Lay the tube in the channel on top of the cradle. It runs front-to-back.
4. Slide the gate into the dovetail grooves along the channel's open side, center it, and tighten 4a until the pad grips the tube.

## Rebuild from source

The geometry comes from one Blender script (tested on Blender 5.2):

```bash
blender -b --factory-startup --python build_macmini_mount.py
```

It rebuilds every part, measures fits and printability, writes the STLs and renders to `out/macmini/`, and saves `out/macmini_mount.blend`. Dimensions are constants at the top of the script. For example, `RAD_CL` sets the thread clearance.

[NOTES_macmini.md](NOTES_macmini.md) lists the design decisions, the measured clearances, and the open issues. Check the ones about your Mac and your tube before printing everything.

## Views

| Horizontal tube | Exploded |
|---|---|
| ![](out/macmini/horizontal_tube.png) | ![](out/macmini/exploded.png) |
