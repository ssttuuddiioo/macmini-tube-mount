# Mac mini tube mount: notes

Script: `build_macmini_mount.py`. Units: 1 BU = 1 mm. Outputs: `out/macmini_mount.blend`,
`out/macmini/*.png`, `out/macmini/stl/*.stl`, `out/macmini/plates/*.3mf`.

Four printed parts: **cradle** (orange, with the tube clamp built in), **nut** (green),
**clamp screw 4a** (yellow), **pad** (purple, the moving jaw).

## Choices

**Layout**
- The tube's bottom face is velcroed to something, so nothing may pass under it or wrap around it.
- The tube lies front-to-back on the cradle's roof, centered over the Mac, about 5 mm from the Mac's top. In use the cradle sits upside-down on the tube:
  - The Mac's weight presses the cradle onto the tube, so the clamp only has to stop sliding and tipping.
  - The Mac's vented underside faces up and stays open. Putting the tube under the floor would have blocked the vented foot.
- Vertical tube: the Mac hangs front-up, so the back-panel cables point down.
- Cradle frame: floor center at origin, Mac front faces -Y, solid side wall on +X.
- Mac clearance is 0.6 mm per side. The Mac rests on two 3 mm rails.

**Clamp (on the cradle roof)**
- Fixed jaw on -X, 5 mm thick. It grips one side face and has a 2 mm-thick lip reaching 2.5 mm over that edge of the velcro face, 0.2 mm clear of it. The lip is the only thing that passes the velcro plane.
- Abutment on +X, flush with the side wall. It holds the nut in a slot open at the back, with a 0.3 mm fit.
- Screw 4a passes through 45° teardrop clearance holes (0.6 mm radial) in the abutment walls, threads through the nut, and pushes the pad against the tube's other side face.
- Everything except the lip stops at least 1.55 mm short of the velcro plane. The closest point is the thumbwheel's top.
- The nut keeps its thread vertical when printed; a thread printed sideways in the cradle would overhang. The screw passing through it keeps it from sliding out of its slot.
- Pad: a 40 × 18 × 27.8 mm block (plus boss) spanning from the tube to the abutment. Nine 45° V-grooves on the face grip the tube. 4a's collar snaps into its socket (lip 8.2 mm over a 9.8 mm cavity, 4 slits) and spins freely.

**Threads (nut + 4a)**
- 12 mm, 2 mm pitch. This is smaller than the original 16 mm so the nut and the thumbwheel fit under the velcro plane.
- Built with the Screw modifier on a triangular profile, which worked on the first try, so no trapezoid fallback was needed.
- Buttress-like profile so it prints without supports. The lower flank is 43.7° from vertical, becoming 44.9° after the internal scale-up. The upper flank is 15° from horizontal.
- Internal thread: a radially scaled-up copy (0.35 mm at the crest), shifted 0.11 mm axially. The helix phase is locked to the screw frame so screw and nut mesh.
- The nut's hole ends get a 45° countersink down to the core.
- On the screw, the thread starts inside the root cone and stops 0.2 mm short of the neck step. Both keep the exact boolean away from coplanar faces, which otherwise leave open edges.
- Screw 4a: 26 × 10 mm knurled wheel (24 V-knurls), a 45° root cone, 24 mm of thread, then a neck and a 9 mm snap collar. The collar is small enough to pass through the nut.

**Cradle**
- Floor cutout: a 112 mm circle under the foot, opened straight back to the rear edge (no ceiling when printed front-face-down).
- Power notch: 30 × 30 mm at rear-left (-X, +Y, seen from the front).
- Retention:
  - Front: a 20 × 30 mm flex tongue in the roof at x = -42, thinned to 2.4 mm, with a 3.5 mm hook.
  - Back: a 45° roof lip.
- Inside corners have 1.5 mm relief channels. Outer long edges have 2 mm chamfers.

**Test pieces**
- `test_thread.stl`: the full nut plus a 15 mm screw stub.
- `test_tube.stl`: a 10 mm slice of the clamp (fixed jaw with lip, roof, abutment with the nut slot). It's cut away from the screw holes, because a flat cut through them trips the exact boolean.

## Measured fits (posed evaluated meshes, both tube orientations)
- Thread flanks: 0.121 mm normal gap. No intersections.
- Screw in its clearance holes 0.575, collar in pad socket 0.3, nut in slot 0.3, pad to cradle 1.9 mm.
- Tube to pad 0.05, tube to fixed jaw 0.05, tube to lip 0.26 mm.
- The Mac sits 0.05 mm above the rails. That offset is only there so the fit check can tell contact apart from interference.

## Open issues
- Thread flank gap is 0.121 mm, tighter than the ~0.2 mm PETG usually likes. Print `plate1_test_pieces.3mf` first. If the thread binds, raise `RAD_CL` (radial clearance).
- Countersinks remove some partial thread at each end of the nut, so full engagement is about 7 of its 10 mm.
- Only the fixed side has a lip. The pad side holds by squeeze alone, because a lip on the pad would stop it printing flat.
- Velcro check: the lip sits 2.5 mm in from one edge of the velcro face and stands 2.2 mm proud. Your velcro must either stop at least 2.5 mm from that edge (a strip narrower than about 20 mm, centered) or be thicker than about 2.2 mm.
- The mount is designed for the velcroed-down case, where gravity seats the Mac. On a vertical tube, the clamp holds the Mac's full 0.7 kg by friction plus the lip. Check it before trusting it.
- The tube direction is fixed front-to-back.
- The fixed jaw's inner root has a 1 mm chamfer, so it needs a tube corner radius of at least 1.7 mm. Standard 1" tube is about 3 mm.
- The nut can only slide out of its slot once the screw is removed. Don't lose it while the screw is out.
- Mac assumptions to check on real hardware:
  - Power button at rear-left.
  - Foot within a 112 mm circle and less than 3 mm proud of the body.
  - Top edge radius small enough for the 3.5 mm hook to catch.
- No elephant-foot chamfer on the cradle's front (bed) edges or the pad's face edges.
- Strength under load hasn't been simulated.
- The tongue-slot tops are 2 mm bridges. These are the only overhangs the checker reports, and they're within the 20 mm limit.
