"""Satisfying Dice Roll and Drop - Perfect Loop (Neilster style).

A small glossy die tumbles down a spiral staircase built from giant dice in
four toy colours (red, yellow, green, blue). On every step it tumbles once
across the top of a big die, then tips over the edge and drops onto the next
one with a bounce.

How the loop works
------------------
* The staircase is a square helix: four steps turn 360 degrees and descend
  exactly four big-die heights, and the colours repeat every four steps.
* The camera orbits the tower one full turn and descends four steps over the
  240-frame loop, so frame 241 is geometrically identical to frame 1.
* Eight 90-degree tumbles about alternating axes multiply out to the
  identity rotation, so even the pips line up at the seam.

Run inside Blender (Scripting tab) or:
    blender -b -P scenes/dice_roll_loop.py -- --render --preview
    python  scenes/dice_roll_loop.py --render      # with the bpy pip module
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
from mathutils import Vector, Matrix  # noqa: E402
import neilster as N  # noqa: E402

BIG = 2.0           # big step dice
SMALL = 1.0         # the tumbling die
STEP_COLOURS = ["red", "yellow", "green", "blue"]
STEPS = range(-4, 12)   # enough tower above and below the visible window

# Pip layout per face value, in face-local (u, v) units of +-0.3 * size.
PIPS = {
    1: [(0, 0)],
    2: [(-1, -1), (1, 1)],
    3: [(-1, -1), (0, 0), (1, 1)],
    4: [(-1, -1), (1, 1), (-1, 1), (1, -1)],
    5: [(-1, -1), (1, 1), (-1, 1), (1, -1), (0, 0)],
    6: [(-1, -1), (1, 1), (-1, 1), (1, -1), (-1, 0), (1, 0)],
}
# Face normal -> (value, u axis, v axis). Opposite faces sum to 7.
FACES = {
    (0, 0, 1): (1, (1, 0, 0), (0, 1, 0)),
    (0, 0, -1): (6, (1, 0, 0), (0, 1, 0)),
    (1, 0, 0): (2, (0, 1, 0), (0, 0, 1)),
    (-1, 0, 0): (5, (0, 1, 0), (0, 0, 1)),
    (0, 1, 0): (3, (1, 0, 0), (0, 0, 1)),
    (0, -1, 0): (4, (1, 0, 0), (0, 0, 1)),
}


def pip_mat():
    return N.plastic("Pip", N.PALETTE["pip"], roughness=0.08, coat=0.6)


def build_die(name, size, location, colour):
    """Bevelled glossy die with dark inlaid pips. Returns the body object;
    pips are parented to it so it animates as one rigid piece."""
    body = N.add_cube(name, size, location, N.plastic(f"Die_{colour}", N.PALETTE[colour], 0.18, 0.5),
                      bevel_width=0.09 * size)
    r = 0.085 * size
    for normal, (value, u, v) in FACES.items():
        n, u, v = Vector(normal), Vector(u), Vector(v)
        for pu, pv in PIPS[value]:
            centre = n * (size / 2 - 0.012 * size) + u * (pu * 0.28 * size) + v * (pv * 0.28 * size)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=24, ring_count=12)
            pip = bpy.context.active_object
            pip.name = f"{name}_pip"
            # Flatten along the face normal so it reads as an inlay, not a bump.
            pip.scale = tuple(0.35 if abs(n[i]) else 1.0 for i in range(3))
            for p in pip.data.polygons:
                p.use_smooth = True
            pip.data.materials.append(pip_mat())
            # Local coordinates: the pip was created at `centre` relative to the
            # die's origin, so parenting with an identity inverse keeps it there.
            pip.location = centre
            pip.parent = body
    return body


def step_layout(k):
    """Return (cell_start, direction) of the small die's path on step k."""
    c = Vector((0.0, 0.0))
    d = Vector((1.0, 0.0))
    rot90 = Matrix.Rotation(math.pi / 2, 2)
    if k >= 0:
        for _ in range(k):
            c = c + d * 2
            d = rot90 @ d
    else:
        for _ in range(-k):
            d = rot90.inverted() @ d
            c = c - d * 2
    return c, d


def main():
    scene = N.reset_scene("Dice_Roll_Loop")
    N.setup_cycles(scene, samples=96, preview=N.cli_args()["preview"])
    F = N.LOOP_FRAMES

    # --- Staircase
    for k in STEPS:
        c, d = step_layout(k)
        centre = c + d * 0.5
        z_top = -BIG * k
        build_die(f"Step_{k:+d}", BIG, (centre.x, centre.y, z_top - BIG / 2), STEP_COLOURS[k % 4])

    # --- Hero die: starts resting on step 0's first cell. Per step: one flat
    # tumble (1 s) then a tumble off the ledge dropping one big die (1 s).
    c0, _ = step_layout(0)
    hero = build_die("Hero", SMALL, (c0.x, c0.y, SMALL / 2), "red")
    per_move = F // 8
    moves = []
    for k in range(4):
        _, d = step_layout(k)
        moves.append({"dir": (d.x, d.y), "frames": per_move - 3, "drop": 0.0})
        moves.append({"dir": (d.x, d.y), "frames": per_move - 3, "drop": BIG})
    N.bake_tumbles(hero, SMALL, hero.location.copy(), moves, start_frame=1, settle_frames=3)

    # --- Camera: orbits the tower axis one full turn and descends four steps
    # over the loop. Linear, so it reads as one continuous glide.
    axis_xy = Vector((1.0, 1.0))                # centre of the square helix
    rig = N.add_empty("CamRig", (axis_xy.x, axis_xy.y, 0))
    look = N.add_empty("Look", (-0.6, -0.6, -2.4), parent=rig)
    offset = Vector((-11.0, -9.0, 19.0))
    cam = N.add_camera(scene, (0, 0, 0), look, lens=80, fstop=2.8, focus_target=hero)
    cam.parent = rig
    cam.location = offset
    for f in (1, F + 1):
        t = (f - 1) / F
        rig.rotation_euler = (0, 0, 2 * math.pi * t)
        rig.location = (axis_xy.x, axis_xy.y, -4 * BIG * t)
        rig.keyframe_insert("rotation_euler", frame=f)
        rig.keyframe_insert("location", frame=f)
    N.set_interp(rig, "LINEAR")

    # Lights ride on the rig: the whole camera+light system is rigid, so the
    # glossy highlights are identical at the loop seam.
    N.studio_lighting(scene, key_energy=6000, fill_energy=1800, parent=rig, target=look, scale=1.3)
    N.finish(scene, "dice_roll_loop")


if __name__ == "__main__":
    main()
