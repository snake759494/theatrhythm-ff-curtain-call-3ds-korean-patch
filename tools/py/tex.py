import numpy as np
BPP={0:32,1:24,2:16,3:16,4:16,5:16,6:16,7:8,8:8,9:8,10:4,11:4}
def _morton():
    m=np.zeros(64,dtype=np.int32)
    for i in range(64):
        x=y=0
        for b in range(3):
            x|=((i>>(2*b))&1)<<b; y|=((i>>(2*b+1))&1)<<b
        m[i]=y*8+x
    return m
MORTON=_morton()
def _pix_order(w,h):
    # returns array idx[k] = linear (y*w+x) for k-th pixel in stream
    tiles=[]
    for ty in range(0,h,8):
        for tx in range(0,w,8):
            for i in range(64):
                p=MORTON[i]; x=tx+p%8; y=ty+p//8
                tiles.append(y*w+x)
    return np.array(tiles)
def decode(data,w,h,fmt):
    """returns RGBA uint8 array h,w,4 (top row first)"""
    n=w*h; order=_pix_order(w,h)
    b=np.frombuffer(data,dtype=np.uint8)
    out=np.zeros((n,4),dtype=np.uint8)
    if fmt==11:
        v=b[:n//2]; a=np.empty(n,np.uint8); a[0::2]=v&0xf; a[1::2]=v>>4; a=a*17
        px=np.stack([np.full(n,255,np.uint8)]*3+[a],1)
    elif fmt==10:
        v=b[:n//2]; l=np.empty(n,np.uint8); l[0::2]=v&0xf; l[1::2]=v>>4; l=l*17
        px=np.stack([l,l,l,np.full(n,255,np.uint8)],1)
    elif fmt==8:
        a=b[:n]; px=np.stack([np.full(n,255,np.uint8)]*3+[a],1)
    elif fmt==7:
        l=b[:n]; px=np.stack([l,l,l,np.full(n,255,np.uint8)],1)
    elif fmt==9:
        v=b[:n]; l=(v>>4)*17; a=(v&0xf)*17; px=np.stack([l,l,l,a],1)
    elif fmt==5:
        v=b[:2*n].reshape(-1,2); a=v[:,0]; l=v[:,1]; px=np.stack([l,l,l,a],1)
    elif fmt==4:
        v=b[:2*n].view('<u2')[:n].astype(np.uint16)
        px=np.stack([((v>>12)&15)*17,((v>>8)&15)*17,((v>>4)&15)*17,(v&15)*17],1).astype(np.uint8)
    elif fmt==0:
        v=b[:4*n].reshape(-1,4); px=v[:,::-1].copy()  # ABGR -> RGBA
    elif fmt==2:
        v=b[:2*n].view('<u2')[:n].astype(np.uint32)
        px=np.stack([((v>>11)&31)*255//31,((v>>6)&31)*255//31,((v>>1)&31)*255//31,(v&1)*255],1).astype(np.uint8)
    elif fmt==3:
        v=b[:2*n].view('<u2')[:n].astype(np.uint32)
        px=np.stack([((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31,np.full(n,255)],1).astype(np.uint8)
    elif fmt==1:
        v=b[:3*n].reshape(-1,3); px=np.concatenate([v[:,::-1],np.full((n,1),255,np.uint8)],1)
    else: raise ValueError(fmt)
    out[order]=px
    return out.reshape(h,w,4)
def encode(img,fmt):
    h,w,_=img.shape; order=_pix_order(w,h)
    px=img.reshape(-1,4)[order].astype(np.int32)
    r,g,b_,a=px[:,0],px[:,1],px[:,2],px[:,3]
    l=(r*299+g*587+b_*114+500)//1000
    q4=lambda x:np.clip((x+8)//17,0,15)
    if fmt==11:
        v=q4(a); return (v[0::2]|(v[1::2]<<4)).astype(np.uint8).tobytes()
    if fmt==10:
        v=q4(l); return (v[0::2]|(v[1::2]<<4)).astype(np.uint8).tobytes()
    if fmt==8: return a.astype(np.uint8).tobytes()
    if fmt==7: return l.astype(np.uint8).tobytes()
    if fmt==9: return ((q4(l)<<4)|q4(a)).astype(np.uint8).tobytes()
    if fmt==5: return np.stack([a,l],1).astype(np.uint8).tobytes()
    if fmt==4: return ((q4(r)<<12)|(q4(g)<<8)|(q4(b_)<<4)|q4(a)).astype('<u2').tobytes()
    if fmt==0: return np.stack([a,b_,g,r],1).astype(np.uint8).tobytes()
    if fmt==1: return np.stack([b_,g,r],1).astype(np.uint8).tobytes()
    if fmt==3: return (((r*31+127)//255<<11)|((g*63+127)//255<<5)|((b_*31+127)//255)).astype('<u2').tobytes()
    if fmt==2: return (((r*31+127)//255<<11)|((g*31+127)//255<<6)|((b_*31+127)//255<<1)|(a>127)).astype('<u2').tobytes()
    raise ValueError(fmt)
