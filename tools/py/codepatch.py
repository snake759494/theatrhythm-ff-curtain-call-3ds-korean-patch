"""code.bin 안의 컬렉션 카드 이름 서식(コレカ#%03d【N】%ls)을 한국어로 바꾼다.
원래 자리에는 글자 수가 모자라므로, 소매판에서 쓰이지 않는 디버그 메뉴 문자열 자리에 새 문자열을 쓰고 포인터만 옮긴다."""
import os, struct, subprocess, shutil, sys
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(W, 'tools', '3dstool', '3dstool.exe')
BASE = 0x100000
PTRS = {'N': 0x449654, 'R': 0x449658, 'P': 0x44965c}
DEBUG_LABEL = 'インターネット対戦＞コレカリザルト'   # 디버그 메뉴 문자열(소매판 미사용) 접두

def cstr(d, s):
    e = s
    while d[e:e + 2] != b'\0\0': e += 2
    return d[s:e].decode('utf-16le'), e + 2

def main(out='out_exefs.bin'):
    tmp = os.path.join(W, '_ex'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    subprocess.run([T, '-xtfu', 'exefs', os.path.join(W, 'exefs.bin'), '--exefs-dir', tmp, '--header', os.path.join(tmp, 'h.bin')], check=True, stdout=subprocess.DEVNULL)
    d = bytearray(open(os.path.join(tmp, 'code.bin'), 'rb').read())
    for k, p in PTRS.items():
        v, = struct.unpack_from('<I', d, p)
        assert cstr(d, v - BASE)[0] == 'コレカ#%03d【' + k + '】%ls', k
    pat = DEBUG_LABEL.encode('utf-16le'); slots = []; i = d.find(pat)
    while i >= 0 and len(slots) < 3:
        s, e = cstr(d, i)
        slots.append((i, e)); i = d.find(pat, e)
    for (s, e), (k, p) in zip(slots, PTRS.items()):
        t = ('콜렉션 카드#%03d【' + k + '】%ls').encode('utf-16le') + b'\0\0'
        assert len(t) <= e - s
        d[s:e] = t + b'\0' * (e - s - len(t))
        struct.pack_into('<I', d, p, BASE + s)
    open(os.path.join(tmp, 'code.bin'), 'wb').write(d)
    subprocess.run([T, '-ctfz', 'exefs', os.path.join(W, out), '--exefs-dir', tmp, '--header', os.path.join(tmp, 'h.bin')], check=True, stdout=subprocess.DEVNULL)
    shutil.rmtree(tmp)
    print('code patched')

if __name__ == '__main__':
    main()
