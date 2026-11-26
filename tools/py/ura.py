"""카드 뒷면(ura_NNN.bclim.lz) 이름·설명문 한글화"""
import os, sys, json, glob
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from arc import lz11_dec, lz11_enc
import bclim

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = os.path.dirname(W)
F_NAME = os.path.join(FD, 'NanumSquareNeo-eHv.ttf')
F_BODY = os.path.join(FD, 'NanumSquareNeo-cBd.ttf')


def text_w(font, s):
    return font.getlength(s)


def wrap(font, text, width):
    lines = []; cur = ''
    for word in text.split(' '):
        t = (cur + ' ' + word) if cur else word
        if text_w(font, t) <= width: cur = t; continue
        if cur: lines.append(cur)
        cur = word
        while text_w(font, cur) > width:  # 긴 단어 강제 분리
            k = len(cur)
            while k > 1 and text_w(font, cur[:k]) > width: k -= 1
            lines.append(cur[:k]); cur = cur[k:]
    if cur: lines.append(cur)
    return lines


def inpaint(a, mask):
    return cv2.inpaint(a[..., :3].copy(), mask.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA)


def text_lines(a):
    L = a.mean(-1); s = a.max(-1) - a.min(-1)
    m = (L < 110) & (s < 30)
    mm = m[:, 15:352]
    tr_ = (mm[:, 1:] & ~mm[:, :-1]).sum(1)
    r = (mm.sum(1) > 6) & (tr_ >= 8)
    runs = []; y = 285
    r[423:] = False
    while y < 450:
        if r[y]:
            y2 = y
            while y2 + 1 < 450 and (r[y2 + 1] or (y2 + 2 < 450 and r[y2 + 2])): y2 += 1
            runs.append((y, y2)); y = y2 + 1
        y += 1
    runs = [q for q in runs if 7 <= q[1] - q[0] + 1 <= 14]
    best = []
    for i in range(len(runs)):
        ch = [runs[i]]
        for q in runs[i + 1:]:
            if 16 <= q[0] - ch[-1][0] <= 21: ch.append(q)
            elif q[0] - ch[-1][0] > 21: break
        if len(ch) > len(best): best = ch
    # 위아래로 이어지는 줄(짧은 마지막 줄 포함): 에지 에너지로 판별
    g = a.mean(-1).astype(np.float32)
    E = (np.abs(cv2.Laplacian(g, cv2.CV_32F))[:, 20:346] > 60).sum(1)
    def probe(y, th):
        if E[y - 2:y + 10].sum() < th: return None
        rows = E[y - 3:y + 12] > 8
        rr = np.nonzero(rows)[0]
        return (y - 3 + rr.min(), y - 3 + rr.max()) if len(rr) else None
    while best and best[-1][0] + 19 < 423:
        q = probe(best[-1][0] + 19, 450)
        if not q: break
        best.append(q)
    while best and best[0][0] - 19 > 290:
        q = probe(best[0][0] - 19, 700)
        if not q: break
        best.insert(0, q)
    return best


def do_body(rgb, text):
    a = rgb.astype(int)
    L = a.mean(-1); s = a.max(-1) - a.min(-1)
    lines0 = text_lines(a)
    nl = len(lines0)
    ty0 = lines0[0][0]; ty1 = lines0[-1][1]
    pitch = (lines0[-1][0] - ty0) / max(nl - 1, 1) if nl > 1 else 18.7
    dark = (L < 110) & (s < 30)
    band = np.zeros(L.shape, bool)
    for y0, y1 in lines0: band[y0 - 2:y1 + 3, 12:356] = True
    xs = np.nonzero((dark & band).sum(0) > 0)[0]; tx0, tx1 = xs.min(), xs.max()
    col = np.median(a[dark & band], 0).astype(int)
    m = band & (L < 175) & (s < 45)
    mk = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & band
    out = inpaint(rgb, mk).astype(np.float32)
    # 잔흔 가리기: 글자 영역에 반투명 흰 막(가장자리 페더)
    A = np.zeros(L.shape, np.float32)
    A[ty0 - 4:ty1 + 5, tx0 - 4:tx1 + 5] = 1
    A = cv2.GaussianBlur(A, (0, 0), 2.5) * 0.5
    out = out * (1 - A[..., None]) + 255 * A[..., None]
    out = np.clip(out, 0, 255).astype(np.uint8)
    width = tx1 - tx0 + 1
    for size in (14, 13, 12, 11):
        font = ImageFont.truetype(F_BODY, size)
        lines = wrap(font, text, width)
        if len(lines) <= nl:
            step = pitch if len(lines) < 2 else min(pitch * 1.3, (lines0[-1][0] - ty0) / (len(lines) - 1))
            step = max(step, pitch); break
        step = (ty1 - ty0 + 1 - size) / (len(lines) - 1) if len(lines) > 1 else pitch
        if step >= size + 3: break
    im = Image.fromarray(out); d = ImageDraw.Draw(im)
    cy0 = (ty0 + lines0[0][1]) / 2
    for i, ln in enumerate(lines):
        cy = cy0 + i * step
        d.text((tx0, cy), ln, font=font, fill=tuple(col), anchor='lm')
    return np.array(im)


ND1, ND2, NR, NM = 3, 7, 3, cv2.INPAINT_NS


def do_name(rgb, name, kind):
    a = rgb.astype(int)
    band = (34, 63)
    tgt = np.array([200, 30, 30]) if kind == 'CHARA' else np.array([80, 30, 110])
    sub = a[band[0]:band[1], :]
    # 왼쪽 시작 부근(x 8~40) 에서 대상 색에 가장 가까운 픽셀을 실제 글자색으로
    d0 = np.abs(sub - tgt).sum(-1)
    reg = d0[:, 6:60]; yy, xx = np.unravel_index(np.argmin(reg), reg.shape)
    col = sub[yy, xx + 6]
    d = np.abs(sub - col).sum(-1)
    near = d < 110
    cs = near.sum(0) > 0
    # 왼쪽부터 연속 열(공백 18px 미만) 범위
    x = 6; last = 6
    while x < 366:
        if cs[x]: last = x
        elif x - last > 26: break
        x += 1
    m = np.zeros(a.shape[:2], bool)
    m[band[0]:band[1], 4:last + 3] = near[:, 4:last + 3]
    ys = np.nonzero(m.any(1))[0]
    gy0, gy1 = ys.min(), ys.max()
    mk = cv2.dilate(m.astype(np.uint8), np.ones((ND1, ND1), np.uint8)).astype(bool)
    br = (a.min(-1) > 215)
    mk |= cv2.dilate(m.astype(np.uint8), np.ones((ND2, ND2), np.uint8)).astype(bool) & br
    mk = cv2.dilate(mk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    out = cv2.inpaint(rgb.copy(), mk.astype(np.uint8) * 255, NR, NM)
    # 로고 시작 위치 = 이름 오른쪽 가용 폭: 원본 이름 끝과 고정 한계 중 큰 값
    maxw = max(last + 2, 230) - 10
    gy0 = 38; h = 19
    size = 26
    font = ImageFont.truetype(F_NAME, size)
    w = text_w(font, name)
    im = Image.new('L', (int(w) + 8, size + 10), 0)
    ImageDraw.Draw(im).text((2, 2), name, font=font, fill=255)
    g = np.array(im); yy = np.nonzero(g.any(1))[0]; xx = np.nonzero(g.any(0))[0]
    g = g[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
    gw = g.shape[1]
    if gw > maxw: g = cv2.resize(g, (maxw, g.shape[0]), interpolation=cv2.INTER_AREA)
    if g.shape[0] != h: g = cv2.resize(g, (g.shape[1], h), interpolation=cv2.INTER_AREA)
    # 흰 테두리(원본처럼 은은하게)
    pad = 2
    G = np.zeros((h + 2 * pad, g.shape[1] + 2 * pad), np.float32); G[pad:-pad, pad:-pad] = g / 255
    edge = cv2.dilate(G, np.ones((3, 3), np.uint8)) * 0.55
    X0 = 10 - pad; Y0 = gy0 - pad
    reg = out[Y0:Y0 + G.shape[0], X0:X0 + G.shape[1]].astype(np.float32)
    e = edge[:reg.shape[0], :reg.shape[1], None]; f = G[:reg.shape[0], :reg.shape[1], None]
    reg = reg * (1 - e) + 255 * e
    reg = reg * (1 - f) + col[None, None, :].astype(np.float32) * f
    out[Y0:Y0 + reg.shape[0], X0:X0 + reg.shape[1]] = np.clip(reg, 0, 255).astype(np.uint8)
    return out


def load():
    tr = {}
    for f in glob.glob(os.path.join(W, 'tr', 'ura_*.json')):
        tr.update({int(k): v for k, v in json.load(open(f, encoding='utf-8')).items()})
    return tr


def render(i, rom, name, kind, body):
    name = name and name.replace('・', '·'); body = body and body.replace('・', '·')
    x = lz11_dec(open(os.path.join(rom, 'common/image/card/ura_%03d.bclim.lz' % i), 'rb').read())
    im = bclim.decode(x)
    rgb = im[..., :3].copy()
    if body: rgb = do_body(rgb, body)
    if name: rgb = do_name(rgb, name, kind)
    im2 = im.copy(); im2[..., :3] = rgb
    return x, im2


def build_all(rom, names, outdir):
    tr = load(); n = 0
    for i in range(1, 163):
        name, kind = names.get(i, (None, None))
        x, im2 = render(i, rom, name, kind, tr.get(i))
        p = os.path.join(outdir, 'common/image/card/ura_%03d.bclim.lz' % i)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(lz11_enc(bclim.encode(x, im2))); n += 1
        # 컬렉션 화면용 축소 썸네일
        tp = 'common/image/card_thumbnail/colleca_back_%03d.bclim.lz' % i
        tx = lz11_dec(open(os.path.join(rom, tp), 'rb').read())
        t = bclim.decode(tx).copy()
        sm = np.array(Image.fromarray(im2[..., :3]).resize((t.shape[1], t.shape[0]), Image.LANCZOS))
        t[..., :3] = sm
        q = os.path.join(outdir, tp); os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, 'wb').write(lz11_enc(bclim.encode(tx, t)))
    return n
