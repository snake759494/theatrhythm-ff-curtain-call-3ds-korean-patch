import sys,time;sys.path.insert(0,'scripts');import emu
h=emu.find_main(); T=float(sys.argv[1]); t0=time.time()
while time.time()-t0<T:
    emu.key(h,'a',hold=0.03); time.sleep(0.03)
