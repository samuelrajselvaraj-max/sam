# Neilster-style satisfying loops in Blender

Procedural recreations of the content on the
[Neilster](https://www.youtube.com/@NEILSTER666/shorts) YouTube Shorts channel:
8-second, 9:16, perfectly looping CGI animations of glossy toy-plastic objects
(Rubik's cubes, dice) with soft studio lighting, shallow depth of field and a
self-similar "infinite" structure.

Everything is a Python script that builds the whole scene from nothing, so
there are no `.blend` files to download: open a script in Blender and run it.

| Scene | Script | Reference short | Loop mechanism |
| --- | --- | --- | --- |
| Rubik's Cube Slide and Drop | `scenes/rubiks_slide_drop.py` | "Satisfying Rubik's Cube Slide and Drop Perfect Loop" | 3x infinite zoom: the dropped cube's top face becomes the next floor |
| Dice Roll and Drop | `scenes/dice_roll_loop.py` | "Satisfying Dice Roll and Drop Perfect Loop" | Square-helix staircase of dice; camera orbits 360 degrees and descends 4 steps |

Preview frames (25 %, 24 samples) are in `renders/<scene>/`.

## Running

**In Blender (any 4.x or 5.x):** Scripting workspace, *Text > Open* one of the
`scenes/*.py` files from this checkout, press *Run Script*. The scene is built
in a fresh file; press space to play, F12 to render. (Open the script from
disk rather than pasting it, so it can find `common/neilster.py`.)

**From the command line with a Blender install:**

```bash
blender -b -P scenes/dice_roll_loop.py -- --render --preview   # 4 preview stills
blender -b -P render_all.py -- --preview                       # both loops as MP4
blender -b -P render_all.py                                    # full quality
```

**Without Blender installed** (uses the `bpy` wheel, Python 3.11):

```bash
pip install bpy
python render_all.py --preview
```

Flags understood by every scene script: `--render` (write stills),
`--preview` (25 % size, 24 samples), `--frame=N` (repeatable),
`--samples=N`, `--percent=N` (render_all only), `--save` (also write `blend/<scene>.blend`).

## How the loops close

Both scenes are built so that frame 241 is pixel-identical to frame 1;
`render_all.py` renders frames 1-240, so the MP4 loops with no visible seam.

* **Rubik's** – every level's top face is at z = 0 with its centre cubie
  missing. The hero cube is exactly one cubie wide and drops flush into the
  hole; its own top face then has a hole for the next (never-rendered) cube.
  The camera dollies along a fixed ray by a factor of 3, exponentially so the
  zoom speed looks constant.
* **Dice** – steps form a square helix: four steps turn 360 degrees and drop
  four big-die heights, colours repeat every four. The small die makes eight
  90-degree tumbles about alternating axes, which multiply out to the identity,
  so even its pips line up at the seam.

Three details that are easy to miss when making an infinite-zoom loop, all
handled in `common/neilster.py`:

1. Lights must be part of the similarity. They ride on a rig that scales with
   the zoom (area lights scale with their parent) and their power is keyframed
   as `energy * scale^2` so irradiance stays constant.
2. Depth of field is not scale invariant. The f-stop is keyframed as
   `fstop / scale` so the physical aperture shrinks with the world.
3. Bevel widths must be in world units (or in the unit-cube's local units for
   scaled primitives) or nested levels get different corner radii.

## Layout

```
common/neilster.py   shared helpers: scene setup, toy-plastic materials, studio
                     lighting, camera, tumble baker, similarity rig, CLI
scenes/*.py          one self-contained builder per short
render_all.py        batch render to PNG sequences + MP4
renders/<scene>/     preview stills (and MP4 output after render_all.py)
```

## Sound design

The scripts render picture only. For the channel's feel, add in the edit:
a crisp plastic *clack* on every die/cube landing (dice: one every second;
Rubik's: one drop at 0:04), and a soft slide/whoosh on the Rubik's glide.
