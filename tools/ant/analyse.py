# Finds the head, the neck and the hip of Domino-Chain's stick figure in a 130x75 frame
import numpy as np
from collections import deque
from scipy import ndimage as ndi

def masks(f):
    a = np.array(f).astype(float)
    al = a[..., 3]; lum = a[..., :3].mean(-1)
    return (al > 128) & (lum < 80), al

def head(core):
    """(x, y, radius) of the head: the topmost of the thick round blobs"""
    if not core.any():
        return None
    # a head drawn as a ring counts as solid
    dt = ndi.distance_transform_edt(ndi.binary_fill_holes(core))
    m = dt.max()
    cand = dt >= max(2.8, 0.72 * m)
    lab, n = ndi.label(cand)
    best = None
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k)
        top = ys.min()
        # a blob counts as a head only when it is about as thick as the thickest one
        pk = dt[lab == k].max()
        key = (top - 4 * (pk >= 0.85 * m), )
        if best is None or key < best[0]:
            i = np.argmax(np.where(lab == k, dt, -1)); y, x = np.unravel_index(i, dt.shape)
            best = (key, (x, y, dt[y, x]))
    return best[1]

def thin(m):
    """Zhang-Suen thinning"""
    m = np.pad(m.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = [np.roll(np.roll(m, -dy, 0), -dx, 1) for dy, dx in
                 ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))]
            p2, p3, p4, p5, p6, p7, p8, p9 = P
            B = sum(P)
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(int) for i in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            d = (m == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if d.any():
                m[d] = 0; changed = True
        if not changed:
            return m[1:-1, 1:-1].astype(bool)

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

def body(core, hd):
    """neck and hip (x, y) from the skeleton: the hip is where the second leg leaves the path from
    the head to the farthest foot"""
    hx, hy, hr = hd
    sk = thin(core)
    pts = set(zip(*np.nonzero(sk)))
    if not pts:
        return None
    # start at the skeleton point nearest to the head centre
    s = min(pts, key=lambda p: (p[0] - hy) ** 2 + (p[1] - hx) ** 2)
    dist = {s: 0.0}; par = {s: None}; q = deque([s])
    while q:
        p = q.popleft()
        for dy, dx in N8:
            n = (p[0] + dy, p[1] + dx)
            if n in pts and n not in dist:
                dist[n] = dist[p] + (1.414 if dy and dx else 1.0); par[n] = p; q.append(n)
    ends = [p for p in dist if sum((p[0] + dy, p[1] + dx) in pts for dy, dx in N8) == 1]
    if not ends:
        return None
    # the foot: farthest below and away
    A = max(ends, key=lambda p: dist[p] + 0.3 * (p[0] - hy))
    path = []; p = A
    while p is not None:
        path.append(p); p = par[p]
    path.reverse()
    onpath = {p: i for i, p in enumerate(path)}
    L = dist[A]
    hip = None
    for e in ends:
        if e == A:
            continue
        p = e
        while p not in onpath:
            p = par[p]
        branch = dist[e] - dist[p]
        if branch >= 8 and 0.3 * L <= dist[p] <= 0.8 * L and dist[p] > hr + 6:
            if hip is None or dist[p] > dist[hip]:
                hip = p
    if hip is None:
        t = max(hr + 8, 0.5 * L)
        hip = min(path, key=lambda p: abs(dist[p] - t))
    tn = hr + 1.5
    neck = min(path, key=lambda p: abs(dist[p] - tn))
    return (neck[1], neck[0]), (hip[1], hip[0]), sk, (A[1], A[0])
