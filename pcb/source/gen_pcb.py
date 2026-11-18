"""Generate Gerber + Excellon files for the rangehood ESP8266 / PC817 board.

Usage: python gen_pcb.py <out_dir>
Writes Gerbers, drill files, a zip for upload, and preview.svg.
Also runs clearance + connectivity checks and exits non-zero on failure.
"""
import math
import os
import sys
import zipfile

OUT = sys.argv[1]
W, H = 80.0, 80.0
P = 2.54
NAME = "rangehood-esp"

pads = []      # dict(x, y, d, drill, net, sq)
tracks = []    # (layer, x1, y1, x2, y2, width, net)
npth = []      # (x, y, drill)
silk = []      # (x1, y1, x2, y2)


def pad(x, y, d, drill, net, sq=False):
    pads.append(dict(x=x, y=y, d=d, drill=drill, net=net, sq=sq))


def trk(layer, pts, w, net):
    for a, b in zip(pts, pts[1:]):
        tracks.append((layer, a[0], a[1], b[0], b[1], w, net))


def sline(*pts):
    for a, b in zip(pts, pts[1:]):
        silk.append((a[0], a[1], b[0], b[1]))


def srect(x1, y1, x2, y2):
    sline((x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1))


def scircle(cx, cy, r, n=48):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    sline(*pts)


# ---- tiny stroke font (4 x 6 grid) ----
O_ = [(1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0)]
P_ = [(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]
FONT = {
    "A": [[(0, 0), (0, 4), (2, 6), (4, 4), (4, 0)], [(0, 3), (4, 3)]],
    "B": [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    "C": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1)]],
    "D": [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (0, 0)]],
    "E": [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    "F": [[(4, 6), (0, 6), (0, 0)], [(0, 3), (3, 3)]],
    "G": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 6), (3, 6)], [(2, 6), (2, 0)], [(1, 0), (3, 0)]],
    "J": [[(4, 6), (4, 1), (3, 0), (1, 0), (0, 1)]],
    "K": [[(0, 0), (0, 6)], [(4, 6), (0, 2)], [(1, 3), (4, 0)]],
    "L": [[(0, 6), (0, 0), (4, 0)]],
    "M": [[(0, 0), (0, 6), (2, 3), (4, 6), (4, 0)]],
    "N": [[(0, 0), (0, 6), (4, 0), (4, 6)]],
    "O": [O_],
    "P": [P_],
    "R": [P_, [(2, 3), (4, 0)]],
    "S": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    "T": [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    "U": [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    "V": [[(0, 6), (2, 0), (4, 6)]],
    "W": [[(0, 6), (1, 0), (2, 3), (3, 0), (4, 6)]],
    "X": [[(0, 0), (4, 6)], [(0, 6), (4, 0)]],
    "Y": [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
    "Z": [[(0, 6), (4, 6), (0, 0), (4, 0)]],
    "0": [O_, [(0.5, 1), (3.5, 5)]],
    "1": [[(1, 5), (2, 6), (2, 0)], [(1, 0), (3, 0)]],
    "2": [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (0, 0), (4, 0)]],
    "3": [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (2, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    "4": [[(3, 0), (3, 6), (0, 2), (4, 2)]],
    "5": [[(4, 6), (0, 6), (0, 3), (3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    "6": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "7": [[(0, 6), (4, 6), (1, 0)]],
    "8": [[(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3)]],
    "9": [[(4, 3), (1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0)]],
    "+": [[(0, 3), (4, 3)], [(2, 1), (2, 5)]],
    "-": [[(0.5, 3), (3.5, 3)]],
    ".": [[(2, 0), (2, 0.4)]],
    "/": [[(0, 0), (4, 6)]],
    " ": [],
}


def text(s, x, y, h, anchor="l"):
    u = h / 6.0
    width = (len(s) * 6 - 2) * u
    if anchor == "c":
        x -= width / 2
    elif anchor == "r":
        x -= width
    for i, ch in enumerate(s):
        for stroke in FONT[ch]:
            sline(*[(x + (i * 6 + px) * u, y + py * u) for px, py in stroke])


# ---------------- layout ----------------
# Wi-Fi Mini (D1 mini) on two 8-pin female headers, same orientation as the
# breadboard version: left column TX..5V, right column RST..3V3, row 1 at top.
xL, xR = 28.57, 51.43
rows = [67.78 - i * P for i in range(8)]
LEFT = ["TX", "RX", "D1", "D2", "D3", "D4", "G", "5V"]
RIGHT = ["RST", "A0", "D0", "D5", "D6", "D7", "D8", "3V3"]
NETS = {"G": "GND", "5V": "5V", "D1": "D1", "D2": "D2", "D5": "D5", "D6": "D6", "D7": "D7"}
for i, y in enumerate(rows):
    pad(xL, y, 1.8, 1.0, NETS.get(LEFT[i], "NC_" + LEFT[i]), sq=(LEFT[i] == "5V"))
    pad(xR, y, 1.8, 1.0, NETS.get(RIGHT[i], "NC_" + RIGHT[i]))
    text(LEFT[i], xL + 1.5, y - 0.6, 1.2, "l")
    text(RIGHT[i], xR - 1.5, y - 0.6, 1.2, "r")
srect(xL - 1.35, rows[-1] - 1.35, xL + 1.35, rows[0] + 1.35)
srect(xR - 1.35, rows[-1] - 1.35, xR + 1.35, rows[0] + 1.35)

# Channels: (label, gpio, centre x)
CH = [("LIGHT", "D1", 20.7), ("MIN", "D2", 33.4), ("MID", "D5", 46.1), ("MAX", "D6", 58.8), ("POWER", "D7", 71.5)]
YT, YO = 5.0, 13.0           # terminal pin row, PC817 bottom pin row
YBUS = YO + P * 3 + 2.0      # GND bus (bottom layer)
for name, gpio, cx in CH:
    p1 = (cx + 1.27, YO + 7.62)
    p2 = (cx - 1.27, YO + 7.62)
    p3 = (cx - 1.27, YO)
    p4 = (cx + 1.27, YO)
    ra = (cx + 1.27, p1[1] + 5.08)
    rb = (cx + 1.27, ra[1] + 10.16)
    tlo = (cx - 2.54, YT)
    thi = (cx + 2.54, YT)
    pad(*p1, 1.6, 0.8, name + "_A", sq=True)
    pad(*p2, 1.6, 0.8, "GND")
    pad(*p3, 1.6, 0.8, name + "_LO")
    pad(*p4, 1.6, 0.8, name + "_HI")
    pad(*ra, 1.6, 0.8, name + "_A")
    pad(*rb, 1.6, 0.8, gpio)
    pad(*tlo, 2.5, 1.3, name + "_LO")
    pad(*thi, 2.5, 1.3, name + "_HI")
    trk("T", [p1, ra], 0.5, name + "_A")
    trk("T", [p3, tlo], 0.5, name + "_LO")
    trk("T", [p4, thi], 0.5, name + "_HI")
    trk("B", [p2, (p2[0], YBUS)], 0.8, "GND")
    # silkscreen
    srect(cx - 2.3, YO + 0.7, cx + 2.3, YO + 6.9)               # PC817 body
    scircle(cx + 1.25, YO + 5.9, 0.35, 16)                       # pin-1 dot
    srect(ra[0] - 1.1, ra[1] + 1.6, ra[0] + 1.1, rb[1] - 1.6)   # resistor body
    srect(cx - 5.08, YT - 3.8, cx + 5.08, YT + 3.8)              # terminal block
    text(name, cx, rb[1] + 2.5, 1.4, "c")
    text("-", tlo[0], YT + 4.3, 1.4, "c")
    text("+", thi[0], YT + 4.3, 1.4, "c")

# Signal routes (top layer)
trk("T", [(xL, rows[2]), (21.97, rows[2]), (21.97, 35.86)], 0.5, "D1")
trk("T", [(xL, rows[3]), (34.67, rows[3]), (34.67, 35.86)], 0.5, "D2")
trk("T", [(xR, rows[3]), (47.37, rows[3]), (47.37, 35.86)], 0.5, "D5")
trk("T", [(xR, rows[4]), (49.5, rows[4]), (49.5, 40.0), (60.07, 40.0), (60.07, 35.86)], 0.5, "D6")
trk("T", [(xR, rows[5]), (72.77, rows[5]), (72.77, 35.86)], 0.5, "D7")

# Hood power terminal (left: 5V, right: GND) + 1000uF capacitor
pcx = 8.0
pad(pcx - 2.54, YT, 2.5, 1.3, "5V", sq=True)
pad(pcx + 2.54, YT, 2.5, 1.3, "GND")
pad(pcx - 2.54, 17.0, 1.8, 1.0, "5V", sq=True)
pad(pcx + 2.54, 17.0, 1.8, 1.0, "GND")
srect(pcx - 5.08, YT - 3.8, pcx + 5.08, YT + 3.8)
text("5V", pcx - 2.54, YT + 4.3, 1.2, "c")
text("GND", pcx + 2.54, YT + 4.3, 1.2, "c")
scircle(pcx, 17.0, 5.0)
text("+", pcx - 3.2, 19.3, 1.2, "c")
text("1000UF", 1.6, 22.8, 1.0, "l")

# Power routes (bottom layer)
trk("B", [(pcx - 2.54, YT), (pcx - 2.54, 44.0), (xL, 44.0), (xL, rows[7])], 1.0, "5V")
trk("B", [(pcx + 2.54, YT), (pcx + 2.54, YBUS), (CH[-1][2] - 1.27, YBUS)], 1.0, "GND")
trk("B", [(xL, rows[6]), (31.0, rows[6]), (31.0, YBUS)], 1.0, "GND")

# Mounting holes (M3)
for hx, hy in [(4, 60), (76, 60), (4, 76), (76, 76)]:
    npth.append((hx, hy, 3.2))
    scircle(hx, hy, 2.9, 32)

text("RANGEHOOD ESP V1", 8.0, 77.0, 1.6, "l")
text("MATCH PIN NAMES TO WIFI MINI", 8.0, 74.6, 1.1, "l")
text("ALL R 330", 54.0, 74.6, 1.1, "l")


# ---------------- checks ----------------
def pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def seg_seg(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b

    def ccw(ax, ay, bx, by, cx, cy):
        return (cy - ay) * (bx - ax) - (by - ay) * (cx - ax)
    d1 = ccw(x3, y3, x4, y4, x1, y1)
    d2 = ccw(x3, y3, x4, y4, x2, y2)
    d3 = ccw(x1, y1, x2, y2, x3, y3)
    d4 = ccw(x1, y1, x2, y2, x4, y4)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return 0.0
    return min(pt_seg(x1, y1, x3, y3, x4, y4), pt_seg(x2, y2, x3, y3, x4, y4),
               pt_seg(x3, y3, x1, y1, x2, y2), pt_seg(x4, y4, x1, y1, x2, y2))


def features(layer):
    f = []
    for p in pads:
        r = p["d"] / 2 * (math.sqrt(2) if p["sq"] else 1)
        f.append(("seg", (p["x"], p["y"], p["x"], p["y"]), r, p["net"]))
    for t in tracks:
        if t[0] == layer:
            f.append(("seg", t[1:5], t[5] / 2, t[6]))
    return f


CLR = 0.2
errors = []
for layer in "TB":
    f = features(layer)
    for i in range(len(f)):
        for j in range(i + 1, len(f)):
            a, b = f[i], f[j]
            d = seg_seg(a[1], b[1]) - a[2] - b[2]
            if a[3] != b[3] and d < CLR:
                errors.append(f"{layer}: {a[3]} vs {b[3]} gap {d:.2f} at {a[1]} / {b[1]}")
    for (hx, hy, hd) in npth:
        for a in f:
            d = pt_seg(hx, hy, *a[1]) - a[2] - hd / 2
            if d < 0.4:
                errors.append(f"{layer}: hole ({hx},{hy}) vs {a[3]} gap {d:.2f}")
    for a in f:
        x1, y1, x2, y2 = a[1]
        m = min(x1, x2, y1, y2, W - max(x1, x2), H - max(y1, y2)) - a[2]
        if m < 0.5:
            errors.append(f"{layer}: {a[3]} too near board edge ({m:.2f})")

# connectivity: union-find over copper items, pads join both layers
items = [("P", i) for i in range(len(pads))] + [("T", i) for i in range(len(tracks))]
parent = list(range(len(items)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def geom(it):
    if it[0] == "P":
        p = pads[it[1]]
        return "TB", (p["x"], p["y"], p["x"], p["y"]), p["d"] / 2, p["net"]
    t = tracks[it[1]]
    return t[0], t[1:5], t[5] / 2, t[6]


for i in range(len(items)):
    li, gi, ri, ni = geom(items[i])
    for j in range(i + 1, len(items)):
        lj, gj, rj, nj = geom(items[j])
        if not set(li) & set(lj):
            continue
        if seg_seg(gi, gj) - ri - rj < 0:
            if ni != nj:
                errors.append(f"SHORT {ni} <-> {nj}")
            parent[find(i)] = find(j)

groups = {}
for i, it in enumerate(items):
    net = geom(it)[3]
    if net.startswith("NC_"):
        continue
    groups.setdefault(net, set()).add(find(i))
for net, g in sorted(groups.items()):
    if len(g) != 1:
        errors.append(f"OPEN net {net}: {len(g)} separate pieces")

print("nets:", ", ".join(f"{n}" for n in sorted(groups)))
print("pads:", len(pads), "tracks:", len(tracks), "holes:", len(npth))
if errors:
    print("CHECK FAILED:")
    for e in errors:
        print("  ", e)
    sys.exit(1)
print("CHECKS PASSED: clearance >= %.2f mm, every net fully connected, no shorts" % CLR)


# ---------------- Gerber output ----------------
def mm(v):
    return str(int(round(v * 1e6)))


class Gerber:
    def __init__(self, func):
        self.func = func
        self.ap = {}
        self.body = []
        self.cur = None

    def ap_id(self, key):
        if key not in self.ap:
            self.ap[key] = 10 + len(self.ap)
        return self.ap[key]

    def use(self, key):
        d = self.ap_id(key)
        if self.cur != d:
            self.body.append(f"D{d}*")
            self.cur = d

    def flash(self, key, x, y):
        self.use(key)
        self.body.append(f"X{mm(x)}Y{mm(y)}D03*")

    def line(self, w, x1, y1, x2, y2):
        self.use(("C", w))
        self.body.append(f"X{mm(x1)}Y{mm(y1)}D02*")
        self.body.append(f"X{mm(x2)}Y{mm(y2)}D01*")

    def write(self, path):
        out = ["G04 Rangehood ESP board*", f"%TF.FileFunction,{self.func}*%", "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%"]
        for key, d in self.ap.items():
            if key[0] == "C":
                out.append(f"%ADD{d}C,{key[1]:.3f}*%")
            else:
                out.append(f"%ADD{d}R,{key[1]:.3f}X{key[1]:.3f}*%")
        out += ["G01*"] + self.body + ["M02*"]
        with open(path, "w", newline="\n") as fh:
            fh.write("\n".join(out) + "\n")


def padkey(p, grow=0.0):
    return ("R" if p["sq"] else "C", round(p["d"] + grow, 3))


os.makedirs(OUT, exist_ok=True)
files = []
for layer, suffix, func in [("T", "F_Cu.gtl", "Copper,L1,Top"), ("B", "B_Cu.gbl", "Copper,L2,Bot")]:
    g = Gerber(func)
    for t in tracks:
        if t[0] == layer:
            g.line(t[5], *t[1:5])
    for p in pads:
        g.flash(padkey(p), p["x"], p["y"])
    files.append((f"{NAME}-{suffix}", g))
for suffix, func in [("F_Mask.gts", "Soldermask,Top"), ("B_Mask.gbs", "Soldermask,Bot")]:
    g = Gerber(func)
    for p in pads:
        g.flash(padkey(p, 0.1), p["x"], p["y"])
    files.append((f"{NAME}-{suffix}", g))
g = Gerber("Legend,Top")
for s in silk:
    g.line(0.15, *s)
files.append((f"{NAME}-F_Silkscreen.gto", g))
g = Gerber("Profile,NP")
for s in [(0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)]:
    g.line(0.1, *s)
files.append((f"{NAME}-Edge_Cuts.gm1", g))
for fname, g in files:
    g.write(os.path.join(OUT, fname))


def excellon(path, holes, plated):
    tools = sorted({h[2] for h in holes})
    out = ["M48", f"; {'PTH' if plated else 'NPTH'} drill file, rangehood ESP board",
           "; FORMAT={-:-/ absolute / metric / decimal}", "FMAT,2", "METRIC"]
    out += [f"T{i + 1}C{d:.3f}" for i, d in enumerate(tools)]
    out += ["%", "G90", "G05"]
    for i, d in enumerate(tools):
        out.append(f"T{i + 1}")
        out += [f"X{x:.3f}Y{y:.3f}" for x, y, dd in holes if dd == d]
    out += ["T0", "M30"]
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


excellon(os.path.join(OUT, f"{NAME}-PTH.drl"), [(p["x"], p["y"], p["drill"]) for p in pads], True)
excellon(os.path.join(OUT, f"{NAME}-NPTH.drl"), npth, False)

zpath = os.path.join(os.path.dirname(OUT.rstrip("/\\")), f"{NAME}-gerbers.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)
print("zip:", zpath)


# ---------------- preview SVG ----------------
S = 10  # px per mm


def X(v):
    return v * S


def Y(v):
    return (H - v) * S


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -20 {W * S + 40} {H * S + 40}">',
       f'<rect x="0" y="0" width="{W * S}" height="{H * S}" fill="#1f5130" rx="6"/>']
for layer, col in [("B", "#4dabf7"), ("T", "#e8a33d")]:
    for t in tracks:
        if t[0] == layer:
            svg.append(f'<line x1="{X(t[1])}" y1="{Y(t[2])}" x2="{X(t[3])}" y2="{Y(t[4])}" '
                       f'stroke="{col}" stroke-width="{t[5] * S}" stroke-linecap="round" opacity="0.85"/>')
for p in pads:
    r = p["d"] / 2 * S
    if p["sq"]:
        svg.append(f'<rect x="{X(p["x"]) - r}" y="{Y(p["y"]) - r}" width="{2 * r}" height="{2 * r}" fill="#d9b44a"/>')
    else:
        svg.append(f'<circle cx="{X(p["x"])}" cy="{Y(p["y"])}" r="{r}" fill="#d9b44a"/>')
    svg.append(f'<circle cx="{X(p["x"])}" cy="{Y(p["y"])}" r="{p["drill"] / 2 * S}" fill="#111"/>')
for hx, hy, hd in npth:
    svg.append(f'<circle cx="{X(hx)}" cy="{Y(hy)}" r="{hd / 2 * S}" fill="#111"/>')
for s in silk:
    svg.append(f'<line x1="{X(s[0])}" y1="{Y(s[1])}" x2="{X(s[2])}" y2="{Y(s[3])}" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>')
svg.append("</svg>")
with open(os.path.join(os.path.dirname(OUT.rstrip("/\\")), "preview.svg"), "w", newline="\n") as fh:
    fh.write("\n".join(svg))
print("preview written")
