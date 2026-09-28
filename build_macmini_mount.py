"""3D-printable Mac mini enclosure that clamps to a 1" square tube (vertical or horizontal).

Units: 1 Blender unit = 1 mm. All parts PETG on a Bambu P1S.
Parts: cradle (with the tube U-channel built into its roof), gate, thumbwheel screw 4a, pressure pad.
Every part is a base mesh plus live Boolean modifiers whose helper objects are parented
to it; modifiers are only applied on the throwaway copies written to STL.

Frames: cradle frame = world (floor center at origin, Mac front faces -Y, side wall on +X).
The tube lies front-to-back directly on the roof (the Mac's square face) in a U-channel that
opens toward +X; the gate closes it and 4a's wheel sits off the +X side. Horizontal tube: the
Mac hangs under it. Vertical tube: the Mac hangs front-up, back-panel cables pointing down.
U frame: the channel profile drawn in the old clamp-block frame (U opens +X, tube along Y),
placed on the roof by the pure translation M_U.
Screw frame: wheel bottom at z=0, thread runs +Z toward the tip.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.scene import new_scene
from lib.geometry import material
from lib.render import camera_rig, studio_look, render_views

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
RDIR = os.path.join(OUT, "macmini")
SDIR = os.path.join(RDIR, "stl")
PDIR = os.path.join(RDIR, "plates")

# ---- params (mm) ----
MAC = (127.0, 127.0, 50.0)        # Mac mini W x D x H
MAC_R = 12.0                      # placeholder corner radius (plan view)
TUBE = 25.4                       # square tube
TUBE_R = 3.0                      # tube corner radius assumed by the U's inner chamfers
CL = 0.6                          # Mac clearance per side
WALL = 4.0                        # cradle walls
RAIL_H = 3.0                      # standoff rails under the Mac
RAIL_X = (57.0, 63.5)             # rail span from center, each side
FOOT_R = 56.0                     # floor cutout radius (vented foot)
LIP = 4.0                         # open-side retaining lips
HOOK = 3.5                        # snap hook depth below the roof
TONGUE_W, TONGUE_L, TONGUE_T, SLOT = 20.0, 30.0, 2.4, 2.0
TONGUE_X = -42.0                  # snap tongue center, clear of the U-channel
RELIEF_R = 1.5                    # inside-corner relief channels
NOTCH = (-70.0, -40.0, 40.0, 70.0)  # power-button notch x0, x1, y0, y1 (rear-left)
FIT = 0.3                         # sliding fit: gate/dovetail
B_BASE = 5.0                      # U back wall
U_IN = 26.2                       # U inside width (roof to cap)
U_EXTRA = 12.0                    # extra U depth for the pad + screw tip
U_WALL = 5.0                      # U cap and floor thickness
PLINTH = 2.0                      # U floor raised above the roof so the dovetail groove leaves roof under it
GATE_T, GATE_L = 10.0, 60.0       # gate thickness (= thread engagement) and length
DOVE = 2.3                        # dovetail tongue reach into each flange
CHAMF = 2.0                       # stress-corner chamfers
# threads: 16 mm, 2 mm pitch, printable buttress-style triangle (lower flank < 45 deg)
PITCH, R_MAJ, R_CORE, R_BASE = 2.0, 8.0, 6.7, 6.5
LOW_TAN, UP_TAN = 0.955, math.tan(math.radians(15))   # dr/dz of lower flank, dz/dr of upper
RAD_CL = 0.35                     # radial clearance at the crest
K_INT = (R_MAJ + RAD_CL) / R_MAJ  # internal thread = radially scaled-up copy
DZ_INT = 0.11                     # axial shift of the internal thread to even out flank gaps
PHASE = 0.0137                    # keeps helix vertices off part faces
STEPS = 48                        # helix / lathe segments per turn
LEAD = 1.0                        # thread lead-in chamfers
WHEEL_R, WHEEL_T, KNURL = 20.0, 10.0, 30
L_4A, L_STUB = 24.0, 15.0
PAD = (40.0, 22.0, 4.0)           # along tube, across, thick
PAD_BOSS_R, PAD_BOSS_H = 8.5, 6.0
RES = 500
DEBUG = False                     # print where overhangs / open edges are

# ---- derived layout ----
IX = MAC[0] / 2 + CL              # 64.1 inner half-width
IY = MAC[1] / 2 + CL
OX = IX + WALL                    # 68.1
Z_FLOOR = WALL
Z_RAIL = Z_FLOOR + RAIL_H
Z_ROOF = Z_RAIL + MAC[2] + 2 * CL  # roof underside
Z_TOP = Z_ROOF + WALL
Y_FRONT, Y_BACK = -(IY + 4.0), IY + 3.0
G0 = B_BASE + U_IN + U_EXTRA      # gate inner face (U frame)
FL_TIP = G0 + GATE_T + 2.0        # U flange tips
TUBE_X0 = B_BASE + 0.05           # tube face against the back wall
PAD_X0 = TUBE_X0 + TUBE + 0.05    # pad face against the tube
U_X = OX - FL_TIP                 # U frame origin: flange tips flush with the +X side wall
U_Z = Z_TOP + PLINTH + U_IN / 2   # U frame origin height: channel floor PLINTH above the roof


def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def from_bmesh(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def prism(name, pts, axis, a0, a1):
    """Extrude a 2D polygon. axis 'Z': pts are (x,y); 'Y': (x,z); 'X': (y,z)."""
    to3 = {"Z": lambda u, v, w: (u, v, w), "Y": lambda u, v, w: (u, w, v),
           "X": lambda u, v, w: (w, u, v)}[axis]
    bm = bmesh.new()
    lo = [bm.verts.new(to3(u, v, a0)) for u, v in pts]
    hi = [bm.verts.new(to3(u, v, a1)) for u, v in pts]
    n = len(pts)
    bm.faces.new(lo)
    bm.faces.new(hi[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    return from_bmesh(name, bm)


def lathe(name, prof, n=STEPS):
    """Revolve (r, z) points about Z. First and last points must sit on the axis (r=0)."""
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        if r == 0:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / n),
                                        r * math.sin(2 * math.pi * i / n), z)) for i in range(n)])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[i], b[0], a[j]))
            else:
                bm.faces.new((a[i], a[j], b[j], b[i]))
    return from_bmesh(name, bm)


def rounded_rect(w, d, r, seg=8):
    pts = []
    for cx, cy, a0 in ((w/2 - r, d/2 - r, 0), (-w/2 + r, d/2 - r, 90),
                       (-w/2 + r, -d/2 + r, 180), (w/2 - r, -d/2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def helper(o, parent, kind="cut"):
    """Hide a boolean operand from renders and make it follow its part."""
    o.parent = parent
    o.hide_render = True
    o.display_type = "WIRE"
    if kind:
        coll_for(parent, kind).objects.link(o)
    return o


def coll_for(part, kind):
    """Per-part operand collection ('add' unions before 'cut' differences)."""
    name = f"{part.name}_{kind}"
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        b = part.modifiers.new(kind, "BOOLEAN")
        b.operation = "UNION" if kind == "add" else "DIFFERENCE"
        b.solver, b.operand_type, b.collection = "EXACT", "COLLECTION", c
        if kind == "add":          # unions first
            part.modifiers.move(len(part.modifiers) - 1, 0)
    return c


def boolean(o, op, other, tolerant=False):
    b = o.modifiers.new(op.lower(), "BOOLEAN")
    b.operation, b.solver, b.object, b.use_hole_tolerant = op, "EXACT", other, tolerant
    return b


# ---- threads ----
def helix(name, z0, z1, k, dz, env_prof):
    """Screw-modifier thread on a triangular profile, trimmed to env_prof by a boolean.
    k scales the profile radially (internal thread = scaled-up copy of the external one)."""
    zc = PITCH * math.floor((z0 - 3) / PITCH) + PHASE + dz   # phase fixed to the screw frame, not z0
    tri = [(R_BASE * k, 0, zc - (R_MAJ - R_BASE) / LOW_TAN), (R_MAJ * k, 0, zc),
           (R_BASE * k, 0, zc + (R_MAJ - R_BASE) * UP_TAN)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(tri, [], [(0, 1, 2)])
    h = link(bpy.data.objects.new(name, me))
    s = h.modifiers.new("Screw", "SCREW")
    s.axis, s.angle, s.screw_offset = "Z", 2 * math.pi, PITCH
    s.steps = s.render_steps = STEPS
    s.iterations = math.ceil((z1 - z0 + 6) / PITCH)
    s.use_normal_calculate = True
    env = helper(lathe(name + "_env", env_prof), h, None)
    boolean(h, "INTERSECT", env, tolerant=True)   # trim first: the open helix ends fall outside
    return h


def thread_cutter(name, za, zb, blind=False):
    """Internal thread for a screw whose frame this object shares: za/zb are the hole's
    entry/exit faces along screw z. Open ends get a 45-degree countersink running from
    R_MAJ+LEAD at the face straight down to the core (no flat shelf to overhang);
    a blind hole ends in a 45-degree drill point instead."""
    R, Rc = R_MAJ * K_INT, R_CORE * K_INT
    cs = R + LEAD - Rc                                  # countersink depth from face to core
    prof = [(0, za - 1), (R + LEAD + 1, za - 1), (Rc, za + cs)]
    if blind:
        prof += [(Rc, zb), (0, zb + Rc)]
    else:
        prof += [(Rc, zb - cs), (R + LEAD + 1, zb + 1), (0, zb + 1)]
    core = lathe(name, prof)
    h = helix(name + "_helix", za - 1, zb + 1, K_INT, DZ_INT,
              [(0, za - 1), (R + 0.5, za - 1), (R + 0.5, zb), (0, zb)])
    helper(h, core, "add")
    return core


def build_screw(name, L, collar):
    """Thumbwheel screw, wheel-down. collar=True adds the neck + snap collar for the pad."""
    ze = 12 + L
    prof = [(0, 9), (WHEEL_R / 2, 9), (WHEEL_R / 2, 10), (R_MAJ, 12), (R_CORE, 12)]
    if collar:
        prof += [(R_CORE, ze), (4, ze), (4, ze + 2.5), (5.5, ze + 4), (5.5, ze + 5), (4, ze + 6.5), (0, ze + 6.5)]
    else:
        prof += [(R_CORE, ze - 1), (R_CORE - 1, ze), (0, ze)]
    body = lathe(name, prof)
    knurl = [((WHEEL_R if i % 2 == 0 else WHEEL_R - 1.2) * math.cos(math.pi * i / KNURL),
              (WHEEL_R if i % 2 == 0 else WHEEL_R - 1.2) * math.sin(math.pi * i / KNURL))
             for i in range(2 * KNURL)]
    wheel = prism(name + "_wheel", knurl, "Z", 0, WHEEL_T)
    wenv = helper(lathe(name + "_wheel_env", [(0, 0), (WHEEL_R - 1, 0), (WHEEL_R + 1, 2),
                                              (WHEEL_R + 1, WHEEL_T - 2), (WHEEL_R - 1, WHEEL_T), (0, WHEEL_T)]), wheel, None)
    boolean(wheel, "INTERSECT", wenv)
    helper(wheel, body, "add")
    h = helix(name + "_helix", 12, ze, 1.0, 0.0,
              [(0, 12), (R_MAJ + 0.3, 12), (R_MAJ + 0.3, ze - LEAD - 0.5), (R_MAJ - LEAD, ze - 0.2), (0, ze - 0.2)])
    helper(h, body, "add")
    return body


def build_pad():
    """Pressure pad, face (z=0) down. Snap socket takes 4a's collar; V-grooves grip the tube."""
    L, W, T = PAD
    pad = prism("pad", [(-L/2, -W/2), (L/2, -W/2), (L/2, W/2), (-L/2, W/2)], "Z", 0, T)
    helper(lathe("pad_boss", [(0, T - 0.5), (PAD_BOSS_R, T - 0.5), (PAD_BOSS_R, T + PAD_BOSS_H), (0, T + PAD_BOSS_H)]), pad, "add")
    top = T + PAD_BOSS_H
    helper(lathe("pad_socket", [(0, T), (5.9, T), (5.9, 7.0), (5.1, 7.8), (5.1, 8.8), (5.1 + top + 1 - 8.8, top + 1), (0, top + 1)]), pad)
    for i in range(4):
        a = math.pi / 2 * i
        c, s = math.cos(a), math.sin(a)
        pts = [(c * r - s * w, s * r + c * w) for r, w in ((4.5, -0.5), (PAD_BOSS_R + 1, -0.5), (PAD_BOSS_R + 1, 0.5), (4.5, 0.5))]
        helper(prism(f"pad_slit{i}", pts, "Z", T + 2.0, top + 1), pad)
    for i in range(9):
        x = -16 + 4 * i
        helper(prism(f"pad_groove{i}", [(x - 0.6, -0.1), (x + 0.6, -0.1), (x, 0.5)], "Y", -W/2 - 1, W/2 + 1), pad)
    return pad


# ---- frames ----
X_4A_W = PAD_X0 + 4.3 + 12 + L_4A + 6.5        # 4a wheel bottom (U x); collar tip 0.3 above the pad socket floor
M_U = Matrix.Translation((U_X, 0, U_Z))        # U frame in the cradle frame (translation only: no rotation noise)
M_4A = Matrix.Translation((X_4A_W, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, "Y")      # screw z -> -X
M_PAD = Matrix.Translation((PAD_X0, 0, 0)) @ Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_4x4()


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ---- parts ----
def build_cradle():
    """Open sleeve: floor, roof, side wall (+X). Front/back open, -X open between retaining lips.
    The tube U-channel is built onto the roof."""
    c = CHAMF
    pts = [(-OX, c), (-OX + c, 0), (OX - c, 0), (OX, c), (OX, Z_TOP - c), (OX - c, Z_TOP),
           (-OX + c, Z_TOP), (-OX, Z_TOP - c), (-OX, Z_ROOF - LIP), (-IX, Z_ROOF - LIP), (-IX, Z_ROOF),
           (IX, Z_ROOF), (IX, Z_FLOOR), (-IX, Z_FLOOR), (-IX, Z_RAIL + LIP), (-OX, Z_RAIL + LIP)]
    cr = prism("cradle", pts, "Y", Y_FRONT, Y_BACK)
    add = lambda o: helper(o, cr, "add")
    cut = lambda o: helper(o, cr)
    for s in (1, -1):
        x0, x1 = sorted((s * RAIL_X[0], s * RAIL_X[1]))
        add(prism(f"rail{s:+d}", [(x0, Z_FLOOR - 0.5), (x1, Z_FLOOR - 0.5), (x1, Z_RAIL), (x0, Z_RAIL)], "Y", Y_FRONT, Y_BACK))
    # snap hook under the tongue tip: 41-degree entry ramp, square catch face 0.6 mm ahead of the Mac
    add(prism("hook", [(Y_FRONT, Z_ROOF + 0.3), (Y_FRONT, Z_ROOF), (-IY, Z_ROOF - HOOK), (-IY, Z_ROOF + 0.3)],
              "X", TONGUE_X - TONGUE_W / 2 + 0.1, TONGUE_X + TONGUE_W / 2 - 0.1))
    # rear stop: 45-degree lip that meets the Mac's top-back edge with 0.6 mm clearance
    y0 = IY - 1.6
    add(prism("back_lip", [(y0, Z_ROOF + 0.4), (Y_BACK, Z_ROOF + 0.4 - (Y_BACK - y0)), (Y_BACK, Z_ROOF + 0.4)],
              "X", -IX - 0.4, IX + 0.4))
    # tube U-channel on the roof, full cradle depth, opening toward +X; extruded along Y so it
    # prints front-face-down like the rest of the sleeve. Floor corners stay square: they merge into the roof.
    c, h, o = CHAMF, U_IN / 2, U_IN / 2 + U_WALL
    u = prism("u_channel", [(0, -o), (FL_TIP, -o), (FL_TIP, -h), (B_BASE + c, -h), (B_BASE, -h + c),
                            (B_BASE, h - c), (B_BASE + c, h), (FL_TIP, h), (FL_TIP, o - c), (FL_TIP - c, o),
                            (c, o), (0, o - c)], "Y", Y_FRONT, Y_BACK)
    u.matrix_world = M_U
    add(u)
    k = G0 + 6 - (h - FIT) + FIT * math.sqrt(2)          # x - z of the offset dovetail flank
    zi, zo = h - 0.6, h - FIT + DOVE + FIT
    for s in (1, -1):
        g = [(G0 - FIT, zi), (G0 - FIT, zo), (zo + k, zo), (zi + k, zi)]
        groove = prism(f"groove{s:+d}", [(x, s * z) for x, z in g], "Y", Y_FRONT - 1, Y_BACK + 1)
        groove.matrix_world = M_U
        cut(groove)
    arc = [(FOOT_R * math.cos(-math.pi * i / 24), FOOT_R * math.sin(-math.pi * i / 24)) for i in range(25)]
    cut(prism("foot_cutout", arc + [(-FOOT_R, Y_BACK + 2), (FOOT_R, Y_BACK + 2)], "Z", -1, Z_FLOOR + 0.5))
    x0, x1, y0, y1 = NOTCH
    cut(prism("power_notch", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "Z", -1, Z_RAIL + LIP + 1))
    for i, (x, z) in enumerate(((IX, Z_FLOOR), (IX, Z_ROOF), (-IX, Z_FLOOR), (-IX, Z_ROOF))):
        cut(prism(f"relief{i}", circle(x, z, RELIEF_R, 16), "Y", Y_FRONT - 1, Y_BACK + 1))
    for s in (1, -1):
        x0, x1 = sorted((TONGUE_X + s * TONGUE_W / 2, TONGUE_X + s * (TONGUE_W / 2 + SLOT)))
        cut(prism(f"tongue_slot{s:+d}", [(x0, Y_FRONT - 1), (x1, Y_FRONT - 1), (x1, Y_FRONT + TONGUE_L), (x0, Y_FRONT + TONGUE_L)],
                  "Z", Z_ROOF - HOOK - 1, Z_TOP + 1))
    zt, yr = Z_ROOF + TONGUE_T, Y_FRONT + TONGUE_L
    cut(prism("tongue_thin", [(Y_FRONT - 1, zt), (yr, zt), (yr + Z_TOP + 1 - zt, Z_TOP + 1), (Y_FRONT - 1, Z_TOP + 1)],
              "X", TONGUE_X - TONGUE_W / 2 - SLOT / 2, TONGUE_X + TONGUE_W / 2 + SLOT / 2))
    return cr


def build_gate():
    """Gate bar: half-dovetail tongues (45-degree flank on the load side), 4a thread in the middle."""
    t, d, w = U_IN / 2 - FIT, DOVE, 6.0
    pts = [(G0, -t - d), (G0 + w + d, -t - d), (G0 + w, -t), (G0 + GATE_T, -t),
           (G0 + GATE_T, t), (G0 + w, t), (G0 + w + d, t + d), (G0, t + d)]
    ga = prism("gate", pts, "Y", -GATE_L / 2, GATE_L / 2)
    hole = thread_cutter("gate_hole", X_4A_W - (G0 + GATE_T), X_4A_W - G0)
    hole.matrix_world = M_4A
    helper(hole, ga)
    return ga


# ---- checks ----
def eval_bm(o, mat=None):
    """Evaluated (modifiers applied) mesh as a bmesh, transformed by mat (default: world)."""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    bm = bmesh.new()
    bm.from_mesh(oe.to_mesh())
    oe.to_mesh_clear()
    bm.transform(o.matrix_world if mat is None else mat)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return bm


def gap(a, b):
    """(intersecting triangle pairs, min vertex-to-surface distance) between two posed parts."""
    ba, bb = eval_bm(a), eval_bm(b)
    ta, tb = BVHTree.FromBMesh(ba), BVHTree.FromBMesh(bb)
    hits = len(ta.overlap(tb))
    d = min(min(tb.find_nearest(v.co)[3] for v in ba.verts), min(ta.find_nearest(v.co)[3] for v in bb.verts))
    ba.free(); bb.free()
    return hits, d


def print_check(bm):
    """Manifold, bed face and overhang stats for a mesh already in print orientation on z=0."""
    bad = sum(1 for e in bm.edges if not e.is_manifold)
    bed = sum(f.calc_area() for f in bm.faces if f.normal.z < -0.999 and max(v.co.z for v in f.verts) < 0.01)
    lim = -math.sin(math.radians(46))                  # normal z of a face 46 deg off vertical (1 deg slack)
    over, span, where = 0.0, 0.0, []
    for f in bm.faces:
        if f.normal.z < lim and max(v.co.z for v in f.verts) > 0.01:
            over += f.calc_area()
            where.append((f.calc_area(), f.calc_center_median(), f.normal.z))
            if f.normal.z < -0.99:                      # flat ceiling = bridge; span is its short side
                xs, ys = [v.co.x for v in f.verts], [v.co.y for v in f.verts]
                span = max(span, min(max(xs) - min(xs), max(ys) - min(ys)))
    if DEBUG:
        for a, c, nz in sorted(where, key=lambda w: -w[0])[:4]:
            print(f"      overhang {a:6.1f} mm2 at {tuple(round(x, 1) for x in c)} nz {nz:.3f}")
        es = [e for e in bm.edges if not e.is_manifold]
        if es:
            cs = [(e.verts[0].co + e.verts[1].co) / 2 for e in es]
            print("      bad edges span", [(round(min(c[i] for c in cs), 1), round(max(c[i] for c in cs), 1)) for i in range(3)])
    return bad, bed, over, span


# ---- plate files ----
BED, BED_MARGIN, GAP = 256.0, 5.0, 10.0
# (source object, name shown in the slicer with its per-part settings, front-left corner on the bed)
PLATES = {
    "plate1_test_pieces": [
        ("test_gate_slice", "test gate thread - 100% infill", (20, 108)),
        ("screw_stub", "test screw stub - 100% infill", (65, 108)),
        ("test_u_slice", "test channel slice - 4 walls 35% infill", (120, 108)),
        ("test_u_gate_slice", "test gate slice - 100% infill", (195, 108)),
    ],
    "plate2_parts": [
        ("cradle", "cradle - 4 walls 35% infill, brim", (15, 15)),
        ("screw_4a", "screw_4a - 100% infill", (170, 15)),
        ("gate", "gate - 100% infill", (170, 70)),
        ("pad", "pad - 100% infill", (15, 130)),
    ],
}


def write_3mf(path, placed):
    """Minimal core-spec 3MF: one object per part, each placed on the bed by its build item.
    placed: (label, (verts, tris, size), (x, y) front-left corner). Checks the layout first."""
    import zipfile
    from xml.sax.saxutils import quoteattr
    boxes = []
    for label, (_, _, size), (x, y) in placed:
        assert x >= BED_MARGIN and y >= BED_MARGIN and x + size.x <= BED - BED_MARGIN and y + size.y <= BED - BED_MARGIN, \
            f"{label} leaves the bed"
        assert size.z <= BED, f"{label} too tall"
        for l2, (x2, y2, w2, d2) in boxes:
            assert x + size.x + GAP <= x2 or x2 + w2 + GAP <= x or y + size.y + GAP <= y2 or y2 + d2 + GAP <= y, \
                f"{label} is within {GAP} mm of {l2}"
        boxes.append((label, (x, y, size.x, size.y)))
    res, build = [], []
    for i, (label, (verts, tris, _), (x, y)) in enumerate(placed, 1):
        vx = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in verts)
        tr = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
        res.append(f'<object id="{i}" type="model" name={quoteattr(label)}><mesh><vertices>{vx}</vertices>'
                   f'<triangles>{tr}</triangles></mesh></object>')
        build.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(res)}</resources><build>{"".join(build)}</build></model>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    print(f"  {os.path.basename(path)}: " + ", ".join(label.split(" - ")[0] for label, _, _ in placed))


# ---- scene ----
def main():
    new_scene()
    os.makedirs(SDIR, exist_ok=True)
    us = bpy.context.scene.unit_settings
    us.system, us.scale_length, us.length_unit = "METRIC", 0.001, "MILLIMETERS"

    P = {"cradle": build_cradle(), "gate": build_gate(),
         "screw_4a": build_screw("screw_4a", L_4A, True), "pad": build_pad()}
    colors = {"cradle": (0.85, 0.45, 0.1), "gate": (0.15, 0.6, 0.3),
              "screw_4a": (0.9, 0.75, 0.1), "pad": (0.6, 0.2, 0.6)}
    for n, o in P.items():
        o.data.materials.append(material("PETG " + n, colors[n]))

    # placeholders (rendered, never exported)
    grey = material("placeholder", (0.45, 0.45, 0.45))
    mac = prism("mac_placeholder", rounded_rect(MAC[0], MAC[1], MAC_R), "Z", Z_RAIL + 0.05, Z_RAIL + 0.05 + MAC[2])
    tube = prism("tube_placeholder", rounded_rect(TUBE, TUBE, TUBE_R), "Z", -250, 250)
    for o in (mac, tube):
        o.data.materials.append(grey)

    # test pieces: live intersections of the real parts
    stub = build_screw("screw_stub", L_STUB, False)
    stub.data.materials.append(P["screw_4a"].data.materials[0])
    t_gate = prism("test_gate_slice", [(G0 - 1, -20), (G0 + GATE_T + 1, -20), (G0 + GATE_T + 1, 20), (G0 - 1, 20)], "Y", -12, 12)
    zt = U_Z + U_IN / 2 + U_WALL + 1
    t_ublk = prism("test_u_slice", [(U_X - 0.5, Z_ROOF - 2), (OX + 1, Z_ROOF - 2), (OX + 1, zt), (U_X - 0.5, zt)], "Y", -5, 5)
    # gate slice for the tube coupon comes from beyond the threaded hole: a flat cut through the helix trips the exact boolean
    t_ugat = prism("test_u_gate_slice", [(G0 - 1, -20), (G0 + GATE_T + 1, -20), (G0 + GATE_T + 1, 20), (G0 - 1, 20)], "Y", 12, 22)
    for t, src in ((t_gate, P["gate"]), (t_ublk, P["cradle"]), (t_ugat, P["gate"])):
        boolean(t, "INTERSECT", src)
        t.parent, t.hide_render = src, True

    def pose(mode):
        # horizontal: tube front-to-back on the roof, Mac hangs below.
        # vertical: whole assembly turned (exact -90 about X) so the tube is vertical and the Mac hangs front-up.
        W = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0))).to_4x4() if mode == "vertical" else Matrix()
        mu = W @ M_U
        ex = mode == "exploded"
        off = lambda x=0, y=0, z=0: Matrix.Translation((x, y, z) if ex else (0, 0, 0))
        P["cradle"].matrix_world = W
        P["gate"].matrix_world = mu @ off(45)                 # exploded offsets out of the U's open side
        P["pad"].matrix_world = mu @ off(30, 0, 45) @ M_PAD
        P["screw_4a"].matrix_world = mu @ off(95) @ M_4A
        mac.matrix_world = W @ off(0, -170)
        tube.hide_render = ex
        tube.matrix_world = mu @ Matrix.Translation((TUBE_X0 + TUBE / 2, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        bpy.context.view_layer.update()

    # ---- fits, measured on the posed evaluated meshes ----
    print("\n== fits (triangle intersections, min gap mm) ==")
    pairs = [("cradle", "gate"), ("gate", "screw_4a"), ("pad", "screw_4a"), ("cradle", "pad"),
             ("gate", "pad"), ("cradle", "screw_4a")]
    for mode in ("horizontal", "vertical"):
        pose(mode)
        objs = dict(P, mac=mac, tube=tube)
        for a, b in pairs + [("mac", "cradle"), ("tube", "cradle"), ("tube", "pad"), ("tube", "gate"),
                             ("tube", "screw_4a")]:
            hits, d = gap(objs[a], objs[b])
            print(f"  {mode:10s} {a:12s} / {b:12s} hits {hits:4d}  gap {d:6.3f}")

    # ---- export, print-oriented on z=0 ----
    print("\n== print checks ==")
    R = lambda deg, ax: Matrix.Rotation(math.radians(deg), 4, ax)
    orient = {"cradle": (R(90, "X"), "front face down"), "gate": (R(-90, "Y"), "inner face down"),
              "screw_4a": (Matrix(), "wheel down"), "pad": (Matrix(), "grip face down")}
    jobs = [(n, [(P[n], orient[n][0])], orient[n][1]) for n in P]
    jobs += [("test_thread", [(t_gate, R(-90, "Y")), (stub, Matrix())], "gate slice inner face down + stub wheel down"),
             ("test_tube", [(t_ublk, R(90, "X")), (t_ugat, R(-90, "Y"))], "U slice front-face-down + gate slice inner face down")]
    table, bodies = [], {}
    for name, items, how in jobs:
        bm, x = bmesh.new(), 0.0
        for o, m in items:
            b = eval_bm(o, m)                          # object-local mesh -> print orientation
            lo = Vector([min(v.co[i] for v in b.verts) for i in range(3)])
            hi = Vector([max(v.co[i] for v in b.verts) for i in range(3)])
            t = b.copy()                               # triangulated copy, min corner at 0, for the plate files
            bmesh.ops.triangulate(t, faces=t.faces)
            t.verts.index_update()
            bodies[o.name] = ([tuple(v.co - lo) for v in t.verts], [tuple(v.index for v in f.verts) for f in t.faces], hi - lo)
            t.free()
            bmesh.ops.translate(b, vec=(x - lo.x, -(lo.y + hi.y) / 2, -lo.z), verts=b.verts)
            x += hi.x - lo.x + 10
            me = bpy.data.meshes.new("tmp")
            b.to_mesh(me); b.free()
            bm.from_mesh(me); bpy.data.meshes.remove(me)
        bad, bed, over, span = print_check(bm)
        dims = [max(v.co[i] for v in bm.verts) - min(v.co[i] for v in bm.verts) for i in range(3)]
        me = bpy.data.meshes.new(name + "_stl")
        bm.to_mesh(me); bm.free()
        tmp = link(bpy.data.objects.new(name + "_stl", me))
        bpy.ops.object.select_all(action="DESELECT")
        tmp.select_set(True)
        bpy.ops.wm.stl_export(filepath=os.path.join(SDIR, name + ".stl"), export_selected_objects=True,
                              apply_modifiers=False, global_scale=1.0, use_scene_unit=False)
        bpy.data.objects.remove(tmp); bpy.data.meshes.remove(me)
        table.append((name, dims, how))
        fits = all(d <= 256 for d in dims)
        print(f"  {name:12s} nonmanifold {bad:3d}  bed {bed:7.0f} mm2  overhang {over:6.1f} mm2  bridge {span:5.1f}  fits P1S {fits}")

    # ---- plate files: one .3mf per print, parts laid out on the P1S bed ----
    print("\n== plates ==")
    for plate, placed in PLATES.items():
        write_3mf(os.path.join(PDIR, plate + ".3mf"), [(label, bodies[src], xy) for src, label, xy in placed])

    # ---- renders ----
    for o in (t_gate, t_ublk, t_ugat, stub):
        o.hide_render = True
    cam = camera_rig((0, 0, 0))
    cam.data.clip_start, cam.data.clip_end = 1, 10000
    studio_look(background=0.5, exposure=0.3)
    tgt = cam.constraints[0].target

    def shoot(folder, name, objs, direction=(1.0, -1.5, 0.9)):
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        c, r = (lo + hi) / 2, (hi - lo).length / 2
        tgt.location = c
        render_views(folder, cam, {name: c + Vector(direction).normalized() * r * 2.9}, resolution=RES)

    visible = list(P.values()) + [mac, tube]
    for mode, pretty in (("exploded", "exploded"), ("vertical", "vertical_tube"), ("horizontal", "horizontal_tube")):
        pose(mode)
        shown = [o for o in visible if not o.hide_render]
        framed = shown if mode == "exploded" else [o for o in shown if o is not tube] + [mac]
        shoot(RDIR, pretty, framed)
    pose("horizontal")
    pdir = os.path.join(RDIR, "parts")
    for n, o in P.items():
        for v in visible:
            v.hide_render = v is not o
        shoot(pdir, n, [o])
    for v in visible:
        v.hide_render = False
    montage(pdir, list(P), os.path.join(RDIR, "parts_sheet.png"), cols=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "macmini_mount.blend"))

    print("\n== parts ==")
    print(f"  {'part':12s} {'bbox as printed (mm)':26s} print orientation")
    for name, d, how in table:
        print(f"  {name:12s} {d[0]:6.1f} x {d[1]:6.1f} x {d[2]:6.1f}   {how}")
    notes = os.path.join(ROOT, "NOTES_macmini.md")
    if os.path.exists(notes):
        txt = open(notes).read()
        if "## Open issues" in txt:
            print("\n== open issues (NOTES_macmini.md) ==\n" + txt.split("## Open issues", 1)[1].strip())


def montage(folder, names, path, cols=3):
    imgs = [bpy.data.images.load(os.path.join(folder, n + ".png")) for n in names]
    import numpy as np
    w, h = imgs[0].size
    rows = math.ceil(len(imgs) / cols)
    sheet = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        r = rows - 1 - i // cols                       # blender rows run bottom-up
        sheet[r * h:(r + 1) * h, (i % cols) * w:(i % cols + 1) * w] = a
    out = bpy.data.images.new("parts_sheet", cols * w, rows * h, alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw, out.file_format = path, "PNG"
    out.save()


main()
