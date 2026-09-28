import bpy, os


def new_scene():
    """Wipe to an empty factory scene and return it."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def out_dir(script_path):
    """out/ next to the calling script, created if missing."""
    out = os.path.join(os.path.dirname(os.path.abspath(script_path)), "out")
    os.makedirs(out, exist_ok=True)
    return out
