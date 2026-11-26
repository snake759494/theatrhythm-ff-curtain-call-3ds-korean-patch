import struct
def lz11_dec(d):
    assert d[0]==0x11; size=d[1]|d[2]<<8|d[3]<<16; p=4
    if size==0: size=struct.unpack_from('<I',d,4)[0]; p=8
    out=bytearray()
    while len(out)<size:
        f=d[p]; p+=1
        for b in range(8):
            if len(out)>=size: break
            if f&(0x80>>b):
                a=d[p]; t=a>>4
                if t==0:
                    ln=((a&0xf)<<4|d[p+1]>>4)+0x11; disp=((d[p+1]&0xf)<<8|d[p+2])+1; p+=3
                elif t==1:
                    ln=((a&0xf)<<12|d[p+1]<<4|d[p+2]>>4)+0x111; disp=((d[p+2]&0xf)<<8|d[p+3])+1; p+=4
                else:
                    ln=t+1; disp=((a&0xf)<<8|d[p+1])+1; p+=2
                s=len(out)-disp
                for i in range(ln): out.append(out[s+i])
            else:
                out.append(d[p]); p+=1
    return bytes(out)
def lz11_enc(d):
    # greedy with hash chains
    n=len(d); out=bytearray([0x11,n&0xff,(n>>8)&0xff,(n>>16)&0xff])
    if n>=1<<24: out=bytearray([0x11,0,0,0])+struct.pack('<I',n)
    heads={}; p=0
    while p<n:
        fpos=len(out); out.append(0); flag=0
        for b in range(8):
            if p>=n: break
            best=0;bd=0
            if p+3<=n:
                key=d[p:p+3]; lst=heads.get(key)
                if lst:
                    mx=min(0x10110,n-p)
                    for q in reversed(lst[-32:]):
                        if p-q>0x1000: break
                        l=3
                        while l<mx and d[q+l]==d[p+l]: l+=1
                        if l>best: best=l;bd=p-q
                        if l==mx: break
            if best>=3:
                flag|=0x80>>b; disp=bd-1
                if best<=0x10:
                    out+=bytes([((best-1)<<4)|(disp>>8),disp&0xff])
                elif best<=0x110:
                    l=best-0x11; out+=bytes([l>>4,((l&0xf)<<4)|(disp>>8),disp&0xff])
                else:
                    l=best-0x111; out+=bytes([0x10|(l>>12),(l>>4)&0xff,((l&0xf)<<4)|(disp>>8),disp&0xff])
                for i in range(best):
                    if p+i+3<=n: heads.setdefault(d[p+i:p+i+3],[]).append(p+i)
                p+=best
            else:
                if p+3<=n: heads.setdefault(d[p:p+3],[]).append(p)
                out.append(d[p]); p+=1
        out[fpos]=flag
    while len(out)%4: out.append(0)
    return bytes(out)

def darc_read(d):
    assert d[:4]==b'darc'
    hlen,ver,fsz,toff,tlen,doff=struct.unpack_from('<HIIIII',d,6)
    def ent(i):
        no,a,b=struct.unpack_from('<III',d,toff+12*i); return no,a,b
    _,_,cnt=ent(0); nt=toff+12*cnt
    def name(o):
        o=nt+(o&0xffffff); e=o
        while d[e:e+2]!=b'\0\0': e+=2
        return d[o:e].decode('utf-16le')
    files=[]
    def walk(i,end,path):
        while i<end:
            no,a,b=ent(i); nm=name(no)
            if no>>24:
                walk(i+1,b,path+nm+'/' if nm not in('','.') else path); i=b
            else:
                files.append((path+nm,i,a,b)); i+=1
    walk(1,cnt,'')
    return files
def darc_get(d,files):
    return {p:d[a:a+b] for p,i,a,b in files}
def darc_replace(d,repl):
    """rebuild darc replacing file data; keep table, re-layout data"""
    files=darc_read(d)
    hlen,ver,fsz,toff,tlen,doff=struct.unpack_from('<HIIIII',d,6)
    out=bytearray(d[:doff])
    # keep original order by offset
    order=sorted(files,key=lambda x:x[2])
    for p,i,a,b in order:
        data=repl.get(p,d[a:a+b])
        al=0x80 if (p.endswith('.bclim') or p.endswith('.bcfnt') or a%0x80==0) else 4
        while len(out)%al: out.append(0)
        struct.pack_into('<II',out,toff+12*i+4,len(out),len(data))
        out+=data
    struct.pack_into('<I',out,0xc,len(out))
    return bytes(out)
