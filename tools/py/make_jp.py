"""원본 romfs에서 일본어 원문을 뽑아 tr/pNN_jp.json(빌드용 대조표)을 다시 만든다.
저장소에는 일본어 원문을 넣지 않으므로 빌드 전에 한 번 실행한다."""
import sys, os, json, glob, re
sys.path.insert(0, os.path.dirname(__file__))
from fmt import mdt_read, tdt_read
from build import CSVCOLS, W, R
NONASCII = re.compile(r'[぀-ヿ一-鿿＀-￯]')

def csv_strings(fn, cols):
    seen = []; s = set()
    for ln in open(os.path.join(R, 'table', fn), 'rb').read().decode('utf-16').split('\n'):
        r = ln.rstrip('\r').split(',')
        for c in cols:
            if c < len(r) and NONASCII.search(r[c]) and r[c] not in s: s.add(r[c]); seen.append(r[c])
    return seen

def source(base):
    p = os.path.join(R, base)
    if base.endswith('.mdt'): return mdt_read(open(p, 'rb').read())
    if base.endswith('.tdt'): return [t for _, t in tdt_read(open(p, 'rb').read())]
    if base.startswith('table/'): return csv_strings(base[6:], CSVCOLS[base[6:]])
    return None

def main():
    cache = {}
    for kf in sorted(glob.glob(os.path.join(W, 'tr', 'p*_ko.json'))):
        ko = json.load(open(kf, encoding='utf-8')); out = {}
        for k, v in ko.items():
            base, _, idx = k.partition('#'); i = int(idx or 0)
            if base not in cache: cache[base] = source(base)
            src = cache[base]
            if src is None: continue
            out[k] = src[i:i + len(v)]
        json.dump(out, open(kf.replace('_ko.json', '_jp.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
