import struct
K=0xFF73
def mdt_read(d):
    assert d[:4]==b'MSGD'
    n,=struct.unpack_from('<I',d,0xc); toff,doff=struct.unpack_from('<II',d,0x10)
    offs=struct.unpack_from('<%dI'%n,d,toff)
    out=[]
    for o in offs:
        p=doff+o; s=[]
        while True:
            c=struct.unpack_from('<H',d,p)[0]^K; p+=2
            if c==0: break
            s.append(chr(c))
        out.append(''.join(s))
    return out
def mdt_write(orig,strs):
    n,=struct.unpack_from('<I',orig,0xc); toff,doff=struct.unpack_from('<II',orig,0x10)
    assert n==len(strs)
    body=[];offs=[];pos=0
    for s in strs:
        offs.append(pos); u=[ord(c)^K for c in s]+[K]; body+=u; pos+=2*len(u)
    hdr=bytearray(orig[:doff])
    struct.pack_into('<%dI'%n,hdr,toff,*offs)
    out=bytes(hdr)+struct.pack('<%dH'%len(body),*body)
    return out
def tdt_read(d):
    n,h=struct.unpack_from('<II',d,0); p=h; out=[]
    for i in range(n):
        sz,io,to=struct.unpack_from('<III',d,p)
        e=d[p:p+sz]; ident=e[io:e.index(b'\0',io)].decode()
        txt=e[to:].decode('utf-16le').rstrip('\0')
        out.append((ident,txt)); p+=sz
    assert p==len(d),(p,len(d))
    return out
def tdt_write(items):
    b=bytearray(struct.pack('<II',len(items),8))
    for ident,txt in items:
        idb=ident.encode()+b'\0'; tb=txt.encode('utf-16le')+b'\0\0'
        b+=struct.pack('<III',12+len(idb)+len(tb),12,12+len(idb))+idb+tb
    return bytes(b)
