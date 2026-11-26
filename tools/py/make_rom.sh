#!/bin/bash
# out_romfs 를 원본 romfs 위에 덮어써 ROM 재빌드
set -e
cd "$(dirname "$0")/.."
T=tools/3dstool/3dstool.exe
OUTROM="../Theatrhythm Final Fantasy - Curtain Call (Korean).3ds"
rm -rf _rb && mkdir _rb
cp -al romfs _rb/romfs
( cd out_romfs && find . -type f ) | while read f; do rm -f "_rb/romfs/$f"; cp "out_romfs/$f" "_rb/romfs/$f"; done
$T -cvtf romfs _rb/romfs.bin --romfs-dir _rb/romfs >/dev/null
$T -cvtf cxi _rb/p0.cxi --not-encrypt --header ncchheader.bin --exh exh.bin --plain plain.bin --logo logo.bin --exefs out_exefs.bin --romfs _rb/romfs.bin >/dev/null
$T -cvt017f cci _rb/p0.cxi p1.cfa p7.cfa "$OUTROM" --header ncsdheader.bin >/dev/null
rm -rf _rb
ls -la "$OUTROM"
