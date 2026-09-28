import bpy, os


def camera_rig(target):
    """Camera that always looks at an empty placed at target. Returns the camera object."""
    scene = bpy.context.scene
    tgt = bpy.data.objects.new("Target", None)
    scene.collection.objects.link(tgt)
    tgt.location = target
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    t = cam.constraints.new("TRACK_TO")
    t.target, t.track_axis, t.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    return cam


def studio_look(background=0.4, exposure=0.8):
    """Workbench look for material colors: grey backdrop, crisp edges, object outlines."""
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = exposure       # studio light alone renders light woods muddy
    scene.world = scene.world or bpy.data.worlds.new("World")
    scene.world.color = (background,) * 3
    sh = scene.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "SCREEN"
    sh.show_object_outline = True


def render_views(out_dir, cam, views, resolution=800, ortho=(), ortho_scale=2.0):
    """Render {name: camera location} to out_dir/<name>.png with Workbench.
    Views named in ortho render orthographic at ortho_scale meters across."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = resolution
    for name, loc in views.items():
        cam.location = loc
        cam.data.type = "ORTHO" if name in ortho else "PERSP"
        cam.data.ortho_scale = ortho_scale
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
