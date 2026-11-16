# Redraws Domino-Chain's figure as a new character, an amber builder ant in a yellow hard
# hat, keeping every pose of the stick figure: its limbs are the stick figure's, and the head,
# thorax, abdomen, eyes, antennae and hat are drawn where the stick figure has its head and torso.
import math, sys
import numpy as np, cairo
from PIL import Image
from scipy import ndimage as ndi
from analyse import masks, head, body

K = 4  # drawn at 4x, then reduced
C = {
    'outline': (0.10, 0.05, 0.02), 'limb': (0.30, 0.13, 0.06), 'limb_hi': (0.45, 0.22, 0.11),
    'body': (0.80, 0.33, 0.12), 'shade': (0.55, 0.20, 0.07), 'hi': (0.96, 0.58, 0.30),
    'hat': (0.98, 0.78, 0.16), 'hat_shade': (0.80, 0.58, 0.05), 'hat_hi': (1.0, 0.93, 0.60),
    'eye': (1, 1, 1), 'pupil': (0.08, 0.05, 0.04),
}
LEFT, RIGHT, FRONT = -1, 1, 0

def facing(name):
    if name.endswith('Left'): return LEFT
    if name.endswith('Right'): return RIGHT
    return FRONT

def rgb(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)

def ellipse(ctx, cx, cy, rx, ry, ang=0.0):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang); ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()

class Head:
    """head-local coordinates: x towards where the ant looks, y up, in frame pixels"""
    def __init__(self, ctx, cx, cy, up, face):
        self.ctx, self.cx, self.cy, self.face = ctx, cx, cy, face
        self.ux, self.uy = up                       # screen direction of local +y
        s = face if face else 1
        self.fx, self.fy = -up[1] * s, up[0] * s    # screen direction of local +x
        if self.fx * (s) < 0:                       # keep +x pointing the way the ant faces
            self.fx, self.fy = -self.fx, -self.fy
    def p(self, x, y):
        return (K * (self.cx + x * self.fx + y * self.ux), K * (self.cy + x * self.fy + y * self.uy))
    def ang(self):
        return math.atan2(self.fy, self.fx)

def render(f, name, idx, override=None):
    core, al = masks(f)
    W, H = f.size
    hd = head(core) if override is None or 'head' not in override else override['head']
    face = facing(name)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W * K, H * K)
    ctx = cairo.Context(surf)
    if hd is None:
        return f
    hx, hy, hr = hd
    b = body(core, hd)
    if b:
        (nx, ny), (px, py), sk, foot = b
    else:
        nx, ny, px, py = hx, hy + hr, hx, hy + 17
    if override and 'hip' in override:
        px, py = override['hip']
    tl = math.hypot(px - hx, py - hy)
    if tl < 10 or tl > 32:
        px, py = hx, hy + 17
    ux, uy = hx - px, hy - py; n = math.hypot(ux, uy); ux, uy = ux / n, uy / n   # up the torso
    hr = max(5.5, min(hr, 7.0))

    # the limbs: the stick figure without its head and torso, smoothed and a little thinner
    lim = core.copy()
    yy, xx = np.mgrid[0:H, 0:W]
    lim &= (xx - hx) ** 2 + (yy - hy) ** 2 > (hr + 1.5) ** 2
    # the torso line, neck to hip, is drawn as the thorax
    ax, ay = hx + ux * -hr, hy + uy * -hr
    vx, vy = px - ax, py - ay; L2 = vx * vx + vy * vy
    t = np.clip(((xx - ax) * vx + (yy - ay) * vy) / L2, 0, 1)
    dtor = np.hypot(xx - (ax + t * vx), yy - (ay + t * vy))
    lim_hi = np.array(Image.fromarray((lim * 255).astype(np.uint8)).resize((W * K, H * K), Image.BICUBIC)).astype(float)
    lim_hi = ndi.gaussian_filter(lim_hi, 1.6)
    tor_hi = np.array(Image.fromarray((np.clip(dtor - 2.2, 0, 3) / 3 * 255).astype(np.uint8)).resize((W * K, H * K), Image.BILINEAR)) / 255.0
    limbs = (lim_hi > 135) & (tor_hi > 0.35)

    # paint: abdomen (behind), limbs, thorax, head, eyes, hat, antennae
    back = -face if face else 0
    # the abdomen hangs back from the hip: the torso direction turned towards the back
    if face:
        bx, by = -ux, -uy                                   # down the torso
        qx, qy = (uy, -ux) if (uy * back) > 0 or (uy == 0 and -ux * back > 0) else (-uy, ux)
        if qx * back < 0: qx, qy = -qx, -qy
        gx, gy = 0.55 * bx + 0.83 * qx, 0.55 * by + 0.83 * qy
        gcx, gcy = px + gx * 8.0, py + gy * 8.0
        ga = math.atan2(gy, gx)
        ellipse(ctx, K * gcx, K * gcy, K * 9.4, K * 6.6, ga); rgb(ctx, C['body']); ctx.fill()
        # bands across it, and a shine
        for d in (-1.0, 3.2):
            ctx.save(); ellipse(ctx, K * gcx, K * gcy, K * 9.4, K * 6.6, ga); ctx.clip()
            cx_, cy_ = gcx + gx * d, gcy + gy * d
            ctx.set_line_width(K * 1.1); rgb(ctx, C['shade'])
            ctx.move_to(K * (cx_ - gy * 7), K * (cy_ + gx * 7)); ctx.line_to(K * (cx_ + gy * 7), K * (cy_ - gx * 7)); ctx.stroke()
            ctx.restore()
        ellipse(ctx, K * (gcx - gx * 2 + ux * 2.2), K * (gcy - gy * 2 + uy * 2.2), K * 3.2, K * 1.4, ga); rgb(ctx, C['hi'], 0.8); ctx.fill()
    else:
        # seen from the front, the abdomen shows between the legs
        ellipse(ctx, K * px, K * (py + 2.5), K * 6.0, K * 6.8); rgb(ctx, C['shade']); ctx.fill()

    img = np.ndarray((H * K, W * K, 4), np.uint8, surf.get_data(), strides=(surf.get_stride(), 4, 1))
    surf.flush()
    lc = np.array([C['limb'][2], C['limb'][1], C['limb'][0], 1.0]) * 255
    img[limbs] = lc.astype(np.uint8)
    surf.mark_dirty()

    # thorax: a chunky segment from the neck down most of the torso, then a thin waist to the hip
    tx, ty = hx - ux * (hr + 0.3), hy - uy * (hr + 0.3)
    ex, ey = tx + (px - tx) * 0.72, ty + (py - ty) * 0.72
    mx, my = (tx + ex) / 2, (ty + ey) / 2
    tl2 = math.hypot(ex - tx, ey - ty) / 2 + 1.8
    ta = math.atan2(ey - ty, ex - tx)
    wx, wy = tx + (px - tx) * 0.9, ty + (py - ty) * 0.9
    ellipse(ctx, K * wx, K * wy, K * 2.0, K * 1.7, ta); rgb(ctx, C['shade']); ctx.fill()
    ellipse(ctx, K * mx, K * my, K * tl2, K * 4.3, ta); rgb(ctx, C['body']); ctx.fill()
    sd = 1 if face >= 0 else -1
    ellipse(ctx, K * (mx + uy * 1.6 * sd - ux * 0.6), K * (my - ux * 1.6 * sd - uy * 0.6), K * tl2 * 0.55, K * 1.3, ta); rgb(ctx, C['hi'], 0.75); ctx.fill()

    # head
    h = Head(ctx, hx, hy, (ux * -1, uy * -1) if False else (-ux, -uy), face)
    # local +y is up: screen up is -(down); the torso's up vector is (ux, uy) towards the head
    # the head tilts with the torso, but not by more than 20 degrees, so the hat stays on top
    ang = math.atan2(ux, -uy)                       # 0 upright, positive leaning right
    ang = max(-0.35, min(0.35, ang))
    hux, huy = math.sin(ang), -math.cos(ang)
    h.ux, h.uy = hux, huy
    s = face if face else 1
    h.fx, h.fy = (-huy, hux) if s > 0 else (huy, -hux)
    if h.fx * s < 0: h.fx, h.fy = -h.fx, -h.fy
    def P(x, y): # local (x right/forward, y up) to screen; screen y grows down
        return (K * (hx + x * h.fx + y * h.ux), K * (hy + x * h.fy + y * h.uy))
    hw, hh = hr + 2.4, hr + 1.4
    ha = math.atan2(h.fy, h.fx)
    c = P(0.8 * (1 if face else 0), 0)
    ellipse(ctx, c[0], c[1], K * hw, K * hh, ha); rgb(ctx, C['body']); ctx.fill()
    c = P(-1.5 * (1 if face else 0), -2.5)
    ellipse(ctx, c[0], c[1], K * hw * 0.7, K * hh * 0.45, ha); rgb(ctx, C['shade'], 0.35); ctx.fill()

    # antennae from under the hat brim, curving forward
    phase = math.sin(idx * 1.3) * 0.8
    def antenna(x0, y0, x1, y1, x2, y2):
        ctx.set_line_width(K * 1.0); rgb(ctx, C['limb'])
        ctx.move_to(*P(x0, y0)); ctx.curve_to(*P(x1, y1), *P(x1 + (x2 - x1) * 0.5, y2), *P(x2, y2)); ctx.stroke()
        ellipse(ctx, *P(x2, y2), K * 1.3, K * 1.3); rgb(ctx, C['limb']); ctx.fill()
    if face:
        antenna(1.0, hh - 1.5, 4.5, hh + 4, hw + 4 + phase, hh + 6.5)
        antenna(3.0, hh - 2.0, 7.5, hh + 2, hw + 7.5 - phase, hh + 3.5)
    else:
        antenna(-2.0, hh - 1.5, -5, hh + 4, -hw - 3 - phase, hh + 6)
        antenna(2.0, hh - 1.5, 5, hh + 4, hw + 3 + phase, hh + 6)

    # eyes
    if face:
        c = P(3.0, 0.8); ellipse(ctx, c[0], c[1], K * 2.9, K * 3.4, ha); rgb(ctx, C['eye']); ctx.fill()
        c = P(4.1, 0.4); ellipse(ctx, c[0], c[1], K * 1.5, K * 1.9, ha); rgb(ctx, C['pupil']); ctx.fill()
        c = P(4.5, 1.2); ellipse(ctx, c[0], c[1], K * 0.55, K * 0.55, ha); rgb(ctx, C['eye']); ctx.fill()
        # mouth
        ctx.set_line_width(K * 0.8); rgb(ctx, C['outline'])
        ctx.move_to(*P(hw - 1.2, -3.0)); ctx.line_to(*P(hw - 3.2, -3.6)); ctx.stroke()
    else:
        for ex in (-2.7, 2.7):
            c = P(ex, 0.4); ellipse(ctx, c[0], c[1], K * 2.5, K * 3.0, ha); rgb(ctx, C['eye']); ctx.fill()
            c = P(ex * 0.9, -0.2); ellipse(ctx, c[0], c[1], K * 1.2, K * 1.5, ha); rgb(ctx, C['pupil']); ctx.fill()
            c = P(ex * 0.9 + 0.4, 0.5); ellipse(ctx, c[0], c[1], K * 0.45, K * 0.45, ha); rgb(ctx, C['eye']); ctx.fill()
        ctx.set_line_width(K * 0.8); rgb(ctx, C['outline'])
        ctx.move_to(*P(-1.6, -3.4)); ctx.curve_to(*P(-0.6, -4.3), *P(0.6, -4.3), *P(1.6, -3.4)); ctx.stroke()

    # hard hat: a dome with a brim reaching forward, and a ridge
    hy0 = hh - 2.2
    ctx.save()
    ctx.move_to(*P(-hw - 0.4, hy0))
    steps = 16
    for i in range(steps + 1):
        a = math.pi - math.pi * i / steps
        ctx.line_to(*P((hw + 0.4) * math.cos(a) + (0.6 if face else 0), hy0 + 5.4 * math.sin(a)))
    ctx.close_path(); rgb(ctx, C['hat']); ctx.fill()
    ctx.restore()
    bx0, bx1 = (-hw - 0.8, hw + 4.2) if face else (-hw - 2.2, hw + 2.2)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_width(K * 1.7); rgb(ctx, C['hat_shade'])
    ctx.move_to(*P(bx0, hy0)); ctx.line_to(*P(bx1, hy0)); ctx.stroke()
    ctx.set_line_width(K * 1.0); rgb(ctx, C['hat_hi'], 0.9)
    ctx.move_to(*P(-1.0 + (0.6 if face else 0), hy0 + 1.2)); ctx.line_to(*P(-1.0 + (0.6 if face else 0), hy0 + 5.0)); ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)

    # outline around it all, then reduce to the frame size
    surf.flush()
    a = img[..., 3].astype(float)
    out = ndi.maximum_filter(a, size=5)
    rgba = np.zeros((H * K, W * K, 4), float)
    oc = np.array(C['outline'])
    rgba[..., :3] = oc; rgba[..., 3] = out / 255.0
    fg = img[..., [2, 1, 0]].astype(float) / 255.0; fa = a / 255.0
    # premultiplied over
    res_a = fa + rgba[..., 3] * (1 - fa)
    res = fg + rgba[..., :3] * rgba[..., 3:4] * (1 - fa[..., None])
    hi = np.dstack([res, res_a])
    small = hi.reshape(H, K, W, K, 4).mean((1, 3))
    rgbv = np.where(small[..., 3:4] > 0, small[..., :3] / np.maximum(small[..., 3:4], 1e-6), 0)
    a_out = small[..., 3:4]
    rgbv = np.clip(rgbv, 0, 1)
    if name.startswith('Ghost'):
        # the ghost is a pale see-through ant
        rgbv = 0.35 * rgbv + 0.65 * np.array([0.92, 0.96, 1.0])
        a_out = a_out * 0.8
    o = np.dstack([rgbv * 255, a_out * 255]).round().astype(np.uint8)
    return Image.fromarray(o, 'RGBA')
