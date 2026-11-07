"""
build_art.py — Arte de portada de "Vertex Forensic Lab", generado por código (sin imágenes de terceros).
Motivo: un enjambre de nodos sobre una rejilla en perspectiva; el rastro cian del Canary Token une
al Scout con el Exploit, y una muralla ámbar (el firewall) corta el paso al enjambre.
Misma paleta que las portadas de "Vertex-Core" y "Vertex-Core SQL".
Salida: arte.png (2000 x 3000, proporción 2:3).

Uso, desde E:\\vertex-forensic-lab\\libro\\portada:
  python build_art.py
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).parent
W, H = 2000, 3000
BG_TOP, BG_BOT = (6, 11, 19), (11, 24, 38)
GRID = (30, 50, 72)
NODE = (70, 100, 130)
CYAN = (34, 211, 238)
AMBER = (245, 158, 11)
RED = (248, 113, 113)

rnd = random.Random(7)
img = Image.new("RGB", (W, H))
px = ImageDraw.Draw(img)
for y in range(H):  # degradado vertical
    t = y / H
    px.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT)))
img = img.convert("RGBA")

# --- rejilla del suelo en perspectiva (mitad inferior) ---
floor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
f = ImageDraw.Draw(floor)
horizon, base = 1450, H + 150
vx = W * 0.60
for k in range(-14, 15):  # líneas que convergen al punto de fuga
    x_far = vx + k * 26
    x_near = vx + k * 260
    f.line([(x_far, horizon), (x_near, base)], fill=GRID + (110,), width=3)
for i in range(1, 26):  # líneas horizontales, más juntas cerca del horizonte
    t = (i / 26) ** 1.8
    y = horizon + (base - horizon) * t
    f.line([(0, y), (W, y)], fill=GRID + (int(40 + 120 * t),), width=2)
img = Image.alpha_composite(img, floor)


def proj(u, v):
    """u en [-1,1] (izquierda-derecha), v en [0,1] (lejos-cerca) -> punto sobre el suelo."""
    t = v ** 1.8
    y = horizon + (base - horizon) * t
    x = vx + u * (260 + 2400 * t)
    return x, y, 0.35 + 1.4 * t  # x, y, escala


# --- el enjambre: nodos repartidos por el suelo ---
nodes = []
for _ in range(120):
    u = rnd.uniform(-0.95, 0.95)
    v = rnd.uniform(0.05, 0.95)
    nodes.append((u, v))

layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(layer)
# conexiones tenues entre nodos cercanos
for i, (u1, v1) in enumerate(nodes):
    for u2, v2 in nodes[i + 1:]:
        if abs(u1 - u2) < 0.18 and abs(v1 - v2) < 0.10:
            x1, y1, s1 = proj(u1, v1)
            x2, y2, s2 = proj(u2, v2)
            d.line([(x1, y1), (x2, y2)], fill=NODE + (int(30 + 60 * (v1 + v2) / 2),), width=2)
for u, v in nodes:
    x, y, s = proj(u, v)
    r = 5 * s
    d.ellipse([x - r, y - r, x + r, y + r], fill=NODE + (int(80 + 140 * v),))

# --- Scout (cian) y Exploit (rojo), y el rastro del Canary Token ---
scout_uv, exploit_uv = (-0.55, 0.55), (0.25, 0.80)
sx, sy, ss = proj(*scout_uv)
ex, ey, es = proj(*exploit_uv)
steps = 60
lift = 420
pts = []
for k in range(steps + 1):  # arco por encima del suelo
    t = k / steps
    x = sx + (ex - sx) * t
    y = sy + (ey - sy) * t - lift * math.sin(math.pi * t)
    pts.append((x, y))
for k in range(0, steps, 2):  # trazo discontinuo
    d.line([pts[k], pts[k + 1]], fill=CYAN + (235,), width=9)
for (x, y, s, col) in [(sx, sy, ss, CYAN), (ex, ey, es, RED)]:
    for rr, al in [(46, 60), (30, 120), (16, 255)]:
        r = rr * s * 0.6
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (al,))

# --- la muralla: firewall ámbar que corta el paso, a la derecha ---
wall = Image.new("RGBA", (W, H), (0, 0, 0, 0))
w = ImageDraw.Draw(wall)
wu = 0.55
for k in range(18):
    v0 = 0.08 + k * 0.05
    x0, y0, s0 = proj(wu, v0)
    x1, y1, s1 = proj(wu, v0 + 0.035)
    h0, h1 = 260 * s0, 260 * s1
    w.polygon([(x0, y0), (x1, y1), (x1, y1 - h1), (x0, y0 - h0)],
              fill=AMBER + (int(60 + 120 * v0),), outline=AMBER + (230,))

glow = Image.alpha_composite(layer, wall).filter(ImageFilter.GaussianBlur(20))
img = Image.alpha_composite(img, glow)
img = Image.alpha_composite(img, layer)
img = Image.alpha_composite(img, wall)

# --- partículas de datos tenues (mitad superior, derecha) ---
fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
g = ImageDraw.Draw(fx)
for _ in range(40):
    x = rnd.randint(int(W * 0.42), W)
    y0 = rnd.randint(250, 1150)
    ln = rnd.randint(120, 480)
    for k in range(0, ln, 22):
        al = int(85 * (1 - k / ln))
        g.rectangle([x, y0 + k, x + 6, y0 + k + 10], fill=CYAN + (al,))
img = Image.alpha_composite(img, fx.filter(ImageFilter.GaussianBlur(1)))

# --- viñeta oscura arriba a la izquierda, donde va el título ---
vig = Image.new("L", (W, H), 0)
v = ImageDraw.Draw(vig)
for i in range(60):
    rad = 1700 - i * 22
    v.ellipse([-rad * 0.9, -rad * 0.7, rad * 0.9, rad * 0.7], fill=int(4 * i))
vig = vig.filter(ImageFilter.GaussianBlur(80))
dark = Image.new("RGBA", (W, H), BG_TOP + (255,))
img = Image.composite(dark, img, vig.point(lambda p: int(p * 0.85)))

img.convert("RGB").save(HERE / "arte.png")
print("OK arte.png", img.size)
