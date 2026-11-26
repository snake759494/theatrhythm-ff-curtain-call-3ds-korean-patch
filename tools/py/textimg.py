import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
import os; ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
FONTS={'H':ROOT+'NanumSquareNeo-eHv.ttf','EB':ROOT+'NanumSquareNeo-dEb.ttf','B':ROOT+'NanumSquareNeo-cBd.ttf','R':ROOT+'NanumSquareNeo-bRg.ttf','M':ROOT+'SeoulHangangEB.ttf','G':os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/tools/galmuri/Galmuri11-Bold.ttf','G9':os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/tools/galmuri/Galmuri9.ttf'}
_F={}
def F(p,s):
    if (p,s) not in _F: _F[(p,s)]=ImageFont.truetype(p,s)
    return _F[(p,s)]
def lum(c): return c[...,0]*0.299+c[...,1]*0.587+c[...,2]*0.114
def analyze(reg,bg=None):
    """reg float RGBA 0..1. returns style dict: fill(rowwise), outline color, t"""
    a=reg[...,3]
    if bg is not None:
        diff=np.abs(reg[...,:3]-bg[...,:3]).max(-1)
        m=diff>0.18
    else:
        m=a>0.5
    D=ndi.distance_transform_edt(m)
    cols=reg[m][:,:3]; ds=D[m]; yy=np.where(m)[0]
    if len(cols)<5: return None
    c0=cols[ds>=np.percentile(ds,85)].mean(0); e=(ds<=1.5); c1=cols[e].mean(0) if e.any() else cols.mean(0)
    lab=np.zeros(len(cols),bool)
    for _ in range(10):
        lab=np.abs(cols-c1).sum(1)<np.abs(cols-c0).sum(1)
        if lab.all() or (~lab).all(): break
        c0=cols[~lab].mean(0); c1=cols[lab].mean(0)
    has=bool(np.abs(c0-c1).max()>0.25 and lab.any() and (~lab).any() and ds[~lab].mean()-ds[lab].mean()>0.6)
    st={'mask':m}
    if has:
        t=max(0.7,float(np.percentile(ds[~lab],10))-0.5)
        fill_sel=~lab; st['outline']=np.median(cols[lab],0); st['t']=min(t,4)
    else:
        fill_sel=np.ones(len(cols),bool); st['t']=0; st['outline']=None
    grad={}
    for y in np.unique(yy):
        s=fill_sel&(yy==y)
        if s.sum()>=2: grad[int(y)]=np.median(cols[s],0)
    st['grad']=grad; st['fill']=np.median(cols[fill_sel],0)
    ys=np.where(m.any(1))[0]; xs=np.where(m.any(0))[0]
    st['bbox']=(int(xs[0]),int(ys[0]),int(xs[-1]),int(ys[-1]))
    return st
def render(text,st,W,H,font='H',ink=None,align='c',cx=None,cy=None,cond_min=0.5,S=4,shrink_to=None):
    """returns RGBA float (H,W) drawing of text with style"""
    t=st['t']; x0,y0,x1,y1=st['bbox']
    ink_h=ink or (y1-y0+1-2*t)
    ttf=FONTS[font]
    p=max(6,int(ink_h*1.3))
    for _ in range(6):
        bb=F(ttf,p*S).getbbox('한'); h=(bb[3]-bb[1])/S
        np_=max(6,int(round(p*ink_h/h)))
        if np_==p: break
        p=np_
    maxw=(shrink_to or (x1-x0+1))-2*t
    while True:
        f=F(ttf,p*S); bb=f.getbbox(text); gb=f.getbbox('한')
        tw=(bb[2]-bb[0])/S
        if tw*cond_min<=maxw or p<=6: break
        p-=1
    pad=int(np.ceil(t))+2
    im=Image.new('L',(bb[2]-bb[0]+2*pad*S,int((ink_h+2*pad+6)*S)),0)
    ImageDraw.Draw(im).text((pad*S-bb[0],pad*S-gb[1]),text,font=f,fill=255)
    sx=min(1.0,maxw/tw)
    hi=np.asarray(im,np.float32)/255
    Wn=max(1,int(round(im.size[0]*sx))); 
    hi=np.asarray(im.resize((Wn,im.size[1]),Image.LANCZOS),np.float32)/255
    def down(z):
        h,w=z.shape; h2=h//S*S; w2=w//S*S
        return z[:h2,:w2].reshape(h2//S,S,w2//S,S).mean((1,3))
    M=down(hi)
    if t>0:
        Dd=ndi.distance_transform_edt(~(hi>0.5))/S
        O=down(np.clip(t+0.5-Dd,0,1)); A=np.maximum(O,M)
    else: A=M
    hh,ww=M.shape
    col=np.zeros((hh,ww,3),np.float32)
    # map rows: '한' top at row pad -> original ink top y0+t
    for r in range(hh):
        y=int(round(y0+t+(r-pad)))
        col[r]=st['grad'].get(y,st['fill'])
    if t>0: col=col*M[...,None]+st['outline'][None,None,:]*(1-M[...,None])
    out=np.zeros((H,W,4),np.float32)
    # position
    xs=np.where(A.max(0)>0.02)[0]; A=A[:,xs[0]:xs[-1]+1]; col=col[:,xs[0]:xs[-1]+1]; ww=A.shape[1]
    ccx=cx if cx is not None else (x0+x1)/2
    if align=='l': ox=x0
    elif align=='r': ox=x1+1-ww
    else: ox=int(round(ccx-ww/2))
    oy=int(round(y0+t-pad)) if cy is None else int(round(cy-hh/2))
    for r in range(hh):
        Y=oy+r
        if not(0<=Y<H): continue
        for_x0=max(0,ox); for_x1=min(W,ox+ww)
        if for_x1<=for_x0: continue
        out[Y,for_x0:for_x1,:3]=col[r,for_x0-ox:for_x1-ox]
        out[Y,for_x0:for_x1,3]=A[r,for_x0-ox:for_x1-ox]
    return out
def over(dst,src):
    a=src[...,3:4]; outa=a+dst[...,3:4]*(1-a)
    rgb=(src[...,:3]*a+dst[...,:3]*dst[...,3:4]*(1-a))/np.maximum(outa,1e-6)
    return np.concatenate([rgb,outa],-1)
def interp_bg(img,box,vertical=False):
    x0,y0,x1,y1=box; out=img.copy()
    if not vertical:
        L=img[y0:y1+1,x0-1]; R=img[y0:y1+1,x1+1]
        t=np.linspace(0,1,x1-x0+1)[None,:,None]
        out[y0:y1+1,x0:x1+1]=L[:,None,:]*(1-t)+R[:,None,:]*t
    else:
        T=img[y0-1,x0:x1+1]; B=img[y1+1,x0:x1+1]
        t=np.linspace(0,1,y1-y0+1)[:,None,None]
        out[y0:y1+1,x0:x1+1]=T[None,:,:]*(1-t)+B[None,:,:]*t
    return out
def process(img8,spec):
    """spec: list of ops: {'text','box':[x0,y0,x1,y1] or None,'mode':'clear'|'interp'|'vinterp','font','align','ink','ttfill'}"""
    img=img8.astype(np.float32)/255
    for op in spec:
        H,W=img.shape[:2]
        box=op.get('box') or [0,0,W-1,H-1]
        x0,y0,x1,y1=box
        reg=img[y0:y1+1,x0:x1+1].copy()
        mode=op.get('mode','clear')
        if mode=='clear':
            st=analyze(reg)
            base=img.copy(); base[y0:y1+1,x0:x1+1]=0
        else:
            base=interp_bg(img,box,vertical=(mode=='vinterp'))
            st=analyze(reg,base[y0:y1+1,x0:x1+1])
        if st is None: continue
        if 'fill' in op: st['fill']=np.array(op['fill'],np.float32)/255; st['grad']={}
        if 'outline' in op:
            st['outline']=np.array(op['outline'],np.float32)/255; st['t']=op.get('t',1.0)
        if op.get('t') is not None and 'outline' not in op: st['t']=op['t']
        bx=st['bbox']
        if op.get('wide'): st['bbox']=(0,bx[1],x1-x0,bx[3])
        r=render(op['text'],st,x1-x0+1,y1-y0+1,font=op.get('font','H'),ink=op.get('ink'),align=op.get('align','c'),shrink_to=op.get('maxw'))
        sub=base[y0:y1+1,x0:x1+1]
        base[y0:y1+1,x0:x1+1]=over(sub,r)
        img=base
    return np.clip(img*255+0.5,0,255).astype(np.uint8)

def inpaint(img,mask,iters=200):
    """diffusion fill of masked pixels using premultiplied RGBA"""
    pm=img.copy(); pm[...,:3]*=pm[...,3:4]
    known=~mask
    cur=pm.copy(); cur[mask]=0
    w=known.astype(np.float32)
    k=np.array([[0,1,0],[1,0,1],[0,1,0]],np.float32)
    for _ in range(iters):
        s=np.stack([ndi.convolve(cur[...,c]*w,k,mode='nearest') for c in range(4)],-1)
        n=ndi.convolve(w,k,mode='nearest')
        upd=mask&(n>0)
        cur[upd]=s[upd]/n[upd][:,None]
        w=np.where(upd,1.0,w)
    out=cur.copy(); a=np.maximum(out[...,3:4],1e-6); out[...,:3]=np.where(out[...,3:4]>1e-4,out[...,:3]/a,0)
    return out
def process2(img8,spec):
    img=img8.astype(np.float32)/255
    for op in spec:
        H,W=img.shape[:2]
        x0,y0,x1,y1=op['box']
        reg=img[y0:y1+1,x0:x1+1]
        L=lum(reg[...,:3])
        sel=(L>op.get('thr',0.6)) if op.get('sel','bright')=='bright' else (L<op.get('thr',0.3))
        sel&=reg[...,3]>0.4
        t=op.get('t',1.5)
        dil=ndi.binary_dilation(sel,iterations=int(np.ceil(t))+1)
        fill=np.median(reg[sel][:,:3],0)
        ring=dil&~sel
        oc=reg[ring][:,:3]
        if op.get('outline') is not None: outl=np.array(op['outline'],np.float32)/255
        else:
            Lr=lum(oc); outl=np.median(oc[Lr<=np.percentile(Lr,30)],0) if op.get('sel','bright')=='bright' else np.median(oc[Lr>=np.percentile(Lr,70)],0)
        if op.get('fill') is not None: fill=np.array(op['fill'],np.float32)/255
        mask=np.zeros((H,W),bool); mask[y0:y1+1,x0:x1+1]=dil
        base=inpaint(img,mask)
        ys,xs=np.where(sel)
        st={'t':t if op.get('outlined',True) else 0,'outline':outl,'grad':{},'fill':fill,
            'bbox':(x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max()),y0+int(ys.max()))}
        if op.get('wide'): st['bbox']=(x0,st['bbox'][1],x1,st['bbox'][3])
        # render in full-image coords
        st2=dict(st); st2['bbox']=(st['bbox'][0],st['bbox'][1]-st['t'],st['bbox'][2],st['bbox'][3]+st['t'])
        st2['bbox']=tuple(int(round(v)) for v in st2['bbox'])
        r=render(op['text'],st2,W,H,font=op.get('font','H'),ink=op.get('ink'),align=op.get('align','c'),shrink_to=op.get('maxw'))
        img=over(base,r)
    return np.clip(img*255+0.5,0,255).astype(np.uint8)

def inpaint(img,mask,iters=0):
    """nearest known pixel fill (keeps shape edges sharp) + light RGB smoothing inside mask"""
    idx=ndi.distance_transform_edt(mask,return_distances=False,return_indices=True)
    out=img[idx[0],idx[1]].copy()
    # smooth RGB inside mask where alpha high
    sm=np.stack([ndi.uniform_filter(out[...,c],3) for c in range(3)],-1)
    m=mask&(out[...,3]>0.5)
    out[m,:3]=sm[m]
    return out
