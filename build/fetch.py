import math, os, sys, urllib.request, concurrent.futures as cf
D = sys.argv[1]
LON0, LON1, LAT0, LAT1 = 8.06, 8.40, 46.555, 46.79
def tile(lon, lat, z):
    n = 2**z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y
def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    req = urllib.request.Request(url, headers={'User-Agent': 'meiringen-3d-build/1.0'})
    for i in range(4):
        try:
            data = urllib.request.urlopen(req, timeout=30).read(); open(path, 'wb').write(data); return
        except Exception as e:
            err = e
    print('fail', url, err)
jobs = []
for z, kind in ((15, 'img'), (13, 'dem')):
    x0, y0 = tile(LON0, LAT1, z); x1, y1 = tile(LON1, LAT0, z)
    os.makedirs(f'{D}/{kind}', exist_ok=True)
    for x in range(int(x0), int(x1) + 1):
        for y in range(int(y0), int(y1) + 1):
            if kind == 'img':
                u = f'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg'
                jobs.append((u, f'{D}/img/{x}_{y}.jpg'))
            else:
                u = f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
                jobs.append((u, f'{D}/dem/{x}_{y}.png'))
print(len(jobs), 'tiles')
with cf.ThreadPoolExecutor(12) as ex: list(ex.map(lambda j: get(*j), jobs))
print('done')
