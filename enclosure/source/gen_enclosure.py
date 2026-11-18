"""3D-printable enclosure (box + lid) for the 80x80 mm rangehood ESP PCB.

Usage: python gen_enclosure.py <out_dir>
Writes box.stl, lid.stl and preview PNGs. Units: mm.
"""
import os
import sys

import manifold3d as m3
import numpy as np
import trimesh

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

PCB = 80.0          # board is 80 x 80
GAP = 1.0           # clearance around board
WALL = 2.0
FLOOR = 2.0
STANDOFF = 5.0      # room for solder joints under the board
PCB_T = 1.6
HEADROOM = 25.0     # tallest part: upright 1000uF cap (~20 mm) + margin
IN = PCB + 2 * GAP  # inner size 82
OUTS = IN + 2 * WALL  # outer size 86
HEIGHT = round(FLOOR + STANDOFF + PCB_T + HEADROOM)  # 34
SEG = 64

pcb_x0 = WALL + GAP   # board origin inside the box
pcb_z0 = FLOOR + STANDOFF


def box(x0, y0, z0, x1, y1, z1):
    return m3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(x, y, z0, z1, d):
    return m3.Manifold.cylinder(z1 - z0, d / 2, d / 2, SEG).translate([x, y, z0])


def bx(px, py):  # board coords -> box coords
    return pcb_x0 + px, pcb_x0 + py


CORNERS = [(-2.0, -2.0), (OUTS + 2.0, -2.0), (-2.0, OUTS + 2.0), (OUTS + 2.0, OUTS + 2.0)]
COL_D = 9.0

# ---------------- box ----------------
body = box(0, 0, 0, OUTS, OUTS, HEIGHT) - box(WALL, WALL, FLOOR, OUTS - WALL, OUTS - WALL, HEIGHT + 1)
for cx, cy in CORNERS:                      # lid screw columns
    body += cyl(cx, cy, 0, HEIGHT, COL_D)
for side in (-1, 1):                        # mounting ears with 4.5 mm holes
    x0 = -12 if side < 0 else OUTS
    ear = box(x0, OUTS / 2 - 10, 0, x0 + 12, OUTS / 2 + 10, 3)
    hx = -6 if side < 0 else OUTS + 6
    body += ear
    body -= cyl(hx, OUTS / 2, -1, 4, 4.5)

# PCB standoffs at the 4 mounting holes, pilot for M3 self-tapping screws
for px, py in [(4, 60), (76, 60), (4, 76), (76, 76)]:
    x, y = bx(px, py)
    body += cyl(x, y, FLOOR - 0.5, pcb_z0, 6.5)
    body -= cyl(x, y, FLOOR, pcb_z0 + 1, 2.5)
# plain support posts under the terminal edge (screwing terminals pushes down)
for px in (1.5, 40.0, 78.5):
    x, y = bx(px, 1.5)
    body += box(x - 1.5, y - 1.5, FLOOR - 0.5, x + 1.5, y + 1.5, pcb_z0)

for cx, cy in CORNERS:                      # lid screw pilot holes
    body -= cyl(cx, cy, HEIGHT - 15, HEIGHT + 1, 2.6)

# wire slot in the front wall, in line with the screw terminals
SLOT_Z0, SLOT_Z1 = pcb_z0 + PCB_T + 0.5, pcb_z0 + PCB_T + 10.5
sx0, _ = bx(2.0, 0)
sx1, _ = bx(78.0, 0)
r = (SLOT_Z1 - SLOT_Z0) / 2
slot = box(sx0 + r, -1, SLOT_Z0, sx1 - r, WALL + 1, SLOT_Z1)
for xx in (sx0 + r, sx1 - r):
    slot += m3.Manifold.cylinder(WALL + 2, r, r, SEG).rotate([-90, 0, 0]).translate([xx, -1, SLOT_Z0 + r])
body -= slot

# ---------------- lid ----------------
LID_T = 2.0
LIP_H, LIP_W, LIP_CLR = 3.0, 1.6, 0.3
lid = box(0, 0, 0, OUTS, OUTS, LID_T)
for cx, cy in CORNERS:
    lid += cyl(cx, cy, 0, LID_T, COL_D)
lo, hi = WALL + LIP_CLR, OUTS - WALL - LIP_CLR
lid += box(lo, lo, LID_T, hi, hi, LID_T + LIP_H) - box(lo + LIP_W, lo + LIP_W, LID_T - 1, hi - LIP_W, hi - LIP_W, LID_T + LIP_H + 1)
for cx, cy in CORNERS:
    lid -= cyl(cx, cy, -1, LID_T + 1, 3.4)
# vent slots over the middle of the board
for i in range(5):
    y = OUTS / 2 - 12 + i * 6
    lid -= box(OUTS / 2 - 15, y - 1, -1, OUTS / 2 + 15, y + 1, LID_T + 1)


def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))


tb, tl = to_trimesh(body), to_trimesh(lid)
for name, t in [("box", tb), ("lid", tl)]:
    assert t.is_watertight, name + " not watertight"
    t.export(os.path.join(OUT, f"rangehood-{name}.stl"))
    ext = t.bounds[1] - t.bounds[0]
    print(f"{name}: {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm, watertight={t.is_watertight}, volume={t.volume / 1000:.1f} cm3")
print("inner cavity:", IN, "x", IN, "; PCB top at z =", pcb_z0 + PCB_T, "; clearance above PCB =", HEIGHT - pcb_z0 - PCB_T - LIP_H)

# ---------------- previews ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def render(t, path, elev, azim, extra=None):
    fig = plt.figure(figsize=(7, 6), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    tris = t.vertices[t.faces]
    light = np.array([0.4, -0.5, 0.8])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(t.face_normals @ light, 0, 1)
    cols = np.c_[0.25 + 0.5 * shade, 0.45 + 0.45 * shade, 0.75 * shade + 0.2, np.ones_like(shade)]
    ax.add_collection3d(Poly3DCollection(tris, facecolors=np.clip(cols, 0, 1), edgecolor="none"))
    if extra is not None:
        ax.add_collection3d(Poly3DCollection(extra.vertices[extra.faces], facecolors=(0.1, 0.5, 0.2, 0.9), edgecolor="none"))
    lo_, hi_ = t.bounds
    c = (lo_ + hi_) / 2
    s = (hi_ - lo_).max() / 2
    ax.set_xlim(c[0] - s, c[0] + s)
    ax.set_ylim(c[1] - s, c[1] + s)
    ax.set_zlim(c[2] - s, c[2] + s)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


pcb_mesh = to_trimesh(box(pcb_x0, pcb_x0, pcb_z0, pcb_x0 + PCB, pcb_x0 + PCB, pcb_z0 + PCB_T))
render(tb, os.path.join(OUT, "preview-box.png"), 35, -60, pcb_mesh)
render(tb, os.path.join(OUT, "preview-box-empty.png"), 55, -110)
render(tl, os.path.join(OUT, "preview-lid.png"), 40, -60)
print("previews written")
