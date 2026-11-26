import sys,time;sys.path.insert(0,'scripts');import emu
h=emu.find_main()
for c in sys.argv[1:]:
    if c.startswith('w'): time.sleep(float(c[1:]))
    elif c.startswith('s:'): emu.capture(h,'_view/'+c[2:]+'.png')
    elif c.startswith('t:'):
        x,y=map(int,c[2:].split(','));emu.touch(h,x,y)
    else:
        k,_,n=c.partition('*')
        for i in range(int(n or 1)): emu.key(h,k)
