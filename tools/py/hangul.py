import numpy as np
from PIL import Image,ImageDraw,ImageFont
_fc={}
def font(path,size):
    k=(path,size)
    if k not in _fc: _fc[k]=ImageFont.truetype(path,size)
    return _fc[k]
def render_mask(ch,path,size,cellw,cellh,baseline,scale=4,xpad=0):
    """returns alpha mask float [0,1] (cellh, w) with glyph placed on baseline, and advance width"""
    F=font(path,size*scale)
    asc,desc=F.getmetrics()
    W=(cellw+8)*scale; H=cellh*scale
    im=Image.new('L',(W,H),0); d=ImageDraw.Draw(im)
    bb=F.getbbox(ch)
    # place baseline at baseline*scale
    d.text((-bb[0]+xpad*scale, baseline*scale-asc),ch,font=F,fill=255)
    a=np.asarray(im,np.float32).reshape(cellh,scale,W//scale,scale).mean((1,3))/255
    gw=int(np.ceil((bb[2]-bb[0])/scale))+xpad
    adv=F.getlength(ch)/scale
    return a,gw,adv
