"""한글패치 빌드: romfs(원본) -> out_romfs(수정 파일만)"""
import sys, os, json, glob, re, csv, io, struct, hashlib, pickle
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from fmt import *
from arc import *
from bcfnt import parse, glyph_images, build
import numpy as np

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(W, 'romfs')
OUT = os.path.join(W, 'out_romfs')
JP = re.compile('[぀-ヿ一-鿿]')
CSVCOLS = {'AbilityTable.csv': [2], 'BgTable.csv': [22], 'CardTable.csv': [1, 5, 6], 'CharaTable.csv': [1], 'ItemTable.csv': [2],
           'MonsterTable.csv': [2], 'MovieTable.csv': [2], 'MusicTable.csv': [7, 8, 10], 'ProficaTable.csv': [1], 'SeriesTable.csv': [1],
           'SummonTable.csv': [2], 'SupporterTable.csv': [2], 'VehicleTable.csv': [2], 'VersusCpuTable.csv': [1]}


def load_ko():
    jp = {}; ko = {}
    for f in sorted(glob.glob(os.path.join(W, 'tr', 'p*_jp.json'))):
        kf = f.replace('_jp.json', '_ko.json')
        if not os.path.exists(kf):
            print('missing', kf); continue
        a = json.load(open(f, encoding='utf-8')); b = json.load(open(kf, encoding='utf-8'))
        for k in a:
            base, _, idx = k.partition('#')
            i0 = int(idx or 0)
            jp.setdefault(base, {}); ko.setdefault(base, {})
            for i, (s, t) in enumerate(zip(a[k], b[k])):
                jp[base][i0 + i] = s; ko[base][i0 + i] = t
    for fix in sorted(glob.glob(os.path.join(W, 'tr', 'fixes*.json'))):
        for base, m in json.load(open(fix, encoding='utf-8')).items():
            for i, t in m.items(): ko[base][int(i)] = t
    return jp, ko


class HashMap(dict):
    """jp->ko 사전 + 원문을 싣지 않은 레이아웃 문장(원문 SHA-1 -> 한국어)"""
    def __init__(self, base, hashed):
        dict.__init__(self, base); self.hashed = hashed
    @staticmethod
    def _h(k): return hashlib.sha1(k.encode('utf-8')).hexdigest()
    def __contains__(self, k): return dict.__contains__(self, k) or self._h(k) in self.hashed
    def __getitem__(self, k):
        return dict.__getitem__(self, k) if dict.__contains__(self, k) else self.hashed[self._h(k)]
    def __reduce__(self): return (HashMap, (dict(self), self.hashed))


def load_static():
    p = os.path.join(W, 'tr', 'static_layout_ko.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def wfile(rel, data):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)


def clean(s):
    return re.sub('\x02.', '', s)


def write_texts(jp, ko):
    pairs = []
    for f in sorted(glob.glob(R + '/**/*.mdt', recursive=True)):
        rel = os.path.relpath(f, R).replace(os.sep, '/')
        d = open(f, 'rb').read(); s = mdt_read(d)
        if rel in ko:
            s2 = [ko[rel].get(i, x) for i, x in enumerate(s)]
            pairs += list(zip(s, s2)); wfile(rel, mdt_write(d, s2))
    for f in sorted(glob.glob(R + '/**/*.tdt', recursive=True)):
        rel = os.path.relpath(f, R).replace(os.sep, '/')
        d = open(f, 'rb').read(); s = tdt_read(d)
        if rel in ko:
            s2 = [(i, ko[rel].get(n, t)) for n, (i, t) in enumerate(s)]
            pairs += [(a[1], b[1]) for a, b in zip(s, s2)]; wfile(rel, tdt_write(s2))
    for fn, cols in CSVCOLS.items():
        rel = 'table/' + fn
        if rel not in ko: continue
        m = {jp[rel][i]: ko[rel][i] for i in jp[rel]}
        raw = open(os.path.join(R, rel), 'rb').read()
        txt = raw.decode('utf-16')
        lines = txt.split('\n'); out = []
        for ln in lines:
            cr = ln.endswith('\r'); body = ln[:-1] if cr else ln
            r = body.split(',')
            for c in cols:
                if c < len(r) and r[c] in m:
                    pairs.append((r[c], m[r[c]])); r[c] = m[r[c]].replace(',', ' ')
            out.append(','.join(r) + ('\r' if cr else ''))
        bom = raw[:2] == b'\xff\xfe'
        data = '\n'.join(out).encode('utf-16le')
        wfile(rel, (b'\xff\xfe' if bom else b'') + data)
    return pairs


# ---------------- fonts ----------------
def needed_for(cmap_codes, pairs, allko):
    G = set(cmap_codes)
    cjk = sum(1 for c in G if 0x4e00 <= c <= 0x9fff)
    need = set()
    if cjk > 1200:
        need = set(allko)
    for s, t in pairs:
        cs = set(ord(c) for c in clean(s) if ord(c) > 0x7f and c not in '\n')
        if not cs or not cs <= G: continue
        need |= set(ord(c) for c in clean(t) if c not in '\n\r')
    return sorted(c for c in need if c not in G and c >= 0x20)


def pad_col0(img, w):
    """0번 열은 게임이 그리지 않으므로 잉크가 있으면 1px 오른쪽으로 밀고 left-1"""
    if img.shape[1] and img[:, 0, 3].max() > 0:
        img = np.concatenate([np.zeros((img.shape[0], 1, 4), img.dtype), img], 1)
        if img[..., :3].max() == 0 or True:
            img[:, 0, :3] = img[:, 1, :3]; img[:, 0, 3] = 0
        w = (w[0] - 1, w[1] + 1, w[2])
    return img, w


def extend_font(data, name, need, cache):
    from style import ref_stats, make_glyph, pick_ttf
    f = parse(data)
    gl = glyph_images(f); ng = len(gl)
    widths = [f['widths'].get(i, (0, 0, 0)) for i in range(ng)]
    cm = dict(f['cmap_d'])
    key = (name, hashlib.md5(data[:4096]).hexdigest(), f['cellw'], f['cellh'])
    if key not in cache:
        st = ref_stats(f)
        small = min(st['cw'] * 0.86, st['bot'] - st['top'] + 1 - 2 * st['t']) <= 10
        cache[key] = (st, small, {})
    st, small, gc = cache[key]
    ttf = pick_ttf(name)
    for c in need:
        if c not in gc:
            gc[c] = make_glyph(chr(c), f, st, ttf, small)
        img, w = pad_col0(*gc[c])
        cm[c] = len(gl); gl.append(img); widths.append(w)
    cwid = max([f['cellw']] + [g.shape[1] for g in gl])
    sw = 256 if cwid < 60 else 512
    return build(f, gl, widths, cm, cellw=cwid, sheet_w=sw)


def process_arc(args):
    rel, pairs, allko, mapping = args
    from clyt import patch_texts
    src = open(os.path.join(R, rel), 'rb').read()
    d = lz11_dec(src)
    if d[:4] != b'darc': return rel, None, 0
    files = darc_read(d)
    repl = {}; cache = {}; sneed = {}
    for p, i, a, b in files:
        if not p.endswith('.bclyt'): continue
        nd, used = patch_texts(d[a:a + b], mapping)
        if nd is not d[a:a + b] and nd != d[a:a + b]: repl[p] = nd
        for fn, t in used:
            sneed.setdefault(fn, set()).update(ord(c) for c in clean(t) if ord(c) > 0x1f)
    for p, i, a, b in files:
        if not p.endswith('.bcfnt'): continue
        x = d[a:a + b]; f = parse(x)
        if not any(c >= 0x3000 for c in f['cmap_d']): continue
        need = set(needed_for(f['cmap_d'].keys(), pairs, allko))
        need |= set(c for c in sneed.get(p.split('/')[-1], ()) if c >= 0x20 and c not in f['cmap_d'])
        if not need: continue
        repl[p] = extend_font(x, p.split('/')[-1], sorted(need), cache)
    # images
    import bclim, plate
    m_ = re.search(r'(abi|itm)(\d{3})_plate', rel)
    for p, i, a, b in files:
        if not p.endswith('.bclim'): continue
        x = d[a:a + b]; h = hashlib.md5(x).hexdigest()
        if h in IMGNEW: repl[p] = IMGNEW[h]; continue
        key = None
        if m_ and (p.endswith('obj_ability.bclim') or p.endswith('obj_item.bclim')): key = m_.group(1).upper() + m_.group(2)
        ms = re.search(r'plt_info_(smn\d{3})', p)
        if ms: key = ms.group(1)
        if key and key in PLATENAMES:
            try: repl[p] = bclim.encode(x, plate.plate(bclim.decode(x), PLATENAMES[key]))
            except Exception as e: print('plate fail', rel, e)
    if not repl: return rel, None, 0
    nd = darc_replace(d, repl)
    return rel, lz11_enc(nd), len(repl)


IMGNEW = {}; PLATENAMES = {}
def _init(imgnew, names):
    global IMGNEW, PLATENAMES
    IMGNEW = imgnew; PLATENAMES = names


def prep_images(ko, jp):
    import pickle, bclim, imgpatch
    from imgview import get
    S = imgpatch.specs({})
    imgnew = {}
    for i, fn in S.items():
        x = get(i); imgnew[hashlib.md5(x).hexdigest()] = bclim.encode(x, fn(bclim.decode(x)))
    names = {}
    for tbl, col in (('AbilityTable.csv', 1), ('ItemTable.csv', 1)):
        m = {jp['table/' + tbl][k]: ko['table/' + tbl][k] for k in jp['table/' + tbl]}
        for ln in open(os.path.join(R, 'table', tbl), 'rb').read().decode('utf-16').splitlines():
            r = ln.split(',')
            if len(r) > 2 and r[2] in m: names[r[1]] = m[r[2]]
    smn = {'smn901': '다이아몬드 더스트', 'smn902': '심판의 번개', 'smn903': '지옥의 화염', 'smn905': '참철검', 'smn907': '메가플레어', 'smn908': '얼티밋 엔드', 'smn910': '초코보 킥'}
    names.update(smn)
    return imgnew, names


def system_font(allko):
    """cbf_std_replace 에 한글 전체(KS X 1001 2350 + 사용 글자) 추가"""
    from hangul import render_mask
    d = open(os.path.join(R, 'font/cbf_std_replace.bcfnt'), 'rb').read(); f = parse(d)
    gl = glyph_images(f); widths = [f['widths'][i] for i in range(len(gl))]; cm = dict(f['cmap_d'])
    ks = set()
    for b1 in range(0xb0, 0xc9):
        for b2 in range(0xa1, 0xff):
            try: ks.add(ord(bytes([b1, b2]).decode('euc-kr')))
            except Exception: pass
    chars = sorted((ks | set(c for c in allko if 0xac00 <= c <= 0xd7a3 or 0x3131 <= c <= 0x318e)) - set(cm))
    ttf = os.path.join(os.path.dirname(W), 'NanumSquareNeo-bRg.ttf')
    cw, ch, bl = 22, f['cellh'], f['baseline']
    for c in chars:
        a, gw, adv = render_mask(chr(c), ttf, 21, cw, ch, bl)
        im = np.zeros((ch, cw, 4), np.uint8); im[..., :3] = 255
        im[..., 3] = (np.clip(a[:, :cw], 0, 1) * 255).astype(np.uint8)
        im, ww = pad_col0(im, (0, min(gw, cw), min(gw, cw) + 1))
        cm[c] = len(gl); gl.append(im); widths.append(ww)
    wfile('font/cbf_std_replace.bcfnt', build(f, gl, widths, cm, cellw=cw + 1, sheet_w=256, sheet_h=256))
    return len(chars)


def main():
    import shutil
    if os.path.exists(OUT): shutil.rmtree(OUT)
    jp, ko = load_ko()
    pairs = write_texts(jp, ko)
    allko = sorted(set(ord(c) for t in [t for f in ko for t in ko[f].values()] + list(load_static().values()) for c in clean(t) if ord(c) > 0x20 and c not in '\n\r'))
    print('texts written; pairs', len(pairs), 'unique chars', len(allko))
    print('system font +', system_font(allko))
    # dedupe pairs, drop identical
    pairs = list({(s, t) for s, t in pairs if s != t})
    arcs = []
    for f in sorted(glob.glob(R + '/**/*.arc.lz', recursive=True)):
        arcs.append(os.path.relpath(f, R).replace(os.sep, '/'))
    mapping = {}
    for f in jp:
        for i in jp[f]:
            if jp[f][i] != ko[f][i]: mapping.setdefault(jp[f][i], ko[f][i])
    mapping = HashMap(mapping, load_static())
    jobs = [(a, pairs, allko, mapping) for a in arcs]
    n = 0
    imgnew, names = prep_images(ko, jp)
    print('images prepared', len(imgnew), 'plate names', len(names))
    with ProcessPoolExecutor(max_workers=max(2, os.cpu_count() - 2), initializer=_init, initargs=(imgnew, names)) as ex:
        for rel, data, k in ex.map(process_arc, jobs, chunksize=4):
            if data:
                wfile(rel, data); n += 1
    print('arcs modified', n)
    import ura
    t = 'table/CardTable.csv'; m = {jp[t][i]: ko[t][i] for i in jp[t]}; names = {}
    for ln in open(os.path.join(R, t), 'rb').read().decode('utf-16').splitlines():
        r = ln.split(',')
        if len(r) > 2 and r[0].startswith('CARD'): names[int(r[0][4:])] = (m.get(r[1], r[1]), r[2])
    print('card backs', ura.build_all(R, names, OUT))


if __name__ == '__main__':
    main()
