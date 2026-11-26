import sys,os,glob,json
sys.path.insert(0,os.path.dirname(__file__)); from fmt import *
R='romfs'; res={}
for f in sorted(glob.glob(R+'/**/*.mdt',recursive=True)):
    d=open(f,'rb').read(); s=mdt_read(d); assert mdt_write(d,s)==d,f
    res[os.path.relpath(f,R).replace(os.sep,'/')]=s
for f in sorted(glob.glob(R+'/**/*.tdt',recursive=True)):
    d=open(f,'rb').read(); s=tdt_read(d); assert tdt_write(s)==d,f
    res[os.path.relpath(f,R).replace(os.sep,'/')]=[t for _,t in s]
json.dump(res,open('jp_text.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
tot=sum(len(x) for v in res.values() for x in v); print(len(res),sum(len(v) for v in res.values()),tot)
