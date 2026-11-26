import sys,glob,os,hashlib,pickle;sys.path.insert(0,'scripts');from arc import *;import bclim
seen={};items=[]
for fn in sorted(glob.glob('romfs/**/*.arc.lz',recursive=True)):
    d=lz11_dec(open(fn,'rb').read())
    for p,i,a,b in darc_read(d):
        if not p.endswith('.bclim'): continue
        x=d[a:a+b]; h=hashlib.md5(x).hexdigest()
        if h in seen: continue
        w,hh,f=bclim.info(x)
        if w<16 or hh<10: continue
        seen[h]=1; items.append((os.path.relpath(fn,'romfs').replace(os.sep,'/'),p))
pickle.dump(items,open('_view/img/index.pkl','wb')); print(len(items))
