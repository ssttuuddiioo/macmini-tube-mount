# Mac mini tube mount

A 3D-printable enclosure that clamps a Mac mini (127 × 127 × 50 mm) to a 1" (25.4 mm) square tube. The clamp mounts on the Mac's square top face to keep it compact:
- **Horizontal tube:** the Mac hangs underneath.
- **Vertical tube:** the Mac stands on edge, flat against the tube.

Every part is printed in PETG, with no metal hardware and no supports.

![On a vertical tube](out/macmini/vertical_tube.png)

## Print

The STLs in `out/macmini/stl/` are already in print orientation, sitting on Z = 0. They were sized for a Bambu P1S (256 mm bed).

| File | Print orientation |
|---|---|
| `cradle.stl` | front face down |
| `clamp_block.stl` | U end down, tube axis up |
| `gate.stl` | inner face down |
| `screw_4a.stl`, `screw_4b.stl` | wheel down |
| `pad.stl` | grip face down |

Print `test_thread.stl` and `test_tube.stl` first. They're small coupons that check the thread fit and the tube/gate fit on your printer before you commit to the big parts.

## Assemble

1. Slide the Mac into the cradle from the front until the roof tab clicks over its front edge. The back lip stops it at the rear.
2. Push the clamp block's diamond tenon into the socket on the cradle's roof. The block fits in four quarter-turns, which pick whether the tube runs front-to-back or across the Mac. Tighten lock screw 4b onto the tenon from the rear of the boss.
3. Snap the pad onto the tip of screw 4a, then thread 4a into the gate.
4. Drop the tube into the U, slide the gate into its dovetail grooves, and tighten 4a until the pad grips the tube. Add zip ties through the slots for backup.

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
