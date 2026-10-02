#!/usr/bin/env python3
"""Render every Neilster-style loop to a 9:16 MP4.

Usage (from the repo root):
    python render_all.py                 # all scenes, full quality, PNG frames + MP4
    python render_all.py --preview       # 25% size, 24 samples: quick motion check
    python render_all.py --percent=50 --samples=40   # mid-quality
    python render_all.py rubiks_slide_drop --samples=64
    blender -b -P render_all.py -- --preview    # same, using a Blender install

Each scene writes renders/<scene>/frame_####.png and renders/<scene>/<scene>.mp4.
Only frames 1..240 are rendered: frame 241 equals frame 1, so the MP4 loops
perfectly when played on repeat (YouTube Shorts loop automatically).
"""
import os
import runpy
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SCENES = ["rubiks_slide_drop", "dice_roll_loop"]
sys.path.insert(0, os.path.join(ROOT, "common"))
import bpy  # noqa: E402
import neilster as N  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
wanted = [a for a in argv if not a.startswith("-")] or SCENES
flags = [a for a in argv if a.startswith("-")]

for scene_name in wanted:
    out = os.path.join(ROOT, "renders", scene_name)
    os.makedirs(out, exist_ok=True)
    # Build the scene without rendering stills, then render the full range.
    sys.argv = ["blender", "--"] + [f for f in flags if f != "--render"]
    runpy.run_path(os.path.join(ROOT, "scenes", f"{scene_name}.py"), run_name="__main__")
    scene = bpy.context.scene
    if "--preview" in flags:
        scene.render.resolution_percentage = 25
    for flag in flags:
        if flag.startswith("--percent="):
            scene.render.resolution_percentage = int(flag.split("=")[1])
    scene.frame_end = N.LOOP_FRAMES
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(out, "frame_")
    bpy.ops.render.render(animation=True)
    mp4 = os.path.join(out, f"{scene_name}.mp4")
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(N.FPS),
                        "-i", os.path.join(out, "frame_%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", mp4], check=True)
        print("wrote", mp4)
    else:
        print("ffmpeg not found; frames are in", out)
