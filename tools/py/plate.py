import numpy as np
from PIL import Image,ImageDraw,ImageFont
import os; ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
def lum(c): return c[...,0]*0.299+c[...,1]*0.587+c[...,2]*0.114
_F={}
def F(ttf,s):
    if (ttf,s) not in _F: _F[(ttf,s)]=ImageFont.truetype(ttf,s)
    return _F[(ttf,s)]
def text_mask(text,ttf,ink_h,maxw,S=4,cond_min=0.6):
    """render text with Hangul ink height = ink_h px; condense to maxw"""
    p=int(ink_h*1.3)
    for _ in range(5):
        bb=F(ttf,p*S).getbbox('한'); h=(bb[3]-bb[1])/S
        np_=max(5,int(round(p*ink_h/h)))
        if np_==p: break
        p=np_
    while True:
        f=F(ttf,p*S); gb=f.getbbox('한'); bb=f.getbbox(text)
        w=bb[2]-bb[0]
        if w/S*cond_min<=maxw or p<=6: break
        p-=1
    im=Image.new('L',(w+8*S,int((ink_h+8)*S)),0)
    ImageDraw.Draw(im).text((4*S-bb[0],4*S-gb[1]),text,font=f,fill=255)
    sx=min(1.0,maxw/(w/S))
    W=max(1,int(round(im.size[0]/S*sx))); H=int(round(im.size[1]/S))
    m=np.asarray(im.resize((W,H),Image.LANCZOS),np.float32)/255
    # trim
    ys=np.where(m.max(1)>0.02)[0]; xs=np.where(m.max(0)>0.02)[0]
    return m[ys[0]:ys[-1]+1, xs[0]:xs[-1]+1], 4-ys[0]  # mask, offset of '한' top
def paste(out,m,ox,oy,col):
    H,W=out.shape[:2]; mh,mw=m.shape
    y0=max(0,oy); x0=max(0,ox); y1=min(H,oy+mh); x1=min(W,ox+mw)
    if y1<=y0 or x1<=x0: return
    sub=m[y0-oy:y1-oy, x0-ox:x1-ox][...,None]
    reg=out[y0:y1,x0:x1]
    reg[...,:3]=reg[...,:3]*(1-sub)+np.array(col)[None,None,:3]*sub
def plate(img,text,ttf=ROOT+"NanumSquareNeo-eHv.ttf",x0=10,x1=118,margin=6):
    im=img.astype(np.float32); H,Wd=im.shape[:2]
    L=lum(im[...,:3])
    body=[y for y in range(H) if np.median(im[y,x0:x1,3])>200]
    yb0,yb1=body[0]+2,body[-1]-2
    tm=np.zeros((H,Wd),bool)
    for y in range(yb0,yb1+1):
        l=L[y,x0:x1]; ref=np.percentile(l,70)
        tm[y,x0:x1]=l<ref-55
    ys,xs=np.where(tm)
    if len(ys)==0: return img
    ty0,ty1,tx0,tx1=ys.min(),ys.max(),xs.min(),xs.max()
    dark=im[tm][:,:3]; tcol=np.median(dark[lum(dark)<=np.percentile(lum(dark),25)],0)
    out=im.copy()
    lx=max(x0-3,tx0-3); rx=min(x1+2,tx1+3)
    for y in range(max(0,ty0-2),min(H,ty1+3)):
        A=im[y,lx]; B=im[y,rx]
        t=np.linspace(0,1,rx-lx+1)[:,None]
        out[y,lx:rx+1]=A[None,:]*(1-t)+B[None,:]*t
    ink=ty1-ty0+1
    m,_=text_mask(text,ttf,ink+1,(x1-x0)-2*margin)
    mh,mw=m.shape
    ox=int(round((x0+x1)/2-mw/2)); oy=int(round((ty0+ty1)/2-mh/2))
    paste(out,m,ox,oy,tcol)
    return np.clip(out,0,255).astype(np.uint8)
