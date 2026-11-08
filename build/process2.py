import math, json, sys, os, random
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
Image.MAX_IMAGE_PIXELS = None
D, OUT = sys.argv[1], sys.argv[2]
LON0, LON1, LAT0, LAT1 = 8.06, 8.40, 46.555, 46.79
LATC = (LAT0 + LAT1) / 2
NT = 4
def px(lon, lat, z=15):
    n = 2**z * 256
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
X0, Y0 = px(LON0, LAT1); X1, Y1 = px(LON1, LAT0)
X0, Y0, X1, Y1 = math.floor(X0), math.floor(Y0), math.ceil(X1), math.ceil(Y1)
PW, PH = X1 - X0, Y1 - Y0
RES = 156543.03392 / 2**15 * math.cos(math.radians(LATC))
WM, HM = PW * RES, PH * RES
print('px', PW, PH, 'm', round(WM), round(HM))
def local(lon, lat):
    x, y = px(lon, lat); return (x - X0 - PW / 2) * RES, (y - Y0 - PH / 2) * RES
# imagery mosaic
tx0, ty0, tx1, ty1 = X0 // 256, Y0 // 256, (X1 - 1) // 256, (Y1 - 1) // 256
mos = Image.new('RGB', ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
for tx in range(tx0, tx1 + 1):
    for ty in range(ty0, ty1 + 1):
        p = f'{D}/img/{tx}_{ty}.jpg'
        if os.path.exists(p): mos.paste(Image.open(p).convert('RGB'), ((tx - tx0) * 256, (ty - ty0) * 256))
img = mos.crop((X0 - tx0 * 256, Y0 - ty0 * 256, X0 - tx0 * 256 + PW, Y0 - ty0 * 256 + PH)); del mos
sc = 4096 / max(PW, PH); TW, TH = round(PW * sc), round(PH * sc)
base = img.resize((TW, TH), Image.LANCZOS); base.save(f'{OUT}/ortho.jpg', quality=78, optimize=True, progressive=True)
# terrain grid
SP = 34.0
GW = round(WM / SP) + 1; GH = round(HM / SP) + 1
dx0, dy0 = X0 // 4 // 256, Y0 // 4 // 256; dx1, dy1 = (X1 // 4) // 256, (Y1 // 4) // 256
dem = np.zeros(((dy1 - dy0 + 1) * 256, (dx1 - dx0 + 1) * 256), np.float32)
for tx in range(dx0, dx1 + 1):
    for ty in range(dy0, dy1 + 1):
        a = np.asarray(Image.open(f'{D}/dem/{tx}_{ty}.png').convert('RGB')).astype(np.float32)
        dem[(ty - dy0) * 256:(ty - dy0 + 1) * 256, (tx - dx0) * 256:(tx - dx0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
def sample(arr, fx, fy):
    x0 = np.clip(np.floor(fx).astype(int), 0, arr.shape[1] - 2); y0 = np.clip(np.floor(fy).astype(int), 0, arr.shape[0] - 2)
    tx = np.clip(fx - x0, 0, 1); ty = np.clip(fy - y0, 0, 1)
    return arr[y0, x0] * (1 - tx) * (1 - ty) + arr[y0, x0 + 1] * tx * (1 - ty) + arr[y0 + 1, x0] * (1 - tx) * ty + arr[y0 + 1, x0 + 1] * tx * ty
GX, GY = np.meshgrid(np.linspace(0, PW, GW), np.linspace(0, PH, GH))
H = sample(dem, (X0 + GX) / 4 - dx0 * 256 - 0.5, (Y0 + GY) / 4 - dy0 * 256 - 0.5)
k = np.array([.25, .5, .25], np.float32)
Hp = np.pad(H, 1, mode='edge'); H = (Hp[:, :-2] * k[0] + Hp[:, 1:-1] * k[1] + Hp[:, 2:] * k[2])[1:-1, :]
Hp = np.pad(H, ((1, 1), (0, 0)), mode='edge'); H = Hp[:-2] * k[0] + Hp[1:-1] * k[1] + Hp[2:] * k[2]
q = np.clip((H - 400) * 10, 0, 65535).astype(np.uint32)
rgb = np.stack([(q >> 8).astype(np.uint8), (q & 255).astype(np.uint8), np.zeros_like(q, np.uint8)], -1)
Image.fromarray(rgb, 'RGB').save(f'{OUT}/terrain.png', optimize=True)
print('grid', GW, GH, H.min(), H.max())
def height_at(x, z):
    return float(sample(H, np.array([(x + WM / 2) / WM * (GW - 1)]), np.array([(z + HM / 2) / HM * (GH - 1)]))[0])
# tiles aligned to grid columns
cb = [round(i * (GW - 1) / NT) for i in range(NT + 1)]; rb = [round(j * (GH - 1) / NT) for j in range(NT + 1)]
tiles = []
for j in range(NT):
    for i in range(NT):
        xa, xb = -WM / 2 + cb[i] / (GW - 1) * WM, -WM / 2 + cb[i + 1] / (GW - 1) * WM
        za, zb = -HM / 2 + rb[j] / (GH - 1) * HM, -HM / 2 + rb[j + 1] / (GH - 1) * HM
        pa, pb = (xa + WM / 2) / RES, (xb + WM / 2) / RES; qa, qb = (za + HM / 2) / RES, (zb + HM / 2) / RES
        crop = img.crop((math.floor(pa), math.floor(qa), math.ceil(pb), math.ceil(qb)))
        if max(crop.size) > 2048: crop = crop.resize((min(2048, crop.size[0]), min(2048, crop.size[1])), Image.LANCZOS)
        crop.save(f'{OUT}/tile-{i}-{j}.jpg', quality=72, optimize=True, progressive=True)
        tiles.append({'i': i, 'j': j, 'c': [cb[i], cb[i + 1]], 'r': [rb[j], rb[j + 1]],
                      'rect': [round(math.floor(pa) * RES - WM / 2, 2), round(math.floor(qa) * RES - HM / 2, 2), round(math.ceil(pb) * RES - WM / 2, 2), round(math.ceil(qb) * RES - HM / 2, 2)]})
# OSM
osm = json.load(open(f'{D}/osm.json'))['elements']
def num(s):
    try: return float(str(s).replace('m', '').replace("'", '').split(';')[0].strip())
    except: return None
bld = []; bmask = Image.new('L', (TW, TH), 0); bd = ImageDraw.Draw(bmask); aerial = []; fun = {}
for e in osm:
    t = e.get('tags', {}); g = e.get('geometry')
    if not g: continue
    pts = [local(p['lon'], p['lat']) for p in g]
    if 'building' in t:
        if pts[0] == pts[-1]: pts = pts[:-1]
        if len(pts) < 3 or any(abs(x) > WM / 2 - 5 or abs(z) > HM / 2 - 5 for x, z in pts): continue
        b = t['building']; h = num(t.get('height'))
        if h is None and num(t.get('building:levels')): h = num(t['building:levels']) * 3 + 2.5
        if h is None: h = {'church': 16, 'chapel': 8, 'garage': 3.5, 'garages': 3.5, 'shed': 3.5, 'hut': 4, 'roof': 4, 'cabin': 4, 'barn': 7, 'farm_auxiliary': 7, 'hangar': 9, 'industrial': 9, 'hotel': 13, 'apartments': 12, 'school': 11, 'commercial': 10, 'retail': 7}.get(b, 7.5)
        h = max(2.5, min(h, 60)); flat = []
        for x, z in pts: flat += [round(x * 2), round(z * 2)]
        bld += [len(pts), round(h * 2)] + flat
        bd.polygon([((x + WM / 2) / WM * TW, (z + HM / 2) / HM * TH) for x, z in pts], fill=255)
    elif t.get('railway') == 'funicular':
        n = t.get('name')
        if n: fun.setdefault(n, []).extend(pts)
    elif t.get('aerialway') in ('gondola', 'cable_car', 'chair_lift'):
        aerial.append({'k': t['aerialway'], 'n': t.get('name', ''), 'p': [[round(x, 1), round(z, 1)] for x, z in pts]})
for n, pts in fun.items():
    if n == 'Chapfbahn' or len(pts) < 2: continue
    a = max(((p, q) for p in pts for q in pts), key=lambda pq: (pq[0][0] - pq[1][0])**2 + (pq[0][1] - pq[1][1])**2)
    dx, dz = a[1][0] - a[0][0], a[1][1] - a[0][1]
    u = sorted(set((round(x, 1), round(z, 1)) for x, z in pts), key=lambda p: (p[0] - a[0][0]) * dx + (p[1] - a[0][1]) * dz)
    aerial.append({'k': 'funicular', 'n': n, 'p': [list(p) for p in u]})
np.array(bld, '<i2').tofile(f'{OUT}/buildings.bin')
print('buildings bytes', len(bld) * 2)
# trees
a = np.asarray(base.resize((TW // 2, TH // 2), Image.BILINEAR)).astype(np.float32)
r, g, b = a[..., 0], a[..., 1], a[..., 2]; lum = 0.3 * r + 0.59 * g + 0.11 * b
forest = ((g >= r + 1) & (lum < 80) & (lum > 22) & (g >= b + 3)).astype(np.float32)
fm = np.asarray(Image.fromarray((forest * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(2))).astype(np.float32) / 255
bm = np.asarray(bmask.resize((TW // 2, TH // 2)).filter(ImageFilter.MaxFilter(3))) > 0
random.seed(7); trees = []; S = 22.0
for z in np.arange(-HM / 2 + 5, HM / 2 - 5, S):
    for x in np.arange(-WM / 2 + 5, WM / 2 - 5, S):
        jx = x + random.uniform(-S * .45, S * .45); jz = z + random.uniform(-S * .45, S * .45)
        u = int((jx + WM / 2) / WM * (TW // 2 - 1)); v = int((jz + HM / 2) / HM * (TH // 2 - 1)); p = fm[v, u]
        if bm[v, u] or p < 0.55 or random.random() > (p - 0.45) * 1.6: continue
        hh = height_at(jx, jz)
        if hh > 2050: continue
        sl = max(abs(height_at(jx + 10, jz) - height_at(jx - 10, jz)), abs(height_at(jx, jz + 10) - height_at(jx, jz - 10))) / 20
        if sl > 1.25: continue
        trees += [round(jx * 2), round(jz * 2), random.randint(0, 255)]
np.array(trees, '<i2').tofile(f'{OUT}/trees.bin'); print('trees', len(trees) // 3)
peaks = []
for e in osm:
    t = e.get('tags', {})
    if t.get('natural') == 'peak' and num(t.get('ele')) and num(t['ele']) >= 2000:
        x, z = local(e['lon'], e['lat'])
        if abs(x) < WM / 2 - 300 and abs(z) < HM / 2 - 300: peaks.append({'n': t['name'], 'e': round(num(t['ele'])), 'x': round(x), 'z': round(z)})
json.dump({'W': WM, 'H': HM, 'GW': GW, 'GH': GH, 'NT': NT, 'X0': X0, 'Y0': Y0, 'PW': PW, 'PH': PH, 'RES': RES, 'tiles': tiles, 'aerial': aerial, 'peaks': peaks},
          open(f'{OUT}/meta.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('ok', len(aerial), 'aerial', len(peaks), 'peaks')
