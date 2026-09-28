import bpy, bmesh


def box(name, size, loc):
    """Axis-aligned box centered at loc. Real dimensions go into the mesh so scale
    stays 1 and bevel widths come out true in every direction."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def bevel(o, width, segments=3):
    """Live bevel modifier on every sharp edge."""
    m = o.modifiers.new("Bevel", "BEVEL")
    m.width, m.segments, m.limit_method = width, segments, "ANGLE"
    return m


def material(name, color, roughness=0.6):
    """Flat-color material; color is linear RGB. Sets both the Workbench color and the glTF base color."""
    m = bpy.data.materials.new(name)
    m.diffuse_color, m.roughness = (*color, 1), roughness
    bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = roughness
    return m


def ply_edges(o, face_mat, edge_mat):
    """Sheet-goods panel: faces normal to the thin axis get face_mat, the edges get edge_mat."""
    co = [v.co for v in o.data.vertices]
    thin = min(range(3), key=lambda k: max(c[k] for c in co) - min(c[k] for c in co))
    o.data.materials.append(face_mat)
    o.data.materials.append(edge_mat)
    for f in o.data.polygons:
        f.material_index = 0 if abs(f.normal[thin]) > 0.5 else 1
