"""Satisfying Rubik's Cube Slide and Drop - Perfect Loop (Neilster style).

How the loop works
------------------
* The floor is the top face of a giant Rubik's cube whose centre cubie is
  missing, leaving a square hole.
* A Rubik's cube exactly one cubie in size slides in from off-screen, hovers
  over the hole and drops into it, sitting flush. Its own top face is now a
  3x3 floor with a hole in the middle.
* The camera dollies toward the hole along its view ray by a factor of 3
  over the 8-second loop (exponential, so the zoom speed looks constant).
  At frame 241 the dropped cube's top face fills the frame exactly the way
  the big floor did at frame 1, so the last frame cuts back to the first
  seamlessly.

Run inside Blender (Scripting tab) or:
    blender -b -P scenes/rubiks_slide_drop.py -- --render --preview
    python  scenes/rubiks_slide_drop.py --render      # with the bpy pip module
"""
import math
import os
import sys

import bpy  # noqa: E402


def _repo_root():
    """Locate the repo whether run from the CLI, the bpy module, or Blender's
    text editor (where __file__ is only set for texts opened from disk)."""
    candidates = []
    if "__file__" in globals():
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    for text in getattr(bpy.data, "texts", []):
        if text.filepath:
            candidates.append(os.path.dirname(bpy.path.abspath(text.filepath)))
    candidates.append(os.getcwd())
    for c in candidates:
        for root in (c, os.path.dirname(c)):
            if os.path.isdir(os.path.join(root, "common")):
                return root
    raise RuntimeError("Open this script from its repo checkout so 'common/neilster.py' can be found.")


sys.path.insert(0, os.path.join(_repo_root(), "common"))
from mathutils import Vector  # noqa: E402
import neilster as N  # noqa: E402

ZOOM = 3.0  # cubie-size ratio between nested levels
CUBE = 1.0  # size of the hero cube (one cubie of the floor cube)

# The 3x3 sticker pattern on every top face. Identical on every level so the
# zoom is self-similar. Index 4 (centre) is the hole.
TOP_PATTERN = ["yellow", "blue", "red",
               "white", None, "green",
               "orange", "yellow", "blue"]
SIDE_COLOURS = {"+x": "red", "-x": "orange", "+y": "green", "-y": "blue", "-z": "white"}


def sticker_mat(colour):
    return N.plastic(f"Sticker_{colour}", N.PALETTE[colour] if colour in N.PALETTE else colour,
                     roughness=0.3, coat=0.35)


BODY = None


def body_mat():
    global BODY
    if BODY is None:
        BODY = N.plastic("CubeBody", "#141414", roughness=0.35, coat=0.2)
    return BODY


def build_rubiks(name, size, location, parent=None, hole=True, top_pattern=TOP_PATTERN):
    """A full Rubik's cube: 27 bevelled black cubies + raised bevelled stickers.

    If `hole` is True the top-centre cubie is left out so the next level can
    drop into it.
    """
    root = N.add_empty(name, location, parent=parent)
    c = size / 3.0
    gap = 0.03 * c
    sticker_t = 0.06 * c
    for ix in (-1, 0, 1):
        for iy in (-1, 0, 1):
            for iz in (-1, 0, 1):
                if hole and (ix, iy, iz) == (0, 0, 1):
                    continue
                cubie = N.add_cube(f"{name}_cubie", c - gap, (ix * c, iy * c, iz * c),
                                   body_mat(), bevel_width=0.07 * c, parent=root)
                # Stickers only on the six outer faces.
                faces = []
                if iz == 1:
                    idx = (iy + 1) * 3 + (ix + 1)   # row-major from -y to +y
                    col = top_pattern[idx]
                    if col:
                        faces.append(((0, 0, 1), col))
                if iz == -1:
                    faces.append(((0, 0, -1), SIDE_COLOURS["-z"]))
                if ix == 1:
                    faces.append(((1, 0, 0), SIDE_COLOURS["+x"]))
                if ix == -1:
                    faces.append(((-1, 0, 0), SIDE_COLOURS["-x"]))
                if iy == 1:
                    faces.append(((0, 1, 0), SIDE_COLOURS["+y"]))
                if iy == -1:
                    faces.append(((0, -1, 0), SIDE_COLOURS["-y"]))
                for normal, col in faces:
                    n = Vector(normal)
                    loc = Vector((ix * c, iy * c, iz * c)) + n * ((c - gap) / 2 + sticker_t / 2 - 0.004 * c)
                    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
                    st = bpy.context.active_object
                    st.name = f"{name}_sticker_{col}"
                    side = 0.84 * c
                    st.scale = (sticker_t if n.x else side, sticker_t if n.y else side, sticker_t if n.z else side)
                    st.data.materials.append(sticker_mat(col))
                    N.bevel(st, 0.08, 4)  # local units of the unit cube: scales with the sticker
                    st.parent = root
    return root


def main():
    scene = N.reset_scene("Rubiks_SlideDrop")
    N.setup_cycles(scene, samples=96, preview=N.cli_args()["preview"])

    # --- Levels. Every level's top face is at z = 0 and its hole is centred
    # on the Z axis: the 3-unit cube sits flush in the 9-unit cube's hole,
    # and the 1-unit hero drops flush into the 3-unit cube's hole.
    build_rubiks("Floor_L2", CUBE * ZOOM * ZOOM, (0, 0, -CUBE * ZOOM * ZOOM / 2))
    build_rubiks("Floor_L1", CUBE * ZOOM, (0, 0, -CUBE * ZOOM / 2))
    hero = build_rubiks("Hero", CUBE, (0, 0, 0))

    # --- Hero animation: slide in from off-screen along +X, stop over the
    # hole, drop in with a bounce, settle flush.
    F = N.LOOP_FRAMES
    start_x = 4.2 * CUBE
    hover_z = 0.45 * CUBE               # hero bottom hovers just above floor
    rest_z = -CUBE / 2                  # flush: hero top == floor top (z=0)

    def key(frame, loc, rot_z=0.0):
        hero.location = loc
        hero.rotation_euler = (0, 0, rot_z)
        hero.keyframe_insert("location", frame=frame)
        hero.keyframe_insert("rotation_euler", frame=frame)

    key(1, (start_x, 0, hover_z))
    key(int(F * 0.42), (0.0, 0, hover_z))           # slide ends above hole
    key(int(F * 0.47), (0.0, 0, hover_z))           # beat before the drop
    key(int(F * 0.54), (0.0, 0, rest_z))            # drop
    key(int(F * 0.58), (0.0, 0, rest_z + 0.08 * CUBE))  # tiny bounce
    key(int(F * 0.63), (0.0, 0, rest_z))            # settle
    key(F + 1, (0.0, 0, rest_z))
    for fc in N.fcurves_of(hero):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "AUTO"
        # Gravity feel on the drop: ease-in to the landing.
        if fc.data_path == "location" and fc.array_index == 2:
            for kp in fc.keyframe_points:
                if abs(kp.co.x - int(F * 0.47)) < 1:
                    kp.interpolation = "QUAD"
                    kp.easing = "EASE_IN"
    # Slide: ease out so it glides to a halt over the hole.
    fcx = [fc for fc in N.fcurves_of(hero) if fc.data_path == "location" and fc.array_index == 0][0]
    fcx.keyframe_points[0].interpolation = "CUBIC"
    fcx.keyframe_points[0].easing = "EASE_OUT"

    # --- Camera + lights on one rig scaled by 1/ZOOM over the loop: an exact
    # similarity about the hole centre, so frame 241 == frame 1 one level in.
    rig = N.add_empty("ZoomRig", (0, 0, 0))
    look = N.add_empty("Look", (0, 0, 0), parent=rig)
    direction = Vector((1.0, -1.15, 1.75)).normalized()
    d0 = 11.5 * CUBE
    cam = N.add_camera(scene, direction * d0, look, lens=70, fstop=2.0)
    cam.data.sensor_fit = "VERTICAL"
    lights = N.studio_lighting(scene, key_energy=2500, fill_energy=700, parent=rig)
    N.animate_similarity(scene, rig, cam, lights, 1.0 / ZOOM, fstop=2.0)

    N.finish(scene, "rubiks_slide_drop")


if __name__ == "__main__":
    main()
