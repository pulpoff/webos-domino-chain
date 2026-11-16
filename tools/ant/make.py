#!/usr/bin/env python3
# Writes art/figure.png: Domino-Chain's figure animations (dc-src/src/images/figure.png, one
# 75-pixel frame below the other) with every frame redrawn as the ant (render.py). Needs Python 3
# with numpy, scipy, Pillow and pycairo. package.sh ships the result in place of the stick figure.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frames import load
from render import render

def main(out):
    rows, im = load()
    im = im.copy()
    n = 0
    for i, name, fr in rows:
        for j, (y, f) in enumerate(fr):
            g = render(f, name, j)
            im.paste(g, (0, y))      # replaces the frame, transparency included
            n += 1
    im.save(out, optimize=True)
    print('%d frames -> %s' % (n, out))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '../../art/figure.png'))
