import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
from bcfnt import glyph_images
import os; ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
NANUM={'L':'NanumSquareNeo-aLt.ttf','R':'NanumSquareNeo-bRg.ttf','B':'NanumSquareNeo-cBd.ttf','EB':'NanumSquareNeo-dEb.ttf','H':'NanumSquareNeo-eHv.ttf'}
SEOUL={'L':'SeoulHangangL.ttf','R':'SeoulHangangM.ttf','B':'SeoulHangangB.ttf','EB':'SeoulHangangEB.ttf','H':'SeoulHangangEB.ttf'}
GAL=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/tools/galmuri/'
def pick_ttf(name):
    n=name.lower()
    if n.startswith('cbf'): w='R'
    elif '_eb' in n or n.startswith('humming_e') or 'std_e' in n: w='H'
    elif '_db' in n or '_d_' in n or '_db_' in n: w='EB'
    elif '_b' in n or 'std_b' in n or n.startswith('skip'): w='EB'
    else: w='R'
    if 'mincho' in n or 'mincyou' in n: return ROOT+SEOUL[w]
    return ROOT+NANUM[w]
def ref_stats(f):
    gl=glyph_images(f); inv={v:k for k,v in f['cmap_d'].items()}
    refs=[i for i,c in inv.items() if 0x4e00<=c<=0x9fff] or [i for i,c in inv.items() if 0x3040<=c<=0x30ff] or [i for i,c in inv.items() if 0x41<=c<=0x5a] or [i for i,c in inv.items() if c>0x20]
    hs=[];tops=[];bots=[];cws=[];lefts=[]
    samples_d=[];samples_c=[];samples_a=[];samples_y=[]
    for i in refs:
        g=gl[i].astype(np.float32)/255; a=g[...,3]
        rows=np.where(a.max(1)>0.3)[0]
        if len(rows)==0: continue
        tops.append(rows[0]); bots.append(rows[-1]); 
        w=f['widths'].get(i); 
        if w: cws.append(w[2]); lefts.append(w[0])
        m=a>0.5
        D=ndi.distance_transform_edt(m)
        ys,xs=np.where(m)
        samples_d+=list(D[ys,xs]); samples_c+=list(g[ys,xs,:3].mean(1) if True else 0); samples_a+=list(a[ys,xs]); samples_y+=list(ys)
        sc=g[ys,xs,:3]
    st={}
    st['top']=float(np.median(tops)); st['bot']=float(np.median(bots))
    st['cw']=int(np.median(cws)) if cws else f['cellw']; st['left']=int(np.median(lefts)) if lefts else 0
    d=np.array(samples_d); c=np.array(samples_c)
    # full-color samples for fill/outline
    cols=[];ds=[];yy=[]
    for i in refs:
        g=gl[i].astype(np.float32)/255; a=g[...,3]; m=a>0.5; D=ndi.distance_transform_edt(m); ys,xs=np.where(m)
        cols.append(g[ys,xs,:3]); ds.append(D[ys,xs]); yy.append(ys)
    cols=np.concatenate(cols); ds=np.concatenate(ds); yy=np.concatenate(yy)
    X=cols
    c0=X[ds>=np.percentile(ds,90)].mean(0); m12=(ds>1)&(ds<=2); c1=X[m12].mean(0) if m12.any() else X.mean(0)
    lab=np.zeros(len(X),bool)
    for _ in range(10):
        lab=(np.abs(X-c1).sum(1)<np.abs(X-c0).sum(1))
        if lab.all() or (~lab).all(): break
        c0=X[~lab].mean(0); c1=X[lab].mean(0)
    st['has_outline']=bool(np.abs(c0-c1).max()>0.25 and lab.any() and (~lab).any())
    if st['has_outline']:
        if ds[lab].mean()>ds[~lab].mean(): c0,c1,lab=c1,c0,~lab
        if ds[~lab].mean()-ds[lab].mean()<0.8: st['has_outline']=False
    if st['has_outline']:
        fill=c0; oc=X[lab]; dd=np.abs(oc-c0).sum(1); outl=np.median(oc[dd>=np.median(dd)],0)
        t=max(0.5,float(np.percentile(ds[~lab],10))-0.5); t=min(t,6.0)
    else:
        fill=np.median(cols,0); outl=fill; t=0
    st['fill']=fill; st['outline']=outl; st['t']=t
    # vertical fill gradient (by row) among inner-ish pixels (ds>t)
    grad={}
    sel=(~lab) if st['has_outline'] else ds>0
    for y in range(f['cellh']):
        s=sel&(yy==y)
        if s.sum()>3: grad[y]=np.median(cols[s],0)
    st['grad']=grad
    ga={}
    rows_a={}
    for i in refs:
        g=gl[i].astype(np.float32)/255; a=g[...,3]
        core=ndi.binary_erosion(a>0.02,iterations=1)
        for y in range(a.shape[0]):
            v=a[y][core[y]]
            if len(v): rows_a.setdefault(y,[]).extend(v.tolist())
    for y,v in rows_a.items():
        if len(v)>3: ga[y]=float(np.percentile(v,75))
    st['galpha']=ga
    st['alpha_grad']=False
    gd=[];ga=[];gc=[]
    for i in refs:
        g=gl[i].astype(np.float32)/255; a=g[...,3]; core=a>0.5
        if not core.any(): continue
        Do=ndi.distance_transform_edt(~core); sel=(~core)&(a>0.04)
        gd+=list(Do[sel]); ga+=list(a[sel]); gc+=list(g[sel][:,:3])
    st['glow']=0
    if gd:
        gd=np.array(gd); ga=np.array(ga)
        r=float(np.percentile(gd,95))
        if r>=1.5:
            st['glow']=r; st['glow_col']=np.median(np.array(gc),0)
            st['glow_a']=[float(np.median(ga[(gd>k-0.5)&(gd<=k+0.5)])) if ((gd>k-0.5)&(gd<=k+0.5)).any() else 0 for k in range(0,int(r)+2)]
    return st
_fc={}
def _font(p,s):
    k=(p,s)
    if k not in _fc: _fc[k]=ImageFont.truetype(p,s)
    return _fc[k]
def make_glyph(ch,f,st,ttf,small=False):
    cw,chh=f['cellw'],f['cellh']; bl=f['baseline']
    em=st['cw']
    t=st['t'] if st['has_outline'] else 0
    center=(st['top']+st['bot'])/2.0           # ink center in cell coords (outline-symmetric)
    target=min(em*0.86, (st['bot']-st['top']+1)-2*t)
    S=1 if small else 4
    if small:
        bold=any(k in ttf for k in ('cBd','dEb','eHv','B.ttf','EB.ttf'))
        if target>=9.5: F=_font(GAL+('Galmuri11-Bold.ttf' if bold else 'Galmuri11.ttf'),12); S=1
        elif target>=8: F=_font(GAL+'Galmuri9.ttf',10); S=1
        else: F=_font(GAL+'Galmuri7.ttf',8); S=1
    else:
        p=max(6,int(target*1.25))
        for _ in range(6):
            F=_font(ttf,p*S); bb=F.getbbox('한'); h=(bb[3]-bb[1])/S
            np_=max(6,int(round(p*target/h)))
            if np_==p: break
            p=np_
        F=_font(ttf,p*S)
    pad=int(np.ceil(t))+2
    H=chh+2*pad; Wd=em+2*pad+16
    im=Image.new('L',(Wd*S,H*S),0); d=ImageDraw.Draw(im)
    gbb=F.getbbox('한'); bb=F.getbbox(ch)
    gh=(gbb[3]-gbb[1])/S
    ytop=(center+pad-gh/2.0)*S-gbb[1]
    inkw=(bb[2]-bb[0])/S
    adv=(em-2 if em>=12 else em-1) if ch!=' ' else max(2,int(round(em*0.25)))
    core_left=(adv-inkw)/2.0 if ch!=' ' else 0
    x0=(pad+core_left)*S-bb[0]
    d.text((x0,ytop),ch,font=F,fill=255)
    hi=np.asarray(im,np.float32)/255
    def down(x): return x.reshape(H,S,Wd,S).mean((1,3)) if S>1 else x
    M=down(hi)
    if small: M=(M>0.45).astype(np.float32)
    if t>0:
        D=ndi.distance_transform_edt(~(hi>0.5))/S
        O=down(np.clip(t+0.5-D,0,1)); A=np.maximum(O,M)
    else: A=M
    if st.get('glow'):
        core=(A>0.5); Do=ndi.distance_transform_edt(~core)
        prof=st['glow_a']; idx=np.clip(np.round(Do).astype(int),0,len(prof)-1)
        G=np.where(core,0,np.array(prof)[idx]); G[Do>st['glow']+0.5]=0
        A2=np.maximum(A,G)
    else: A2=A
    col=np.zeros(M.shape+(3,),np.float32)
    for y in range(H):
        col[y]=st['grad'].get(y-pad,st['fill'])
    if t>0: col=col*M[...,None]+st['outline'][None,None,:]*(1-M[...,None])
    if st.get('glow'):
        col=np.where((A<0.5)[...,None],st['glow_col'][None,None,:],col)
    A=A2
    if st.get('alpha_grad'):
        for y in range(H):
            A[y]*=st['galpha'].get(y-pad,1.0)
    # crop: vertical rows pad..pad+chh map to cell rows 0..chh
    A=A[pad:pad+chh]; col=col[pad:pad+chh]
    xs=np.where(A.max(0)>0.02)[0]
    if len(xs)==0: return np.zeros((chh,1,4),np.uint8),(0,0,adv)
    x1,x2=int(xs[0]),int(xs[-1])+1
    img=np.zeros((chh,x2-x1,4),np.uint8)
    img[...,:3]=(np.clip(col[:,x1:x2],0,1)*255).astype(np.uint8)
    img[...,3]=(np.clip(A[:,x1:x2],0,1)*255).astype(np.uint8)
    left=x1-pad
    return img,(int(left),x2-x1,int(adv))
