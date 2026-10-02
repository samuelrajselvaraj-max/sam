"""Satisfying Football Infinite Loop (Neilster style) - foosball Droste zoom.

A toy foosball table with a miniature copy of itself sunk into the centre
circle, and a smaller one inside that. A red player kicks the ball, a blue
player returns it, it arcs high and lands in the miniature table while the
camera dollies in. When the mini table fills the frame the loop is back at
frame 1.

How the loop works
------------------
* The whole table (pitch, rails, rods, players and the animated ball) lives
  in one collection. Nested levels are collection instances scaled by
  RATIO about the centre spot, so every level plays the same 240-frame
  animation in sync.
* The ball ends the loop at RATIO * (its start position) and shrinks by
  RATIO over the loop; the camera dollies in by 1/RATIO along a fixed ray.
  Frame 241 is therefore the same picture as frame 1, one level deeper.

Run inside Blender (Scripting tab) or:
    blender -b -P scenes/football_loop.py -- --render --preview
    python  scenes/football_loop.py --render      # with the bpy pip module
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

W, L = 6.0, 10.0          # pitch size (x, y)
CIRCLE_R = 0.9            # centre circle radius
RATIO = (2 * CIRCLE_R) / W  # 0.3: nested table width equals the circle
ROD_Z = 0.55
BALL_R = 0.24
RODS = [  # (y, team, players)
    (-4.1, "red", 1), (-3.0, "red", 2), (-1.7, "blue", 3), (-0.5, "red", 5),
    (0.5, "blue", 5), (1.7, "red", 3), (3.0, "blue", 2), (4.1, "blue", 1),
]


def link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)


def box(name, size, loc, mat, coll, bevel=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    if bevel:
        N.bevel(o, bevel, 3)
    link(o, coll)
    return o


def cylinder(name, radius, depth, loc, rot, mat, coll):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot, vertices=48)
    o = bpy.context.active_object
    o.name = name
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(mat)
    link(o, coll)
    return o


def ball_material():
    mat = bpy.data.materials.new("Football")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Coat Weight"].default_value = 0.3
    tex = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 2.6
    vor.inputs["Randomness"].default_value = 0.6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (0.9, 0.9, 0.9, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.02, 0.02, 0.02, 1)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(vor.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Red"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def build_table(coll):
    pitch = N.plastic("Pitch", N.PALETTE["pitch"], roughness=0.55, coat=0.1)
    white = N.plastic("Line", "#F4F4F0", roughness=0.5, coat=0.0)
    rail = N.plastic("Rail", N.PALETTE["charcoal"], roughness=0.4, coat=0.3)
    chrome = N.chrome()
    teams = {"red": N.plastic("Player_red", N.PALETTE["red"], 0.3, 0.3),
             "blue": N.plastic("Player_blue", N.PALETTE["blue"], 0.3, 0.3)}
    handle = N.plastic("Handle", "#101010", roughness=0.5, coat=0.2)

    # Pitch slab (top at z=0 so the similarity's fixed point is on the surface).
    rt, rh = 0.35, 0.7
    slab = box("Pitch", (W, L, 0.4), (0, 0, -0.2), pitch, coll)
    # Recess for the nested table: a hidden cutter the size of the mini
    # table's footprint, boolean-subtracted from the slab and the markings
    # that cross the centre. Instanced with the collection, so every level
    # has a recess for the next.
    cutter = box("Recess", ((W + 2 * rt) * RATIO, (L + 2 * rt) * RATIO, 1.2), (0, 0, 0), pitch, coll)
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    cutters = [slab]
    lw, lh = 0.07, 0.006
    cutters.append(box("HalfwayLine", (W, lw, lh), (0, 0, lh / 2), white, coll))
    for sy in (-1, 1):
        box("TouchLine", (lw, L, lh), (sy * (W / 2 - lw), 0, lh / 2), white, coll)
        box("GoalLine", (W, lw, lh), (0, sy * (L / 2 - lw), lh / 2), white, coll)
        # Penalty box.
        bw, bd = 3.4, 1.4
        box("BoxFront", (bw, lw, lh), (0, sy * (L / 2 - bd), lh / 2), white, coll)
        for sx in (-1, 1):
            box("BoxSide", (lw, bd, lh), (sx * bw / 2, sy * (L / 2 - bd / 2), lh / 2), white, coll)
    bpy.ops.mesh.primitive_torus_add(major_radius=CIRCLE_R, minor_radius=lw / 2, location=(0, 0, 0),
                                     major_segments=96, minor_segments=8)
    ring = bpy.context.active_object
    ring.name = "CentreCircle"
    ring.scale.z = 0.2
    ring.data.materials.append(white)
    link(ring, coll)
    cutters.append(ring)
    for o in cutters:
        mod = o.modifiers.new("Recess", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "EXACT"

    # Rails.
    for sx in (-1, 1):
        box("RailSide", (rt, L + 2 * rt, rh), (sx * (W / 2 + rt / 2), 0, rh / 2 - 0.4), rail, coll, bevel=0.04)
    for sy in (-1, 1):
        box("RailEnd", (W, rt, rh), (0, sy * (L / 2 + rt / 2), rh / 2 - 0.4), rail, coll, bevel=0.04)
        # Goal mouth.
        box("Goal", (1.6, 0.12, 0.5), (0, sy * (L / 2 + 0.05), 0.25), chrome, coll)

    # Rods with players. Each rod is a parent empty so it can spin and slide.
    rods = []
    for i, (y, team, n) in enumerate(RODS):
        rod_root = N.add_empty(f"Rod_{i}", (0, y, ROD_Z))
        link(rod_root, coll)
        rod = cylinder(f"RodBar_{i}", 0.045, W + 2 * rt + 1.4, (0, 0, 0), (0, math.pi / 2, 0), chrome, coll)
        rod.parent = rod_root
        for sx in (-1, 1):
            h = cylinder(f"Handle_{i}", 0.09, 0.5, (sx * (W / 2 + rt + 0.95), 0, 0), (0, math.pi / 2, 0), handle, coll)
            h.parent = rod_root
        spacing = W / (n + 1)
        for j in range(n):
            x = -W / 2 + spacing * (j + 1)
            body = box(f"Body_{i}_{j}", (0.2, 0.13, 0.4), (x, 0, -0.22), teams[team], coll, bevel=0.03)
            body.parent = rod_root
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=(x, 0, 0.0), segments=24, ring_count=12)
            head = bpy.context.active_object
            head.name = f"Head_{i}_{j}"
            for p in head.data.polygons:
                p.use_smooth = True
            head.data.materials.append(teams[team])
            link(head, coll)
            head.parent = rod_root
            foot = box(f"Foot_{i}_{j}", (0.22, 0.2, 0.12), (x, 0, -0.47), teams[team], coll, bevel=0.03)
            foot.parent = rod_root
        rods.append(rod_root)

    # Ball.
    bpy.ops.mesh.primitive_uv_sphere_add(radius=BALL_R, segments=48, ring_count=24)
    ball = bpy.context.active_object
    ball.name = "Ball"
    for p in ball.data.polygons:
        p.use_smooth = True
    ball.data.materials.append(ball_material())
    link(ball, coll)
    return rods, ball


def animate(rods, ball):
    F = N.LOOP_FRAMES

    # --- Rod kicks. A kick is a quick forward swing about the rod axis (X).
    def kick(rod, frame, direction=1, wind=-0.9, swing=0.8, slide=0.0):
        rod.rotation_euler = (0, 0, 0)
        rod.keyframe_insert("rotation_euler", frame=frame - 10)
        rod.rotation_euler = (direction * wind, 0, 0)
        rod.keyframe_insert("rotation_euler", frame=frame - 3)
        rod.rotation_euler = (-direction * swing, 0, 0)
        rod.keyframe_insert("rotation_euler", frame=frame + 2)
        rod.rotation_euler = (0, 0, 0)
        rod.keyframe_insert("rotation_euler", frame=frame + 14)
        if slide:
            rod.location.x = 0
            rod.keyframe_insert("location", frame=frame - 16)
            rod.location.x = slide
            rod.keyframe_insert("location", frame=frame - 2)
            rod.location.x = 0
            rod.keyframe_insert("location", frame=frame + 22)

    for rod in rods:  # loop-safe rest pose at both ends
        rod.rotation_euler = (0, 0, 0)
        rod.location = (0, rod.location.y, ROD_Z)
        rod.keyframe_insert("rotation_euler", frame=1)
        rod.keyframe_insert("location", frame=1)
        rod.keyframe_insert("rotation_euler", frame=F + 1)
        rod.keyframe_insert("location", frame=F + 1)
    kick(rods[3], 14, direction=1, slide=-0.25)      # red midfield kicks it away
    kick(rods[4], 62, direction=-1, slide=0.3)       # blue midfield returns it
    kick(rods[5], 104, direction=1, slide=0.15)      # red forward lofts it
    kick(rods[2], 150, direction=-1, swing=0.3)      # blue defenders flinch
    for rod in rods:
        N.set_interp(rod, "BEZIER", "AUTO")

    # --- Ball: piecewise parabolic flight, baked per frame. Positions are in
    # the parent table's space; it ends at RATIO * start inside the mini table.
    start = Vector((-1.35, -0.75))
    end = start * RATIO
    segments = [  # (to_xy, end_frame, apex_height)
        (start, 14, 0.0),
        (Vector((1.25, 0.35)), 62, 0.45),
        (Vector((0.35, 1.55)), 104, 0.7),
        (end, 196, 2.6),
        (end + Vector((0.03, 0.02)), 214, 0.32 * RATIO * 2),
        (end, 228, 0.1 * RATIO * 2),
        (end, F + 1, 0.0),
    ]
    ball.rotation_mode = "XYZ"
    pos = start
    f0 = 1
    spin = Vector((0.0, 0.0, 0.0))
    for to, f1, apex in segments:
        for f in range(f0, f1 + 1):
            u = (f - f0) / max(1, f1 - f0)
            sc = RATIO ** ((f - 1) / F)
            xy = pos.lerp(to, u)
            z = BALL_R * sc + apex * 4 * u * (1 - u)
            ball.location = (xy.x, xy.y, z)
            ball.scale = (sc, sc, sc)
            # Roll about the axis perpendicular to travel.
            step = (to - pos) / max(1, f1 - f0)
            spin += Vector((step.y, -step.x, 0)) / (BALL_R * sc)
            ball.rotation_euler = (spin.x, spin.y, 0)
            ball.keyframe_insert("location", frame=f)
            ball.keyframe_insert("scale", frame=f)
            ball.keyframe_insert("rotation_euler", frame=f)
        pos = to
        f0 = f1
    N.set_interp(ball, "LINEAR")


def main():
    scene = N.reset_scene("Football_Loop")
    N.setup_cycles(scene, samples=96, preview=N.cli_args()["preview"])
    F = N.LOOP_FRAMES

    table = bpy.data.collections.new("Table")
    scene.collection.children.link(table)
    rods, ball = build_table(table)
    animate(rods, ball)
    # The source collection itself is level 0.

    # Nested levels as collection instances scaled about the centre spot.
    # Level -1 is the giant parent table whose foreground players drift past
    # the camera at the start of the loop, exactly as level 0's do at the end.
    for level in (-2, -1, 1, 2, 3):
        inst = bpy.data.objects.new(f"TableLevel_{level}", None)
        inst.instance_type = "COLLECTION"
        inst.instance_collection = table
        s = RATIO ** level
        inst.scale = (s, s, s)
        scene.collection.objects.link(inst)

    # Camera + lights on one rig scaled by RATIO over the loop: an exact
    # similarity about the centre spot, so frame 241 == frame 1 one level in.
    rig = N.add_empty("ZoomRig", (0, 0, 0))
    look = N.add_empty("Look", (0, 0, 0), parent=rig)
    direction = Vector((0.28, -0.55, 2.0)).normalized()
    d0 = 26.0
    cam = N.add_camera(scene, direction * d0, look, lens=70, fstop=4.0)
    cam.data.sensor_fit = "VERTICAL"
    lights = N.studio_lighting(scene, key_energy=9000, fill_energy=3000, world_strength=0.45, parent=rig, target=look, scale=1.6)
    N.animate_similarity(scene, rig, cam, lights, RATIO, fstop=4.0)

    N.finish(scene, "football_loop")


if __name__ == "__main__":
    main()
