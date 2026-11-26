import struct,numpy as np
from tex import decode as tdec, encode as tenc
import etc1
CL2TEX={0:7,1:8,2:9,3:5,4:6,5:3,6:1,7:2,8:4,9:0,10:12,11:13,12:10,13:11}
def info(d):
    w,h,fmt=struct.unpack_from('<HHI',d,len(d)-0xc)
    return w,h,CL2TEX[fmt]
def _etc_decode(data,w,h,alpha):
    bs=16 if alpha else 8
    cols=etc1.decode_all_blocks(data)  # (N,4,4,3) at every 8B
    img=np.zeros((h,w,4),np.uint8); img[...,3]=255
    k=0
    for ty in range(0,h,8):
        for tx in range(0,w,8):
            for sub in range(4):
                bx=tx+(sub&1)*4; by=ty+(sub>>1)*4
                off=k*bs
                if alpha:
                    a=struct.unpack_from('<Q',data,off)[0]
                    av=np.array([(a>>(4*i))&0xf for i in range(16)],np.uint8)*17
                    # alpha order: column-major x*4+y
                    img[by:by+4,bx:bx+4,3]=av.reshape(4,4).T
                    blk=cols[(off+8)//8]
                else: blk=cols[off//8]
                img[by:by+4,bx:bx+4,:3]=blk
                k+=1
    return img
def decode(d):
    w,h,fmt=info(d)
    # textures are stored with padded power-of-two dims? use stored w,h rounded to 8
    p2=lambda v: max(8,1<<(v-1).bit_length())
    W=p2(w); H=p2(h)
    if fmt in (12,13): return _etc_decode(d,W,H,fmt==13)[:h,:w]
    return tdec(d,W,H,fmt)[:h,:w]

def _etc_encode(img,alpha,orig=None,origimg=None):
    H,W=img.shape[:2]; out=bytearray(); k=0; bs=16 if alpha else 8
    for ty in range(0,H,8):
        for tx in range(0,W,8):
            for sub in range(4):
                bx=tx+(sub&1)*4; by=ty+(sub>>1)*4
                blk=img[by:by+4,bx:bx+4]
                if orig is not None and (blk==origimg[by:by+4,bx:bx+4]).all():
                    out+=orig[k*bs:(k+1)*bs]; k+=1; continue
                k+=1
                if alpha:
                    a=np.clip((blk[...,3].astype(int)+8)//17,0,15)
                    v=0
                    for i in range(16):
                        x=i//4; y=i%4; v|=int(a[y,x])<<(4*i)
                    out+=struct.pack('<Q',v)
                out+=etc1.encode_block(blk[...,:3])
    return bytes(out)
def encode(orig,img):
    """orig: original bclim bytes; img: RGBA (h,w) -> new bclim bytes same size/format"""
    w,h,fmt=info(orig)
    p2=lambda v: max(8,1<<(v-1).bit_length())
    W=p2(w); H=p2(h)
    full=decode_full(orig); o_full=full.copy()
    full[:h,:w]=img
    if fmt in (12,13): data=_etc_encode(full,fmt==13,orig,o_full)
    else: data=tenc(full,fmt)
    body=len(orig)-0x28
    assert len(data)==body,(len(data),body)
    return data+orig[body:]
def decode_full(d):
    w,h,fmt=info(d)
    p2=lambda v: max(8,1<<(v-1).bit_length())
    W=p2(w); H=p2(h)
    if fmt in (12,13): return _etc_decode(d,W,H,fmt==13)
    return tdec(d,W,H,fmt)
