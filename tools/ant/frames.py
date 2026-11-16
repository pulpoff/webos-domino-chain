# Cuts Domino-Chain's figure.png into its animations, in the order graphicsn.cpp loads them
import os, re
from PIL import Image
SRC = os.environ.get('DC_SRC', os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../dc-src/src'))
FROM_PNG = [i for i in range(66) if i not in (28, 29, 44, 45, 50)]

def anims():
    src = open(SRC + '/domino-chain/figure.cpp').read()
    blk = src[src.index('numFigureAnimationsImages[FigureAnimNothing]'):]
    blk = blk[blk.index('{') + 1:blk.index('};')]
    return [(name.replace('FigureAnim', ''), int(n)) for n, name in re.findall(r'(\d+),?\s*//\s*(\w+)', blk)]

def load(path=SRC + '/images/figure.png'):
    """[(index, name, [(y, frame image)])] for the animations stored in the PNG, plus the PNG"""
    im = Image.open(path).convert('RGBA')
    a = anims(); y = 0; out = []
    for i in FROM_PNG:
        name, n = a[i]; fr = []
        for j in range(n):
            fr.append((y, im.crop((0, y, im.width, y + 75)))); y += 75
        if name == 'Falling':
            y += 150
        out.append((i, name, fr))
    assert y == im.height, (y, im.height)
    return out, im
