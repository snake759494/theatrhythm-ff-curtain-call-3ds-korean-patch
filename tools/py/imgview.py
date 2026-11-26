import sys,pickle;sys.path.insert(0,'scripts');from arc import *;import bclim
from PIL import Image,ImageDraw;import numpy as np
idx=pickle.load(open('_view/img/index.pkl','rb'))
def get(i):
    a,p=idx[i]; d=lz11_dec(open('romfs/'+a,'rb').read())
    for q,_,o,s in darc_read(d):
        if q==p: return d[o:o+s]
if __name__=='__main__':
    sc=int(sys.argv[1]); ids=[int(x) for x in sys.argv[3:]]; out=sys.argv[2]
    tiles=[]
    for i in ids:
        im=bclim.decode(get(i)); bg=np.zeros(im.shape[:2]+(3,));bg[:]=(255,0,255);al=im[...,3:]/255
        t=Image.fromarray((im[...,:3]*al+bg*(1-al)).astype(np.uint8)).resize((im.shape[1]*sc,im.shape[0]*sc),Image.NEAREST)
        d=ImageDraw.Draw(t)
        for x in range(0,im.shape[1],8): d.line([(x*sc,0),(x*sc,4)],fill=(0,255,0)); d.text((x*sc+1,5),str(x),fill=(0,255,0)) if x%16==0 else None
        for y in range(0,im.shape[0],8): d.line([(0,y*sc),(4,y*sc)],fill=(0,255,0)); d.text((5,y*sc),str(y),fill=(0,255,0)) if y%16==0 else None
        tiles.append((i,t))
    W=max(t.size[0] for _,t in tiles); H=sum(t.size[1]+14 for _,t in tiles)
    C=Image.new('RGB',(W,H),(30,30,30)); dr=ImageDraw.Draw(C); y=0
    for i,t in tiles: dr.text((0,y),str(i),fill=(255,255,0)); C.paste(t,(0,y+12)); y+=t.size[1]+14
    C.save(out)
