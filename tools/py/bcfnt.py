import struct
def parse(d):
    assert d[:4]==b'CFNT'
    hs,=struct.unpack_from('<H',d,6); nblk,=struct.unpack_from('<I',d,0x10)
    finf=0x14
    f={}
    (f['ftype'],f['linefeed'],f['altidx'],f['dleft'],f['dglyph'],f['dchar'],f['enc'],tglp,cwdh,cmap,
     f['height'],f['width'],f['ascent'])=struct.unpack_from('<BbHbBBBIIIBBB',d,finf+8)
    f['tglp']=tglp; f['cwdh']=cwdh; f['cmap']=cmap
    t=tglp-8
    (cw,ch,bl,mw,ssz,ns,fmt,cpr,rows,sw,sh,sdo)=struct.unpack_from('<BBBBIHHHHHHI',d,t+8)
    f.update(cellw=cw,cellh=ch,baseline=bl,maxw=mw,sheetsize=ssz,nsheets=ns,fmt=fmt,cols=cpr,rows=rows,sw=sw,sh=sh)
    f['sheets']=[d[sdo+i*ssz:sdo+(i+1)*ssz] for i in range(ns)]
    # cmap
    cm={}
    o=cmap
    while o:
        b=o-8
        cs,ce,meth,_,nxt=struct.unpack_from('<HHHHI',d,b+8)
        p=b+0x14
        if meth==0:
            off,=struct.unpack_from('<H',d,p)
            for c in range(cs,ce+1): cm[c]=off+c-cs
        elif meth==1:
            for c in range(cs,ce+1):
                g,=struct.unpack_from('<H',d,p+2*(c-cs))
                if g!=0xffff: cm[c]=g
        else:
            n,=struct.unpack_from('<H',d,p)
            for i in range(n):
                c,g=struct.unpack_from('<HH',d,p+2+4*i); cm[c]=g
        o=nxt
    f['cmap_d']=cm
    wd={}
    o=cwdh
    while o:
        b=o-8
        s,e,nxt=struct.unpack_from('<HHI',d,b+8)
        for i in range(s,e+1): wd[i]=struct.unpack_from('<bBB',d,b+0x10+3*(i-s))
        o=nxt
    f['widths']=wd
    return f

import numpy as np
def glyph_images(f):
    """list of RGBA cell images (ch,cw,4) by glyph index"""
    from tex import decode
    cw,ch=f['cellw'],f['cellh']; cols,rows=f['cols'],f['rows']
    out=[]
    for s in f['sheets']:
        im=decode(s,f['sw'],f['sh'],f['fmt'])
        for r in range(rows):
            for c in range(cols):
                x=c*(cw+1); y=r*(ch+1)
                out.append(im[y:y+ch,x:x+cw].copy())
    ng=max(f['widths'])+1
    return out[:ng]

def build(f,glyphs,widths,cmap,cellw=None,cellh=None,baseline=None,sheet_w=None,sheet_h=None):
    """glyphs: list of RGBA arrays (any size <= cell), widths list of (left,gw,cw), cmap dict code->idx"""
    from tex import encode,BPP
    fmt=f['fmt']
    cw=cellw or f['cellw']; ch=cellh or f['cellh']; bl=baseline if baseline is not None else f['baseline']
    n=len(glyphs)
    sw=sheet_w or 256
    cols=sw//(cw+1)
    if sheet_h is None:
        # choose sheet height: power of two, up to 512 to keep sheets few
        need_rows=-(-n//cols)
        sh=8
        while sh<256 and (sh//(ch+1))<need_rows: sh*=2
        sh=max(sh,32)
    else: sh=sheet_h
    rows=sh//(ch+1); per=cols*rows
    ns=-(-n//per)
    ssz=sw*sh*BPP[fmt]//8
    sheets=[]
    for s in range(ns):
        im=np.zeros((sh,sw,4),np.uint8)
        if fmt in (9,5,4,0): im[...,:3]=0
        else: im[...,:3]=255
        for k in range(per):
            gi=s*per+k
            if gi>=n: break
            g=glyphs[gi]; r,c=divmod(k,cols)
            x=c*(cw+1); y=r*(ch+1)
            gh,gw=g.shape[:2]
            im[y:y+min(gh,ch),x:x+min(gw,cw)]=g[:ch,:cw]
        sheets.append(encode(im,fmt))
    maxw=max(w[2] for w in widths) if widths else cw
    # assemble
    out=bytearray(b'CFNT'+struct.pack('<HHIII',0xFEFF,0x14,0x03000000,0,4))
    finf=len(out)
    out+=b'FINF'+struct.pack('<I',0x20)+bytes(0x18)
    tglp=len(out)
    hdr=struct.pack('<BBBBIHHHHHHI',cw,ch,bl,min(255,max(maxw,cw)),ssz,ns,fmt,cols,rows,sw,sh,0)
    out+=b'TGLP'+struct.pack('<I',0)+hdr
    while len(out)%0x80: out.append(0)
    sdo=len(out)
    for s in sheets: out+=s
    struct.pack_into('<I',out,tglp+4,len(out)-tglp)
    struct.pack_into('<I',out,tglp+8+0x14,sdo)
    cwdh=len(out)
    body=struct.pack('<HHI',0,n-1,0)+b''.join(struct.pack('<bBB',*w) for w in widths)
    out+=b'CWDH'+struct.pack('<I',0)+body
    while len(out)%4: out.append(0)
    struct.pack_into('<I',out,cwdh+4,len(out)-cwdh)
    cmp=len(out)
    codes=sorted(cmap)
    body=struct.pack('<HHHHI',0,0xffff,2,0,0)+struct.pack('<H',len(codes))+b''.join(struct.pack('<HH',c,cmap[c]) for c in codes)
    out+=b'CMAP'+struct.pack('<I',0)+body
    while len(out)%4: out.append(0)
    struct.pack_into('<I',out,cmp+4,len(out)-cmp)
    struct.pack_into('<BbHbBBBIIIBBB',out,finf+8,f['ftype'],f['linefeed'],f['altidx'],f['dleft'],f['dglyph'],f['dchar'],f['enc'],
                     tglp+8,cwdh+8,cmp+8,f['height'],f['width'],f['ascent'])
    struct.pack_into('<I',out,0xc,len(out))
    return bytes(out)
