import struct
def sections(d):
    hs,=struct.unpack_from('<H',d,6); n,=struct.unpack_from('<I',d,0x10)
    p=hs; out=[]
    for i in range(n):
        m=d[p:p+4]; sz,=struct.unpack_from('<I',d,p+4); out.append((m,p,sz)); p+=sz
    return out
def info(d):
    fonts=[];tbs=[]
    for m,p,sz in sections(d):
        if m==b'fnl1':
            n,=struct.unpack_from('<I',d,p+8)
            for i in range(n):
                o,=struct.unpack_from('<I',d,p+12+4*i); s=p+12+o
                fonts.append(d[s:d.index(b'\0',s)].decode())
        if m==b'txt1':
            name=d[p+0xc:p+0x24].split(b'\0')[0].decode()
            mx,ln,mat,fi=struct.unpack_from('<HHHH',d,p+0x4c)
            to,=struct.unpack_from('<I',d,p+0x58)
            txt=d[p+to:p+to+ln].decode('utf-16le') if ln else ''
            sx,sy=struct.unpack_from('<ff',d,p+0x64)
            tbs.append(dict(name=name,font=fi,max=mx,text=txt,off=p,size=(sx,sy)))
    return fonts,tbs

def patch_texts(d, mapping):
    """replace static txt1 texts via mapping(jp->ko). returns (newdata, [(fontname, kotext)])"""
    fonts,_=info(d)
    hs,=struct.unpack_from('<H',d,6)
    out=bytearray(d[:hs]); used=[]; changed=False
    for m,p,sz in sections(d):
        seg=bytearray(d[p:p+sz])
        if m==b'txt1':
            mx,ln,mat,fi=struct.unpack_from('<HHHH',seg,0x4c)
            to,=struct.unpack_from('<I',seg,0x0c+0x4c)
            txt=bytes(seg[to:to+ln]).decode('utf-16le','replace')
            s=txt.split('\0')[0]
            if s in mapping and mapping[s]!=s:
                k=mapping[s]
                tb=k.encode('utf-16le')+b'\0\0'
                newmax=max(mx,len(tb))
                body=bytes(seg[:to])+tb+b'\0'*(newmax-len(tb))
                while len(body)%4: body+=b'\0'
                seg=bytearray(body)
                struct.pack_into('<HH',seg,0x4c,newmax,len(tb))
                struct.pack_into('<I',seg,4,len(seg))
                changed=True
                if fi<len(fonts): used.append((fonts[fi],k))
            elif fi<len(fonts) and s:
                used.append((fonts[fi],s))
        out+=seg
    struct.pack_into('<I',out,0xc,len(out))
    return (bytes(out) if changed else d), used
