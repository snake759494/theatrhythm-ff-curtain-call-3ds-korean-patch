# 재빌드

## 준비물

- Python 3.11 이상, `pip install pillow numpy opencv-python`
- Git for Windows의 bash
- [3dstool](https://github.com/dnasdw/3dstool)의 `3dstool.exe` (`tools/3dstool/`에 둡니다)
- 복호화된 원본 일본판 .3ds. MD5가 README 표의 값이어야 합니다.
- 글꼴(`docs/FONT_CREDITS.md`)
- (배포 파일을 만들 때) xdelta3

## 폴더 배치

빌드 스크립트는 저장소를 작업 폴더로 씁니다. 원본 ROM과 나눔스퀘어네오 글꼴은 저장소 바로 위 폴더에 둡니다.

```
상위 폴더/
  Theatrhythm Final Fantasy - Curtain Call (Japan).3ds
  NanumSquareNeo-*.ttf
  저장소/
    tools/py, text, ...
```

번역 폴더 이름은 빌드 코드에서 `tr/`입니다. 처음 한 번 `text/`를 `tr/`로 복사합니다.

## 순서

```bash
cp -r text tr
T=tools/3dstool/3dstool.exe
J="../Theatrhythm Final Fantasy - Curtain Call (Japan).3ds"
# 원본 분해: 헤더·exefs·romfs
$T -xvt017f cci p0.cxi p1.cfa p7.cfa "$J" --header ncsdheader.bin
$T -xvtf cxi p0.cxi --header ncchheader.bin --exh exh.bin --plain plain.bin --logo logo.bin --exefs exefs.bin --romfs romfs.bin
$T -xvtf romfs romfs.bin --romfs-dir romfs
rm p0.cxi romfs.bin
mkdir -p scripts && cp tools/py/* scripts/   # 빌드 코드는 scripts/ 경로를 가정합니다
python scripts/make_jp.py        # 원본에서 일본어 대조표(tr/pNN_jp.json) 생성
mkdir -p _view/img && python scripts/mkindex.py   # 그림 색인
python scripts/build.py          # out_romfs/ 에 바뀐 파일만 생성
bash scripts/make_rom.sh         # ../...(Korean).3ds
```

`build.py`는 다음을 차례로 합니다.
1. `mdt`·`tdt` 문장과 `table/*.csv` 이름 열을 한국어로 교체
2. 본체 공용 글꼴 대체용 `font/cbf_std_replace.bcfnt` 생성
3. 모든 `*.arc.lz`를 풀어 레이아웃 고정 문구 교체, 아카이브 안 `bcfnt`에 필요한 한글 추가, 그림 글자·이름판 교체(병렬 처리)
4. 컬렉카 뒷면 162장과 컬렉션 축소 그림 162장 생성(`ura.py`)

`make_rom.sh`는 원본 romfs 위에 `out_romfs`를 덮어 romfs를 다시 만들고, 암호화하지 않은 CXI와 CCI로 묶습니다.

## 배포 파일 만들기

```bash
xdelta3 -e -0 -s "../Theatrhythm Final Fantasy - Curtain Call (Japan).3ds" "../Theatrhythm Final Fantasy - Curtain Call (Korean).3ds" Theatrhythm_FF_CurtainCall_3DS_KO_v1.0.xdelta
```

결과 ROM의 MD5가 README 표의 값과 같으면 배포판과 같은 결과입니다.

## 화면 확인 도구

`emu.py`, `rpc.py`, `go.py`, `ss.py`, `mashkey.py`는 Azahar를 백그라운드로 띄워 창 메시지로 버튼·터치를 넣고, Azahar 스크립팅 RPC로 화면을 저장하는 검증용 도구입니다. Azahar는 `tools/azahar/`에 둡니다.
