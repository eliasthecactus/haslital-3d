import math, os, sys, urllib.request, concurrent.futures as cf
from PIL import Image
D, OUT = sys.argv[1], sys.argv[2]
LON0, LON1, LAT0, LAT1 = 8.174, 8.224, 46.707, 46.737
Z = 16
def px(lon, lat, z):
    n = 2**z * 256
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
X0, Y0 = map(math.floor, px(LON0, LAT1, Z)); X1, Y1 = map(math.ceil, px(LON1, LAT0, Z))
os.makedirs(f'{D}/img16', exist_ok=True)
jobs = [(x, y) for x in range(X0 // 256, (X1 - 1) // 256 + 1) for y in range(Y0 // 256, (Y1 - 1) // 256 + 1)]
def get(j):
    x, y = j; p = f'{D}/img16/{x}_{y}.jpg'
    if os.path.exists(p): return
    u = f'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{Z}/{x}/{y}.jpeg'
    open(p, 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'meiringen-3d-build/1.0'}), timeout=30).read())
with cf.ThreadPoolExecutor(12) as ex: list(ex.map(get, jobs))
tx0, ty0 = X0 // 256, Y0 // 256
mos = Image.new('RGB', ((X1 - 1) // 256 - tx0 + 1) * 256 and (((X1 - 1) // 256 - tx0 + 1) * 256, ((Y1 - 1) // 256 - ty0 + 1) * 256))
for x, y in jobs: mos.paste(Image.open(f'{D}/img16/{x}_{y}.jpg').convert('RGB'), ((x - tx0) * 256, (y - ty0) * 256))
img = mos.crop((X0 - tx0 * 256, Y0 - ty0 * 256, X1 - tx0 * 256, Y1 - ty0 * 256))
img.save(f'{OUT}/detail.jpg', quality=78, optimize=True, progressive=True)
# bounds in z15 px space (divide by 2)
print({'x0': X0 / 2, 'y0': Y0 / 2, 'x1': X1 / 2, 'y1': Y1 / 2, 'size': img.size})
