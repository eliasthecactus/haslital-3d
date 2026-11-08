import json, math, sys
import numpy as np
from PIL import Image
SITE = sys.argv[1]
meta = json.load(open(f'{SITE}/meta.json'))
W, H, X0, Y0, PW, PH, RES = (meta[k] for k in ('W', 'H', 'X0', 'Y0', 'PW', 'PH', 'RES'))
im = np.asarray(Image.open(f'{SITE}/terrain.png').convert('RGB')).astype(np.float32)
HT = (im[..., 0] * 256 + im[..., 1]) / 10 + 400; GH, GW = HT.shape
def local(lon, lat):
    n = 2**15 * 256; x = (lon + 180) / 360 * n; y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return (x - X0 - PW / 2) * RES, (y - Y0 - PH / 2) * RES
def h(x, z):
    gx = min(GW - 1.001, max(0, (x + W / 2) / W * (GW - 1))); gz = min(GH - 1.001, max(0, (z + H / 2) / H * (GH - 1)))
    x0, z0 = int(gx), int(gz); tx, tz = gx - x0, gz - z0
    return HT[z0, x0] * (1 - tx) * (1 - tz) + HT[z0, x0 + 1] * tx * (1 - tz) + HT[z0 + 1, x0] * (1 - tx) * tz + HT[z0 + 1, x0 + 1] * tx * tz
rels = {e['id']: e for e in json.load(open('data/hg.json'))['elements'] if e['type'] == 'relation'}
inside = lambda p: abs(p[0]) < W / 2 - 30 and abs(p[1]) < H / 2 - 30
def chain(ids):
    ways = []
    for rid in ids:
        for m in rels[rid].get('members', []):
            if m['type'] == 'way' and 'geometry' in m:
                ways.append([local(g['lon'], g['lat']) for g in m['geometry']])
    d = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    segs = []
    rest = ways[:]
    while rest:
        cur = rest.pop(0)
        grown = True
        while grown:
            grown = False
            for i, w in enumerate(rest):
                for ww in (w, w[::-1]):
                    if d(cur[-1], ww[0]) < 25: cur = cur + ww[1:]; rest.pop(i); grown = True; break
                    if d(cur[0], ww[-1]) < 25: cur = ww[:-1] + cur; rest.pop(i); grown = True; break
                if grown: break
        segs.append(cur)
    segs.sort(key=lambda s: -sum(d(s[i], s[i + 1]) for i in range(len(s) - 1)))
    # keep main chain plus pieces longer than 300 m (alternatives) ; clip to model
    main = segs[0]; out = [main] + [s for s in segs[1:] if sum(d(s[i], s[i + 1]) for i in range(len(s) - 1)) > 300]
    clipped = []
    for s in out:
        cur = []
        for p in s:
            if inside(p): cur.append(p)
            elif len(cur) > 1: clipped.append(cur); cur = []
            else: cur = []
        if len(cur) > 1: clipped.append(cur)
    clipped.sort(key=lambda s: -len(s))
    return clipped
def simplify(s, tol=6):
    if len(s) < 3: return s
    a, b = np.array(s[0]), np.array(s[-1]); ab = b - a; L = np.hypot(*ab) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(s) - 1):
        p = np.array(s[i]); dd = abs(ab[0] * (a[1] - p[1]) - ab[1] * (a[0] - p[0])) / L
        if dd > dmax: dmax, idx = dd, i
    if dmax > tol: return simplify(s[:idx + 1], tol)[:-1] + simplify(s[idx:], tol)
    return [s[0], s[-1]]
def stats(seg):
    pts = []
    for i in range(len(seg) - 1):
        a, b = seg[i], seg[i + 1]; L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L / 15))
        for k in range(n): pts.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    pts.append(seg[-1])
    el = [h(*p) for p in pts]; dist = [0]
    for i in range(1, len(pts)): dist.append(dist[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    # hysteresis ascent/descent
    up = dn = 0; ref = el[0]
    for e in el:
        if e - ref > 8: up += e - ref; ref = e
        elif ref - e > 8: dn += ref - e; ref = e
    km = dist[-1] / 1000
    th = km / 4.0; tv = up / 300 + dn / 500
    t = max(th, tv) + min(th, tv) / 2
    prof = [round(float(np.interp(dist[-1] * i / 59, dist, el))) for i in range(60)]
    return {'km': round(km, 1), 'up': int(round(up, -1)), 'down': int(round(dn, -1)), 'max': int(round(max(el))), 'min': int(round(min(el))),
            'min_t': int(round(t * 60 / 15) * 15), 'profile': prof}
HIKES = json.load(open('build/hike_defs.json'))
out = {}
for hid, d in HIKES.items():
    segs = chain(d['rels'])
    fx, fz = local(*d['from'])
    m0 = segs[0]
    if math.hypot(m0[-1][0]-fx, m0[-1][1]-fz) < math.hypot(m0[0][0]-fx, m0[0][1]-fz): segs[0] = m0[::-1]
    if d.get('cut_at_max'):
        els = [h(*p) for p in segs[0]]; k = int(np.argmax(els)); segs[0] = segs[0][:k+1]
    st = stats(segs[0])
    if len(segs) > 1 and not d.get('mainonly'): pass
    sym = [rels[r]['tags'].get('osmc:symbol', '') for r in d['rels']]
    diff = 'alpine' if any(s.startswith('blue') for s in sym) else 'mountain' if any(s.startswith('red') for s in sym) else d.get('diff', 'hiking')
    if d.get('diff'): diff = d['diff']
    segs_out = [[[round(x, 1), round(z, 1)] for x, z in simplify(s)] for s in (segs[:1] if d.get('mainonly') else segs)]
    sx, sz = segs[0][0]; ex, ez = segs[0][-1]
    out[hid] = {**st, 'diff': diff, 'segs': segs_out, 'start': [round(sx, 1), round(sz, 1)], 'end': [round(ex, 1), round(ez, 1)],
                'loop': math.hypot(sx - ex, sz - ez) < 150}
    print(hid, round(h(sx,sz)), '->', round(h(ex,ez)), st['km'], 'km', st['up'], 'up', st['down'], 'down', st['max'], 'max', st['min_t'], 'min', diff, len(segs), 'segs', [len(s) for s in segs_out])
json.dump(out, open(f'{SITE}/routes.json', 'w'), separators=(',', ':'))
