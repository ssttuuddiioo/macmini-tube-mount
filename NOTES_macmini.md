# Mac mini tube mount — notes

Script: `build_macmini_mount.py`. Units: 1 BU = 1 mm. Outputs: `out/macmini_mount.blend`,
`out/macmini/*.png`, `out/macmini/stl/*.stl`.

## Choices

**Layout**
- Cradle frame: floor center at origin, Mac front faces -Y, solid side wall on +X.
- The connector (socket boss) sits in the middle of the roof, the Mac's square face, so the clamp stacks on the Mac instead of sitting beside it.
  - Horizontal tube: the Mac hangs under it.
  - Vertical tube: the Mac stands on its solid side wall with its roof against the tube.
  - The block's four quarter-turns choose whether the tube runs front-to-back or across the Mac.
- The boss, socket and 4b hole are drawn as if on the side wall, then moved onto the roof with one exact transform (`M_CONN`). Their geometry, fits and print behaviour are unchanged, and Y stays print-up.
- The Mac slides in from the front. The -X side stays open between 4 mm retaining lips on the floor and roof, which keeps the power notch reachable.
- Inside is Mac + 0.6 mm per side. The Mac rests on two 3 mm rails along the side strips, so its bottom sits 7 mm above the bed face.
- Mac placeholder: 12 mm corner radius. Tube placeholder: 3 mm corner radius. Neither is exported.

**Cradle**
- Floor cutout: a 112 mm circle under the foot, opened straight back to the rear edge. With the cradle printed front-face-down, the hole then has no ceiling to bridge. Underside and back stay open.
- Power notch: 30 × 30 mm at rear-left (-X, +Y, seen from the front). It cuts through the floor, rail and lip.
- Retention:
  - Front: a 20 × 30 mm flex tongue in the roof, thinned to 2.4 mm. It sits off-center (x = -42) to clear the boss footprint. Its hook is 3.5 mm deep, with a 41° entry ramp and a square catch 0.6 mm ahead of the Mac face. Deflection is about 2.3 mm, roughly 0.9 % strain.
  - Back: a 45° roof lip that meets the Mac's top-back edge with 0.6 mm clearance.
- Inside corners have 1.5 mm relief channels. Outer long edges have 2 mm chamfers.

**Socket and tenon**
- Printed as a 45° diamond (the square rotated 45°), so both the socket ceiling and the tenon's underside are 45° with no bridges. Four-way indexing is kept.
- Tenon is 20 mm square and 29.5 mm long. Socket is 20.6 mm and 30 mm deep, giving 0.3 mm per side.
- The boss is 34 mm deep. That lets lock screw 4b sit far enough out that its 40 mm wheel clears the roof.

**Lock screw 4b**
- Threads into the rear (+Y) face of the boss, so the hole is vertical in print.
- Its tip presses the tenon's top edge, wedging the tenon into the socket's lower V.

**Clamp block and gate**
- Block base is 14 mm thick. At 5 mm, the tube would hit 4b's wheel in the horizontal orientation.
- U inside is 26.2 mm wide, but 38.2 mm deep instead of 26.2. At the spec depth there's no room for the pad and the screw tip, so I added 12 mm.
- The U's inside corners have 2 mm chamfers. They clear tubes with a corner radius of 2.9 mm or more.
- Gate: 10 mm thick, with half-dovetail tongues 2.3 mm deep. The 45° flank is on the load side, so it pulls the flanges in under load. The gate prints inner-face-down.
- Zip-tie slots: 3 × 6 mm hexagons (pointed ends, no bridge) at y = ±24.5, between the tube and the gate. A tie through a pair wraps the flange tips and gate as backup retention.

**Threads**
- 16 mm, 2 mm pitch. Built with the Screw modifier on a triangular profile: the first method worked, so no trapezoid fallback.
- Two fixes were needed:
  1. Calculate normals on the Screw modifier.
  2. Trim the open-ended helix with the envelope *before* unioning it with the core. Unioning first breaks the exact boolean.
- Profile is buttress-like so it prints without supports:
  - The lower flank is 43.7° from vertical. After the internal scale-up it becomes 44.9°.
  - The upper flank is 15° from horizontal. It faces up in every print orientation used.
- Internal thread: a radially scaled-up copy (×1.0438, giving 0.35 mm at the crest), shifted 0.11 mm axially to even out the flank gaps. The helix phase is locked to the screw frame so screw and hole mesh.
- Open hole ends get a 45° countersink from 1 mm outside the thread down to the core. The 4b hole is blind and ends in a 45° drill point.

**Screws and pad**
- Screws: 40 × 10 mm wheel with 30 V-knurls, 1 mm edge chamfers, and a 2 mm 45° root cone. 4a has 24 mm of thread plus a neck and snap collar. 4b has 18 mm plus a chamfered tip.
- Pad: 40 × 22 × 4 mm with nine 45° V-grooves across the tube. The socket has a 10.2 mm lip over an 11.8 mm cavity, and the boss has 4 slits. 4a's 11 mm collar snaps in and spins freely.

**Test pieces**
- `test_thread.stl`: a 24 mm-wide slice of the gate (full 10 mm thread) plus a 15 mm screw stub.
- `test_tube.stl`: a 10 mm slice of the U plus a 10 mm gate slice.

## Measured fits (posed evaluated meshes, both tube orientations)
- Thread flanks: 0.135 mm normal gap. Radial clearance is 0.35 mm at the crest and 0.29 mm at the root. No intersections.
- Tenon/socket 0.3, gate/grooves 0.3, collar/pad socket 0.3, 4b tip/tenon 0.2, pad/gate 2.8, 4b wheel/tube ≥ 5.1 mm.
- The Mac sits 0.05 mm above the rails and the block 0.05 mm off the boss. These offsets are only there so the fit check can tell contact apart from interference.

## Open issues
- Thread flank gap is 0.135 mm, tighter than the ~0.2 mm PETG usually likes. Print `test_thread.stl` first. If it binds, raise `RAD_CL` (radial clearance).
- Countersinks remove about 1.4 mm of partial thread at each end of the gate, so full engagement is about 7 of its 10 mm.
- 4b locks by friction plus wedging on the tenon edge. It isn't a positive pin; the tenon can only come out once 4b is backed off.
- The gate is held along the tube axis only by the pad's clamping force. Use the zip-tie slots if that isn't enough.
- The U's inner chamfers assume a tube corner radius of 2.9 mm or more. A sharp-cornered tube will sit on them, about 0.2 mm high.
- Mac assumptions to check on real hardware:
  - Power button at rear-left.
  - Foot within a 112 mm circle and less than 3 mm proud of the body.
  - Top edge radius small enough for the 3.5 mm hook to catch.
- No elephant-foot chamfer on the cradle's front (bed) edges or the pad's face edges.
- The tenon root and the boss-to-plate top junction have no fillet. Both are stress corners that I left square to keep the tenon's shoulder seat flat.
- Strength under 0.7 kg hasn't been analyzed. The load runs floor -> 4 mm side wall -> 4 mm roof -> boss, and the -X side is open. A rough hand estimate for the floor cantilever gives about 1.2 MPa, far below PETG's ~50 MPa, but the C-frame hasn't been simulated.
- The tongue-slot tops are 2 mm bridges. These are the only overhangs the checker reports, and they're within the 20 mm limit.
