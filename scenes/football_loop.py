"""Satisfying Football Infinite Loop (Neilster style) - foosball Droste zoom.

A tabletop foosball table with a miniature copy of itself standing in the
centre circle (and a smaller one inside that). A red striker kicks the ball,
it bounces once on the pitch, the blue keeper lobs it back in a high arc and
it drops into the miniature table at the foot of *its* red striker, who kicks
it at the exact moment the loop restarts.

Physics
-------
Every flight is a true parabola under one gravity constant G (the scene is
"slow motion" scale: G is smaller than 9.8 because the table is 6 units
wide). The bounce keeps horizontal velocity and reflects vertical velocity
with restitution E < 1; the two kicks are impulses, which is where velocity
may change direction. The ball rolls/spins at omega = v / r.

Loop
----
* The whole table lives in one collection; nested levels are collection
  instances scaled by RATIO about the fixed point P of the similarity. The
  mini table stands ON the pitch, so P sits a little above the centre spot:
  P.z = CABINET * RATIO / (1 - RATIO).
* The ball ends the loop at P + RATIO * (start - P), shrinking by RATIO, and
  the camera dollies in by 1/RATIO along a fixed ray through P. Frame 241 is
  the picture of frame 1 one level deeper.

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

# --- Table ---------------------------------------------------------------
W, L = 6.0, 10.0            # playfield (x across, y along)
RAIL_T, RAIL_H = 0.35, 0.75  # cabinet wall thickness / height above pitch
CABINET = 0.9               # cabinet depth below the pitch (it stands on this)
CIRCLE_R = 1.0
RATIO = (2 * CIRCLE_R) / (W + 2 * RAIL_T)   # mini table footprint == centre circle
P_Z = CABINET * RATIO / (1 - RATIO)        # fixed point of the similarity
ROD_Z = 0.55
ROD_R = 0.045
MAN_FOOT_DROP = 0.5          # foot centre below the rod axis
BALL_R = 0.3
G = 2.5                      # scene gravity (units / s^2): slow-mo toy scale
RODS = [  # (y, team, men)  blue attacks +y, red attacks -y
    (-4.1, "blue", 1), (-3.0, "blue", 2), (-1.7, "red", 3), (-0.5, "blue", 5),
    (0.5, "red", 5), (1.7, "blue", 3), (3.0, "red", 2), (4.1, "red", 1),
]
KICK_FRAME_BLUE = 140
F = N.LOOP_FRAMES
FPS = N.FPS


# --- helpers ---------------------------------------------------------------
def link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)


def box(name, size, loc, mat, coll, bevel=None, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    if bevel:
        N.bevel(o, bevel, 3)
    link(o, coll)
    if parent:
        o.parent = parent
    return o


def cylinder(name, radius, depth, loc, rot, mat, coll, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot, vertices=48)
    o = bpy.context.active_object
    o.name = name
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(mat)
    link(o, coll)
    if parent:
        o.parent = parent
    return o


def sphere(name, radius, loc, mat, coll, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc, segments=32, ring_count=16)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(mat)
    link(o, coll)
    if parent:
        o.parent = parent
    return o


def ball_material():
    """Black-and-white panel ball: Voronoi cells thresholded to black/white
    with a thin dark seam between panels."""
    mat = bpy.data.materials.new("Football")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.3
    bsdf.inputs["Coat Weight"].default_value = 0.4
    tex = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 2.2
    vor.inputs["Randomness"].default_value = 0.45
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    panel = nt.nodes.new("ShaderNodeValToRGB")
    panel.color_ramp.interpolation = "CONSTANT"
    panel.color_ramp.elements[0].color = (0.92, 0.92, 0.9, 1)
    panel.color_ramp.elements[1].position = 0.64
    panel.color_ramp.elements[1].color = (0.02, 0.02, 0.02, 1)
    edge = nt.nodes.new("ShaderNodeTexVoronoi")
    edge.feature = "DISTANCE_TO_EDGE"
    edge.inputs["Scale"].default_value = 2.2
    edge.inputs["Randomness"].default_value = 0.45
    seam = nt.nodes.new("ShaderNodeValToRGB")
    seam.color_ramp.elements[0].position = 0.0
    seam.color_ramp.elements[0].color = (0.15, 0.15, 0.15, 1)
    seam.color_ramp.elements[1].position = 0.03
    seam.color_ramp.elements[1].color = (1, 1, 1, 1)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(tex.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(tex.outputs["Object"], edge.inputs["Vector"])
    nt.links.new(vor.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Red"], panel.inputs["Fac"])
    nt.links.new(edge.outputs["Distance"], seam.inputs["Fac"])
    nt.links.new(panel.outputs["Color"], mix.inputs[6])
    nt.links.new(seam.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return mat


def build_man(name, x, team_mat, coll, parent, facing):
    """Classic foosball man: round head, tapered torso, hips, one wedge foot.
    `facing` is +1/-1 along y: the kicking face of the foot."""
    sphere(f"{name}_head", 0.13, (x, 0, 0.17), team_mat, coll, parent, scale=(1, 0.9, 1.05))
    box(f"{name}_neck", (0.1, 0.08, 0.08), (x, 0, 0.06), team_mat, coll, 0.02, parent)
    body = box(f"{name}_torso", (0.26, 0.16, 0.3), (x, 0, -0.1), team_mat, coll, 0.04, parent)
    box(f"{name}_hips", (0.22, 0.14, 0.14), (x, 0, -0.3), team_mat, coll, 0.03, parent)
    box(f"{name}_foot", (0.24, 0.2, 0.16), (x, 0, -MAN_FOOT_DROP), team_mat, coll, 0.03, parent)
    # Shirt stripe for a bit of life.
    stripe = box(f"{name}_stripe", (0.27, 0.17, 0.05), (x, 0, -0.03), N.plastic("Stripe", "#F4F4F0", 0.3, 0.3), coll, 0.01, parent)
    return body


def build_table(coll):
    pitch = N.plastic("Pitch", N.PALETTE["pitch"], roughness=0.32, coat=0.25)
    white = N.plastic("Line", "#F4F4F0", roughness=0.4, coat=0.1, bump=0)
    cab = N.plastic("Cabinet", "#141416", roughness=0.35, coat=0.35)
    chrome = N.chrome()
    teams = {"red": N.plastic("Player_red", N.PALETTE["red"], 0.25, 0.4),
             "blue": N.plastic("Player_blue", N.PALETTE["blue"], 0.25, 0.4)}
    handle = N.plastic("Handle", "#101010", roughness=0.45, coat=0.2)

    # Cabinet: the playfield is the top of a solid slab; walls stand around it.
    box("Slab", (W, L, CABINET), (0, 0, -CABINET / 2), pitch, coll)
    for sx in (-1, 1):
        box("WallSide", (RAIL_T, L + 2 * RAIL_T, CABINET + RAIL_H),
            (sx * (W / 2 + RAIL_T / 2), 0, (RAIL_H - CABINET) / 2), cab, coll, bevel=0.05)
    for sy in (-1, 1):
        box("WallEnd", (W, RAIL_T, CABINET + RAIL_H),
            (0, sy * (L / 2 + RAIL_T / 2), (RAIL_H - CABINET) / 2), cab, coll, bevel=0.05)
        box("GoalMouth", (1.7, RAIL_T + 0.02, 0.45), (0, sy * (L / 2 + RAIL_T / 2), 0.225), cab, coll)
        box("GoalFrame", (1.8, 0.06, 0.5), (0, sy * (L / 2 - 0.03), 0.25), chrome, coll)

    # Markings: thin white strips just above the pitch.
    lw, lh = 0.07, 0.008
    box("Halfway", (W, lw, lh), (0, 0, lh / 2), white, coll)
    for sy in (-1, 1):
        box("Touch", (lw, L, lh), (sy * (W / 2 - lw), 0, lh / 2), white, coll)
        box("GoalLine", (W, lw, lh), (0, sy * (L / 2 - lw), lh / 2), white, coll)
        bw, bd = 3.6, 1.5
        box("BoxFront", (bw, lw, lh), (0, sy * (L / 2 - bd), lh / 2), white, coll)
        for sx in (-1, 1):
            box("BoxSide", (lw, bd, lh), (sx * bw / 2, sy * (L / 2 - bd / 2), lh / 2), white, coll)
    bpy.ops.mesh.primitive_torus_add(major_radius=CIRCLE_R, minor_radius=lw / 2, location=(0, 0, 0),
                                     major_segments=128, minor_segments=8)
    ring = bpy.context.active_object
    ring.name = "CentreCircle"
    ring.scale.z = 0.25
    ring.data.materials.append(white)
    link(ring, coll)

    # Rods with men. Each rod is an empty so it can spin about X.
    rods = []
    for i, (y, team, n) in enumerate(RODS):
        rod = N.add_empty(f"Rod_{i}", (0, y, ROD_Z))
        link(rod, coll)
        cylinder(f"RodBar_{i}", ROD_R, W + 2 * RAIL_T + 2.2, (0, 0, 0), (0, math.pi / 2, 0), chrome, coll, rod)
        for sx in (-1, 1):
            cylinder(f"Handle_{i}", 0.1, 0.6, (sx * (W / 2 + RAIL_T + 1.0), 0, 0), (0, math.pi / 2, 0), handle, coll, rod)
            box(f"Collar_{i}", (0.08, 0.14, 0.14), (sx * (W / 2 + RAIL_T + 0.6), 0, 0), cab, coll, 0.02, rod)
        spacing = W / (n + 1)
        facing = 1 if team == "blue" else -1
        for j in range(n):
            build_man(f"Man_{i}_{j}", -W / 2 + spacing * (j + 1), teams[team], coll, rod, facing)
        rods.append(rod)

    ball = sphere("Ball", BALL_R, (0, 0, BALL_R), ball_material(), coll)
    return rods, ball


# --- animation -------------------------------------------------------------
def kick(rod, frame, sign, wind=0.95, follow=0.55):
    """Wind-up then strike at `frame`. sign=+1 swings the foot toward +y."""
    keys = [(frame - 14, 0.0), (frame - 5, -sign * wind), (frame, 0.0),
            (frame + 4, sign * follow), (frame + 18, 0.0)]
    for f, rx in keys:
        rod.rotation_euler = (rx, 0, 0)
        rod.keyframe_insert("rotation_euler", frame=f)


def man_foot_point(rod_y, x, sign):
    """Where the ball sits when touching the kicking face of a man's foot."""
    return Vector((x, rod_y + sign * (0.1 + BALL_R), BALL_R))


def parabola(p0, p1, frames):
    """Per-frame positions and velocities for a projectile from p0 to p1 in
    `frames` frames under gravity G. Returns list of (pos, vel)."""
    T = frames / FPS
    vh = (p1.xy - p0.xy) / T
    vz0 = (p1.z - p0.z) / T + G * T / 2
    out = []
    for i in range(frames + 1):
        t = i / FPS
        pos = Vector((p0.x + vh.x * t, p0.y + vh.y * t, p0.z + vz0 * t - 0.5 * G * t * t))
        vel = Vector((vh.x, vh.y, vz0 - G * t))
        out.append((pos, vel))
    return out


def animate(rods, ball):
    red_striker = rods[6]   # red, y=3.0, 2 men at x=-1, 1 -> kicker at x=-1 faces -y
    blue_keeper = rods[0]   # blue, y=-4.1, 1 man at x=0 faces +y
    for rod in rods:
        rod.rotation_euler = (0, 0, 0)
        rod.keyframe_insert("rotation_euler", frame=1)
        rod.keyframe_insert("rotation_euler", frame=F + 1)
    # Red striker strikes exactly at the seam (frame 241 == frame 1).
    kick(red_striker, 1, sign=-1)
    kick(red_striker, F + 1, sign=-1)
    kick(blue_keeper, KICK_FRAME_BLUE, sign=+1)
    # Idle: the other rods drift a little so the table feels alive.
    for i, rod in enumerate(rods):
        if rod in (red_striker, blue_keeper):
            continue
        amp = 0.06 + 0.02 * (i % 3)
        for f in range(1, F + 2, 40):
            ph = 2 * math.pi * ((f - 1) / F) * (1 + i % 2)
            rod.rotation_euler = (amp * math.sin(ph), 0, 0)
            rod.keyframe_insert("rotation_euler", frame=f)
    for rod in rods:
        N.set_interp(rod, "BEZIER", "AUTO")

    # --- Ball. Start A: at the red striker's foot the instant it is struck.
    A = man_foot_point(3.0, -1.0, -1)
    K = man_foot_point(-4.1, 0.0, +1)                 # blue keeper's foot
    P = Vector((0, 0, P_Z))
    Lnd = P + (A - P) * RATIO                         # landing = A one level deeper
    E = 0.62                                          # restitution of the pitch bounce
    # Flight 1 + bounce arc 2 go A -> K in a straight line (horizontal
    # velocity is preserved by the bounce), so the bounce point splits the
    # distance 1 : E and the time likewise.
    frames_AK = KICK_FRAME_BLUE - 1
    f1 = round(frames_AK / (1 + E))
    f2 = frames_AK - f1
    B = A + (K - A) * (f1 / frames_AK)
    # The ball shrinks through the loop, so its resting height on the parent
    # pitch at a given frame is BALL_R * scale(frame).
    B.z = BALL_R * RATIO ** (f1 / F)
    K.z = BALL_R * RATIO ** ((KICK_FRAME_BLUE - 1) / F)
    seg1 = parabola(A, B, f1)
    seg2 = parabola(B, K, f2)
    seg3 = parabola(K, Lnd, F + 1 - KICK_FRAME_BLUE)
    # Sanity: the bounce must lose energy, the keeper's lob is an impulse.
    vz_in, vz_out = seg1[-1][1].z, seg2[0][1].z
    assert vz_out < -vz_in, "bounce would gain energy; adjust E or timing"

    ball.rotation_mode = "QUATERNION"
    from mathutils import Quaternion
    quat = Quaternion((1, 0, 0, 0))
    frame = 1
    for seg in (seg1, seg2, seg3):
        for i, (pos, vel) in enumerate(seg):
            if i == 0 and frame > 1:
                continue  # shared endpoint
            f = frame + i - (0 if frame == 1 else 1)
            sc = RATIO ** ((f - 1) / F)
            r = BALL_R * sc
            ball.location = (pos.x, pos.y, pos.z)
            ball.scale = (sc, sc, sc)
            # Spin about the horizontal axis perpendicular to travel, omega = v / r.
            vh = Vector((vel.x, vel.y, 0))
            if vh.length > 1e-6:
                axis = Vector((0, 0, 1)).cross(vh.normalized())
                quat = Quaternion(axis, (vh.length / r) / FPS) @ quat
            ball.rotation_quaternion = quat
            ball.keyframe_insert("location", frame=f)
            ball.keyframe_insert("scale", frame=f)
            ball.keyframe_insert("rotation_quaternion", frame=f)
        frame = f + 1
    N.set_interp(ball, "LINEAR")
    return A, K, B, Lnd


def main():
    scene = N.reset_scene("Football_Loop")
    N.setup_cycles(scene, samples=96, preview=N.cli_args()["preview"])

    table = bpy.data.collections.new("Table")
    scene.collection.children.link(table)
    rods, ball = build_table(table)
    animate(rods, ball)

    # Nested levels: instances scaled about the fixed point P. Level -1 is
    # the giant parent whose foreground men pass the camera at the start,
    # exactly as level 0's do at the end.
    P = Vector((0, 0, P_Z))
    for level in (-2, -1, 1, 2, 3, 4):
        s = RATIO ** level
        inst = bpy.data.objects.new(f"TableLevel_{level}", None)
        inst.instance_type = "COLLECTION"
        inst.instance_collection = table
        inst.scale = (s, s, s)
        inst.location = P + (Vector((0, 0, 0)) - P) * s
        scene.collection.objects.link(inst)

    rig = N.add_empty("ZoomRig", P)
    look = N.add_empty("Look", (0, 0, 0), parent=rig)
    direction = Vector((0.22, -0.42, 1.7)).normalized()
    d0 = 25.0
    cam = N.add_camera(scene, P + direction * d0, look, lens=60, fstop=4.0)
    cam.data.sensor_fit = "VERTICAL"
    lights = N.studio_lighting(scene, key_energy=12000, fill_energy=4000, world_strength=0.45,
                               parent=rig, target=look, scale=1.8)
    # animate_similarity scales about the rig origin; the camera ray is
    # expressed relative to P so the dolly converges on the fixed point.
    _similarity_about(scene, rig, cam, lights, P, direction * d0, fstop=4.0)
    N.finish(scene, "football_loop")


def _similarity_about(scene, rig, cam, lights, P, cam_offset, fstop):
    """Like N.animate_similarity but with the fixed point at P, not the origin."""
    base = [light.data.energy for light in lights]
    cam.data.dof.focus_object = None
    for f in range(1, F + 2):
        s = RATIO ** ((f - 1) / F)
        rig.scale = (s, s, s)
        rig.keyframe_insert("scale", frame=f)
        cam.location = P + cam_offset * s
        cam.keyframe_insert("location", frame=f)
        cam.data.dof.focus_distance = cam_offset.length * s
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
        cam.data.dof.aperture_fstop = fstop / s
        cam.data.dof.keyframe_insert("aperture_fstop", frame=f)
        for light, e in zip(lights, base):
            light.data.energy = e * s * s
            light.data.keyframe_insert("energy", frame=f)
    N.set_interp(rig, "LINEAR")
    N.set_interp(cam, "LINEAR")


if __name__ == "__main__":
    main()
