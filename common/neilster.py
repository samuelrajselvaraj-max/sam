"""Shared helpers for the Neilster-style satisfying-loop scenes.

Everything here is plain bpy so the scene scripts run unchanged in:
  * Blender GUI  (Scripting workspace -> open script -> Run)
  * Blender CLI  (blender -b -P scenes/<scene>.py -- --render)
  * the `bpy` pip module (python scenes/<scene>.py --render)

Conventions: Z up, metres, radians, 9:16 vertical, 30 fps, 8-second loops.
"""
import math
import os
import sys

import bpy
from mathutils import Vector, Euler

FPS = 30
LOOP_SECONDS = 8
LOOP_FRAMES = FPS * LOOP_SECONDS  # 240

# Toy-plastic palette (sRGB hex -> linear) ------------------------------------
PALETTE = {
    "red": "#E53935",
    "blue": "#1E88E5",
    "green": "#43A047",
    "yellow": "#FDD835",
    "orange": "#FB8C00",
    "white": "#F2F2F0",
    "pip": "#111111",
    "pitch": "#2E9E38",
    "charcoal": "#1C1C1E",
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


# Scene bootstrap --------------------------------------------------------------
def reset_scene(name="Neilster"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = name
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = LOOP_FRAMES
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.unit_settings.system = "METRIC"
    return scene


def setup_cycles(scene, samples=128, preview=False):
    scene.render.engine = "CYCLES"
    cy = scene.cycles
    cy.samples = 24 if preview else samples
    cy.use_denoising = not preview
    cy.use_adaptive_sampling = True
    cy.max_bounces = 6
    try:
        cy.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.get_devices()
        if not any(d.use for d in prefs.devices if d.type != "CPU"):
            cy.device = "CPU"
    except Exception:
        cy.device = "CPU"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"


# Materials --------------------------------------------------------------------
def plastic(name, hex_color, roughness=0.22, coat=0.4):
    """Glossy toy plastic with a clearcoat, the signature look of the channel."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    return mat


def chrome(name="Chrome"):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.92, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.12
    return mat


# Geometry helpers -------------------------------------------------------------
def bevel(obj, width=0.08, segments=5):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    for p in obj.data.polygons:
        p.use_smooth = True
    return mod


def add_cube(name, size=1.0, location=(0, 0, 0), material=None, bevel_width=None, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    if bevel_width:
        bevel(obj, bevel_width)
    if parent:
        obj.parent = parent
    return obj


def add_empty(name, location=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = location
    e.empty_display_type = "PLAIN_AXES"
    bpy.context.scene.collection.objects.link(e)
    if parent:
        e.parent = parent
    return e


# Lighting / camera ------------------------------------------------------------
def studio_lighting(scene, key_energy=1500, fill_energy=400, world_strength=0.35):
    """Soft overhead studio: big warm key top-left, large cool fill, grey world."""
    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.85, 0.87, 0.9, 1)
    bg.inputs["Strength"].default_value = world_strength

    bpy.ops.object.light_add(type="AREA", location=(-6, -4, 10))
    key = bpy.context.active_object
    key.name = "Key"
    key.data.energy = key_energy
    key.data.size = 8
    key.data.color = (1.0, 0.95, 0.88)
    key.rotation_euler = Euler((math.radians(28), math.radians(-22), 0))

    bpy.ops.object.light_add(type="AREA", location=(7, 5, 8))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = fill_energy
    fill.data.size = 12
    fill.data.color = (0.88, 0.93, 1.0)
    fill.rotation_euler = Euler((math.radians(-30), math.radians(30), 0))
    return key, fill


def add_camera(scene, location, target, lens=85, fstop=2.8, focus_target=None):
    cam_data = bpy.data.cameras.new("ShortsCam")
    cam_data.lens = lens
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new("ShortsCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = location
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    cam_data.dof.focus_object = focus_target or target
    scene.camera = cam
    return cam


# Animation helpers ------------------------------------------------------------
def fcurves_of(id_block):
    """F-curves of an ID's action, on both legacy (<=4.x) and slotted (5.x) actions."""
    ad = id_block.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):  # legacy API
        return list(act.fcurves)
    slot = ad.action_slot.handle
    return [fc for layer in act.layers for strip in layer.strips
            for cb in strip.channelbags if cb.slot_handle == slot for fc in cb.fcurves]


def set_interp(obj, interpolation="BEZIER", easing="AUTO", data_path=None):
    for fc in fcurves_of(obj):
        if data_path and fc.data_path != data_path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = interpolation
            kp.easing = easing


def make_cyclic(obj):
    """Add a Cycles F-modifier so the action repeats seamlessly past the loop."""
    for fc in fcurves_of(obj):
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")


def edge_tumble(obj, start_frame, frames, axis, direction, size, pivot_parent=None):
    """Rigid 90-degree tumble of a cube over one of its bottom edges.

    Implemented with a temporary pivot empty at the bottom edge: the cube is
    parented to the pivot, the pivot rotates 90 degrees, then the cube's world
    matrix is baked back so the next tumble can use a fresh pivot.
    axis: 'X' or 'Y' (the direction of travel). direction: +1 or -1.
    """
    scene = bpy.context.scene
    scene.frame_set(start_frame)
    half = size / 2
    world = obj.matrix_world.copy()
    pos = world.translation
    # Pivot sits at the leading bottom edge.
    if axis == "X":
        pivot_loc = Vector((pos.x + direction * half, pos.y, pos.z - half))
        rot_axis = "Y"
        angle = -direction * math.pi / 2
    else:
        pivot_loc = Vector((pos.x, pos.y + direction * half, pos.z - half))
        rot_axis = "X"
        angle = direction * math.pi / 2

    pivot = add_empty(f"{obj.name}_pivot_{start_frame}", pivot_loc, parent=pivot_parent)
    obj.parent = pivot
    obj.matrix_parent_inverse = pivot.matrix_world.inverted()

    pivot.rotation_euler = Euler((0, 0, 0))
    pivot.keyframe_insert("rotation_euler", frame=start_frame)
    idx = "XYZ".index(rot_axis)
    rot = [0, 0, 0]
    rot[idx] = angle
    pivot.rotation_euler = Euler(rot)
    pivot.keyframe_insert("rotation_euler", frame=start_frame + frames)
    # A tumble accelerates into the landing like a real block: ease-in.
    for fc in fcurves_of(pivot):
        for kp in fc.keyframe_points:
            kp.interpolation = "QUAD"
            kp.easing = "EASE_IN"
    # Short settle "clack" bounce: tiny over-rotation then back.
    pivot.rotation_euler = Euler(rot)
    pivot.keyframe_insert("rotation_euler", frame=start_frame + frames + 3)
    return pivot


# Output -----------------------------------------------------------------------
def cli_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    return {
        "render": "--render" in argv,
        "preview": "--preview" in argv,
        "frames": [int(a.split("=")[1]) for a in argv if a.startswith("--frame=")],
        "save": "--save" in argv,
    }


def render_frames(scene, out_dir, frames=None, preview=False):
    os.makedirs(out_dir, exist_ok=True)
    if preview:
        scene.render.resolution_percentage = 25
    frames = frames or [1, LOOP_FRAMES // 4, LOOP_FRAMES // 2, LOOP_FRAMES]
    for f in frames:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(out_dir, f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)


def render_animation(scene, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = os.path.join(out_dir, "loop_")
    bpy.ops.render.render(animation=True)


def finish(scene, scene_slug, build_fn_name="main"):
    """Common CLI tail: optional save of .blend and optional render."""
    args = cli_args()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo, "renders", scene_slug)
    if args["save"]:
        os.makedirs(os.path.join(repo, "blend"), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(repo, "blend", f"{scene_slug}.blend"))
    if args["render"]:
        render_frames(scene, out_dir, args["frames"] or None, preview=args["preview"])
