# Mac mini tube mount: notes

Script: `build_macmini_mount.py`. Units: 1 BU = 1 mm. Outputs: `out/macmini_mount.blend`,
`out/macmini/*.png`, `out/macmini/stl/*.stl`.

Four printed parts: **cradle** (orange, with the tube channel built in), **gate** (green),
**clamp screw 4a** (yellow), **pressure pad** (purple).

## Choices

**Layout**
- Cradle frame: floor center at origin, Mac front faces -Y, solid side wall on +X.
- The tube lies front-to-back directly on the roof (the Mac's square face), in a U-channel that is part of the cradle. The tube's underside is about 7.5 mm above the Mac's top. The whole mount is 95.4 mm tall.
  - Horizontal tube: the Mac hangs under it.
  - Vertical tube: the Mac hangs front-up, so the back-panel cables point down.
- The tube direction is fixed front-to-back. A channel running across the roof would print as a large flat overhang, since the cradle prints standing on its front face.
- The U opens toward +X. The gate closes that side, and 4a's wheel sits beside the Mac's +X side wall instead of on top.
- Mac clearance is 0.6 mm per side. The Mac rests on two 3 mm rails.
- Mac placeholder: 12 mm corner radius. Tube placeholder: 3 mm corner radius. Neither is exported.

**Cradle**
- Floor cutout: a 112 mm circle under the foot, opened straight back to the rear edge, so it has no ceiling when printed front-face-down. The underside and back stay open.
- Power notch: 30 × 30 mm at rear-left (-X, +Y, seen from the front).
- Retention:
  - Front: a 20 × 30 mm flex tongue in the roof at x = -42, clear of the channel. It's thinned to 2.4 mm. The hook is 3.5 mm deep, with a 41° entry ramp and a square catch 0.6 mm ahead of the Mac face.
  - Back: a 45° roof lip that meets the Mac's top-back edge with 0.6 mm clearance.
- Inside corners have 1.5 mm relief channels. Outer long edges have 2 mm chamfers.

**Tube channel (part of the cradle)**
- 26.2 mm tall inside (roof to cap), and 38.2 mm deep from back wall to gate to leave room for the pad and screw tip.
- Runs the full 135 mm depth of the cradle. The back wall and cap are 5 mm thick.
- The channel floor is raised 2 mm above the roof so the lower dovetail groove leaves roof material under it.
- The inside corners have 2 mm chamfers. They clear tubes with a corner radius of 2.9 mm or more.
- The channel profile is the old clamp block's U cross-section, placed on the roof by a pure translation (`M_U`).

**Gate**
- 60 mm long and 10 mm thick, with half-dovetail tongues 2.3 mm deep. The 45° flank is on the load side, so it pulls the cap and roof toward each other under load.
- Slides in from either end of the channel. Prints inner-face-down.
- 0.3 mm sliding fit in the grooves.

**Threads (gate + 4a)**
- 16 mm, 2 mm pitch. Built with the Screw modifier on a triangular profile, which worked on the first try, so no trapezoid fallback was needed.
- Two fixes were needed:
  1. Calculate normals on the Screw modifier.
  2. Trim the open-ended helix before unioning it with the core.
- Buttress-like profile so it prints without supports:
  - The lower flank is 43.7° from vertical, becoming 44.9° after the internal scale-up.
  - The upper flank is 15° from horizontal.
- Internal thread: a radially scaled-up copy (×1.0438, giving 0.35 mm at the crest), shifted 0.11 mm axially to even out the flank gaps. The helix phase is locked to the screw frame so screw and hole mesh.
- Hole ends get a 45° countersink from 1 mm outside the thread down to the core.

**Screw and pad**
- 4a: 40 × 10 mm knurled wheel (30 V-knurls, 1 mm edge chamfers), a 2 mm 45° root cone, 24 mm of thread, then a neck and snap collar.
- Pad: 40 × 22 × 4 mm with nine 45° V-grooves across the tube. The socket has a 10.2 mm lip over an 11.8 mm cavity, with 4 slits. 4a's 11 mm collar snaps in and spins freely.

**Removed when the clamp block merged into the cradle**
- The clamp block, the diamond tenon and socket, the socket boss, and lock screw 4b.
- The zip-tie slots. Through the roof they would open into the Mac's cavity.

**Test pieces**
- `test_thread.stl`: a 24 mm-wide slice of the gate (full 10 mm thread) plus a 15 mm screw stub.
- `test_tube.stl`: a 10 mm slice of the cradle's channel (roof, U and a stub of side wall) plus a 10 mm gate slice. The gate slice is taken from past the threaded hole, because a flat cut through the helix trips the exact boolean.

## Measured fits (posed evaluated meshes, both tube orientations)
- Thread flanks: 0.135 mm normal gap. Radial clearance is 0.35 mm at the crest and 0.29 mm at the root. No intersections.
- Gate in grooves 0.3, collar in pad socket 0.3, pad to gate 2.8, 4a wheel to cradle 5.1, 4a wheel to tube 4.35 mm.
- The Mac sits 0.05 mm above the rails. That offset is only there so the fit check can tell contact apart from interference.

## Open issues
- Thread flank gap is 0.135 mm, tighter than the ~0.2 mm PETG usually likes. Print `test_thread.stl` first. If it binds, raise `RAD_CL` (radial clearance).
- Countersinks remove about 1.4 mm of partial thread at each end of the gate, so full engagement is about 7 of its 10 mm.
- The gate is held along the tube axis only by the pad's clamping force. With the zip-tie slots gone, there is no backup.
- The tube direction is fixed front-to-back. On a vertical tube the Mac hangs front-up; you can't mount it on edge.
- The U's inner chamfers assume a tube corner radius of 2.9 mm or more. A sharp-cornered tube will sit on them, about 0.2 mm high.
- The lower dovetail groove leaves about 2.2 mm between it and the roof/side-wall relief channel, just under the 2.4 mm minimum wall.
- The Mac's center sits about 31 mm to the side of the tube, so it applies a small twisting load on the clamp.
- Mac assumptions to check on real hardware:
  - Power button at rear-left.
  - Foot within a 112 mm circle and less than 3 mm proud of the body.
  - Top edge radius small enough for the 3.5 mm hook to catch.
- No elephant-foot chamfer on the cradle's front (bed) edges or the pad's face edges.
- Strength under 0.7 kg hasn't been analyzed. The load runs floor -> 4 mm side wall -> roof -> channel. A rough hand estimate for the floor cantilever gives about 1.2 MPa, far below PETG's ~50 MPa, but the C-frame hasn't been simulated.
- The tongue-slot tops are 2 mm bridges. These are the only overhangs the checker reports, and they're within the 20 mm limit.
