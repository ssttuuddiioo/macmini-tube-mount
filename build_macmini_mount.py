"""3D-printable Mac mini enclosure that clamps to a 1" square tube (vertical or horizontal).

Units: 1 Blender unit = 1 mm. All parts PETG on a Bambu P1S.
Parts: cradle (+ plate), clamp block, gate, thumbwheel screws 4a/4b, pressure pad.
Every part is a base mesh plus live Boolean modifiers whose helper objects are parented
to it; modifiers are only applied on the throwaway copies written to STL.

Frames: cradle frame = world (floor center at origin, Mac front faces -Y, side wall on +X).
The connector sits on the roof (the Mac's square face), so the clamp stacks on the Mac
instead of beside it. Horizontal tube: Mac hangs under it. Vertical tube: Mac stands on its
side wall with the roof against the tube.
Connector geometry is drawn as if on the +X wall and moved onto the roof by M_CONN.
Block frame: tenon points -X into the socket, tube axis along local Y, the U opens +X.
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
TONGUE_X = -42.0                  # snap tongue center, off to the side of the roof boss
RELIEF_R = 1.5                    # inside-corner relief channels
NOTCH = (-70.0, -40.0, 40.0, 70.0)  # power-button notch x0, x1, y0, y1 (rear-left)
TENON = 20.0                      # tenon square side (printed as a 45-degree diamond)
FIT = 0.3                         # sliding fits: tenon/socket, gate/dovetail
SOCK_D = 30.0                     # socket depth
BOSS_WALL, BOSS_TOP = 5.0, 12.0   # boss walls; wall above the socket that carries 4b's thread
B_BASE = 14.0                     # clamp block base thickness (keeps tube clear of 4b's wheel)
U_IN = 26.2                       # U inside width
U_EXTRA = 12.0                    # extra U depth for the pad + screw tip
U_WALL, U_LEN = 5.0, 60.0
GATE_T = 10.0                     # gate thickness = thread engagement
DOVE = 2.3                        # dovetail tongue reach into each flange
ZIP = (3.0, 6.0)                  # zip-tie slot x (across) and y (along tube)
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
L_4A, L_4B, L_STUB = 24.0, 18.0, 15.0
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
ZS = (Z_FLOOR + Z_ROOF) / 2       # socket axis height
HS = (TENON + 2 * FIT) / math.sqrt(2)   # socket half-diagonal
HT = TENON / math.sqrt(2)               # tenon half-diagonal
X_SOCK0 = OX + 4.0                # socket bottom
X_BOSS = X_SOCK0 + SOCK_D         # boss outer face
Y_BOSS_TOP = HS + BOSS_TOP
X_4B = X_BOSS - R_MAJ * K_INT - 2.65   # 4b axis: 2.65 mm wall to the boss face, wheel clears the plate
Y_4B_TIP = HT + 0.2               # 4b tip just above the tenon's top edge
G0 = B_BASE + U_IN + U_EXTRA      # gate inner face (block frame)
FL_TIP = G0 + GATE_T + 2.0
TUBE_X0 = B_BASE + 0.05           # tube face against the base
PAD_X0 = TUBE_X0 + TUBE + 0.05    # pad face against the tube
BLOCK_X = X_BOSS + 0.05           # block frame origin in the cradle frame (shoulder seated on the boss)


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
Y_4B_W = Y_4B_TIP + 12 + L_4B                 # 4b wheel bottom (cradle y)
X_4A_W = PAD_X0 + 4.3 + 12 + L_4A + 6.5        # 4a wheel bottom (block x); collar tip 0.3 above the socket floor
# Connector frame: maps geometry drawn on the +X wall (socket axis +X at y=0, z=ZS) onto the
# roof center (socket axis +Z). Y is unchanged, so print orientation and overhangs carry over.
M_CONN = (Matrix.Translation((0, 0, Z_TOP)) @ Matrix(((0, 0, -1), (0, 1, 0), (1, 0, 0))).to_4x4()   # exact -90 about Y
          @ Matrix.Translation((-OX, 0, -ZS)))   # exact entries: rotation noise makes the exact boolean leave slivers
M_4B = M_CONN @ Matrix.Translation((X_4B, Y_4B_W, ZS)) @ Matrix.Rotation(math.radians(90), 4, "X")    # screw z -> -Y
M_4A = Matrix.Translation((X_4A_W, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, "Y")      # screw z -> -X
M_PAD = Matrix.Translation((PAD_X0, 0, 0)) @ Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_4x4()


def m_block(k):
    """Block frame in the cradle frame; k quarter-turns about the tenon axis (0: tube front-to-back, 1: tube across)."""
    return M_CONN @ Matrix.Translation((BLOCK_X, 0, ZS)) @ Matrix.Rotation(math.radians(90 * k), 4, "X")


def diamond(h, zc=0.0):
    return [(h, zc), (0, zc + h), (-h, zc), (0, zc - h)]


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ---- parts ----
def build_cradle():
    """Open sleeve: floor, roof, side wall (+X). Front/back open, -X open between retaining lips.
    The socket boss sits on the roof."""
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
    # socket boss on the roof, underside at 45 degrees so it prints front-face-down without support
    yb = -HS - BOSS_WALL
    boss = prism("boss", [(OX - 0.4, yb - (X_BOSS - OX + 0.4)), (X_BOSS, yb), (X_BOSS, Y_BOSS_TOP), (OX - 0.4, Y_BOSS_TOP)],
                 "Z", ZS - HS - BOSS_WALL, ZS + HS + BOSS_WALL)
    boss.matrix_world = M_CONN
    add(boss)
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
    sock = prism("socket", diamond(HS, ZS), "X", X_SOCK0, X_BOSS + 1)
    sock.matrix_world = M_CONN
    cut(sock)
    hole = thread_cutter("cradle_4b_hole", Y_4B_W - Y_BOSS_TOP, Y_4B_W - 8.0, blind=True)
    hole.matrix_world = M_4B
    cut(hole)
    return cr


def build_block():
    """Clamp block: diamond tenon, U-channel with dovetail grooves and zip-tie slots."""
    c, h, o = CHAMF, U_IN / 2, U_IN / 2 + U_WALL
    pts = [(c, -o), (FL_TIP - c, -o), (FL_TIP, -o + c), (FL_TIP, -h), (B_BASE + c, -h), (B_BASE, -h + c),
           (B_BASE, h - c), (B_BASE + c, h), (FL_TIP, h), (FL_TIP, o - c), (FL_TIP - c, o), (c, o), (0, o - c), (0, -o + c)]
    bl = prism("clamp_block", pts, "Y", -U_LEN / 2, U_LEN / 2)
    helper(prism("tenon", diamond(HT), "X", -(SOCK_D - 0.5), 0.5), bl, "add")
    k = G0 + 6 - (h - FIT) + FIT * math.sqrt(2)          # x - z of the offset dovetail flank
    zi, zo = h - 0.6, h - FIT + DOVE + FIT
    for s in (1, -1):
        g = [(G0 - FIT, zi), (G0 - FIT, zo), (zo + k, zo), (zi + k, zi)]
        helper(prism(f"groove{s:+d}", [(x, s * z) for x, z in g], "Y", -U_LEN / 2 - 1, U_LEN / 2 + 1), bl)
    xc = (TUBE_X0 + TUBE + G0) / 2
    a, b = ZIP[0] / 2, ZIP[1] / 2
    for s in (1, -1):
        yc = s * (U_LEN / 2 - b - 2.5)
        hexa = [(xc - a, yc - b + a), (xc, yc - b), (xc + a, yc - b + a), (xc + a, yc + b - a), (xc, yc + b), (xc - a, yc + b - a)]
        helper(prism(f"zip{s:+d}", hexa, "Z", -o - 1, o + 1), bl)
    return bl


def build_gate():
    """Gate bar: half-dovetail tongues (45-degree flank on the load side), 4a thread in the middle."""
    t, d, w = U_IN / 2 - FIT, DOVE, 6.0
    pts = [(G0, -t - d), (G0 + w + d, -t - d), (G0 + w, -t), (G0 + GATE_T, -t),
           (G0 + GATE_T, t), (G0 + w, t), (G0 + w + d, t + d), (G0, t + d)]
    ga = prism("gate", pts, "Y", -U_LEN / 2, U_LEN / 2)
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


# ---- scene ----
def main():
    new_scene()
    os.makedirs(SDIR, exist_ok=True)
    us = bpy.context.scene.unit_settings
    us.system, us.scale_length, us.length_unit = "METRIC", 0.001, "MILLIMETERS"

    P = {"cradle": build_cradle(), "clamp_block": build_block(), "gate": build_gate(),
         "screw_4a": build_screw("screw_4a", L_4A, True), "screw_4b": build_screw("screw_4b", L_4B, False),
         "pad": build_pad()}
    colors = {"cradle": (0.85, 0.45, 0.1), "clamp_block": (0.1, 0.35, 0.8), "gate": (0.15, 0.6, 0.3),
              "screw_4a": (0.9, 0.75, 0.1), "screw_4b": (0.9, 0.75, 0.1), "pad": (0.6, 0.2, 0.6)}
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
    t_ublk = prism("test_u_slice", [(-0.5, -25), (FL_TIP + 1, -25), (FL_TIP + 1, 25), (-0.5, 25)], "Y", -5, 5)
    t_ugat = prism("test_u_gate_slice", [(G0 - 1, -20), (G0 + GATE_T + 1, -20), (G0 + GATE_T + 1, 20), (G0 - 1, 20)], "Y", -5, 5)
    for t, src in ((t_gate, P["gate"]), (t_ublk, P["clamp_block"]), (t_ugat, P["gate"])):
        boolean(t, "INTERSECT", src)
        t.parent, t.hide_render = src, True

    def pose(mode):
        # horizontal: tube front-to-back above the roof, Mac hangs below.
        # vertical: tube across the roof, whole assembly turned so the Mac stands on its side wall.
        k = 1 if mode == "vertical" else 0
        W = Matrix.Rotation(math.radians(90), 4, "Y") if mode == "vertical" else Matrix()
        mb = W @ m_block(k)
        ex = mode == "exploded"
        off = lambda x=0, y=0, z=0: Matrix.Translation((x, y, z) if ex else (0, 0, 0))
        P["cradle"].matrix_world = W
        P["clamp_block"].matrix_world = mb @ off(60)          # exploded offsets along the tenon axis
        P["gate"].matrix_world = mb @ off(130)
        P["pad"].matrix_world = mb @ off(95, 0, 70) @ M_PAD
        P["screw_4a"].matrix_world = mb @ off(190) @ M_4A
        P["screw_4b"].matrix_world = W @ off(0, 50) @ M_4B
        mac.matrix_world = W @ off(0, -170)
        tube.hide_render = ex
        tube.matrix_world = mb @ Matrix.Translation((TUBE_X0 + TUBE / 2, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        bpy.context.view_layer.update()

    # ---- fits, measured on the posed evaluated meshes ----
    print("\n== fits (triangle intersections, min gap mm) ==")
    pairs = [("cradle", "clamp_block"), ("clamp_block", "gate"), ("gate", "screw_4a"), ("cradle", "screw_4b"),
             ("pad", "screw_4a"), ("clamp_block", "screw_4b"), ("clamp_block", "pad"), ("gate", "pad")]
    for mode in ("horizontal", "vertical"):
        pose(mode)
        objs = dict(P, mac=mac, tube=tube)
        for a, b in pairs + [("mac", "cradle"), ("tube", "clamp_block"), ("tube", "pad"), ("tube", "gate"),
                             ("tube", "screw_4b"), ("tube", "cradle")]:
            hits, d = gap(objs[a], objs[b])
            print(f"  {mode:10s} {a:12s} / {b:12s} hits {hits:4d}  gap {d:6.3f}")

    # ---- export, print-oriented on z=0 ----
    print("\n== print checks ==")
    R = lambda deg, ax: Matrix.Rotation(math.radians(deg), 4, ax)
    orient = {"cradle": (R(90, "X"), "front face down"), "clamp_block": (R(90, "X"), "U end down, tube axis up"),
              "gate": (R(-90, "Y"), "inner face down"), "screw_4a": (Matrix(), "wheel down"),
              "screw_4b": (Matrix(), "wheel down"), "pad": (Matrix(), "grip face down")}
    jobs = [(n, [(P[n], orient[n][0])], orient[n][1]) for n in P]
    jobs += [("test_thread", [(t_gate, R(-90, "Y")), (stub, Matrix())], "gate slice inner face down + stub wheel down"),
             ("test_tube", [(t_ublk, R(90, "X")), (t_ugat, R(-90, "Y"))], "U slice flat + gate slice inner face down")]
    table = []
    for name, items, how in jobs:
        bm, x = bmesh.new(), 0.0
        for o, m in items:
            b = eval_bm(o, m)                          # object-local mesh -> print orientation
            lo = Vector([min(v.co[i] for v in b.verts) for i in range(3)])
            hi = Vector([max(v.co[i] for v in b.verts) for i in range(3)])
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
    montage(pdir, list(P), os.path.join(RDIR, "parts_sheet.png"))

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
