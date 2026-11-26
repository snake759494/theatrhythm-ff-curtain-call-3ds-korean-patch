import sys,struct;sys.path.insert(0,'tools/azahar/azahar-windows-msvc-2127.0.1/scripting')
from AzaharRPC import AzaharRPC
def R(): return AzaharRPC(timeout=2)
def dump(r,start,size,chunk=16000):
    out=bytearray()
    for a in range(start,start+size,chunk):
        try: out+=r.read_memory(a,min(chunk,start+size-a))
        except Exception: out+=b'\0'*min(chunk,start+size-a)
    return bytes(out)
