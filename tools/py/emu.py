import ctypes,ctypes.wintypes as W,subprocess,time,os,sys
u=ctypes.windll.user32; g=ctypes.windll.gdi32
EXE=os.path.abspath('tools/azahar/azahar-windows-msvc-2127.0.1/azahar.exe')
ROM=os.path.abspath('../Theatrhythm Final Fantasy - Curtain Call (Japan).3ds')
def windows(pid=None):
    res=[]
    @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def cb(h,l):
        p=W.DWORD(); u.GetWindowThreadProcessId(h,ctypes.byref(p))
        if u.IsWindowVisible(h):
            n=ctypes.create_unicode_buffer(256); u.GetWindowTextW(h,n,256)
            exe=None
            res.append((h,p.value,n.value))
        return True
    u.EnumWindows(cb,0); return res
def find_main():
    for h,p,t in windows():
        if t.startswith('Azahar'): return h
def capture(h,path):
    from PIL import Image
    r=W.RECT(); u.GetClientRect(h,ctypes.byref(r)); w,hh=r.right,r.bottom
    hdc=u.GetDC(h); mdc=g.CreateCompatibleDC(hdc); bmp=g.CreateCompatibleBitmap(hdc,w,hh); g.SelectObject(mdc,bmp)
    u.PrintWindow(h,mdc,3)
    class BI(ctypes.Structure): _fields_=[('a',W.DWORD),('w',W.LONG),('h',W.LONG),('p',W.WORD),('b',W.WORD),('c',W.DWORD),('s',W.DWORD),('x',W.LONG),('y',W.LONG),('cu',W.DWORD),('ci',W.DWORD)]
    bi=BI(40,w,-hh,1,32,0,0,0,0,0,0); buf=ctypes.create_string_buffer(w*hh*4)
    g.GetDIBits(mdc,bmp,0,hh,buf,ctypes.byref(bi),0)
    im=Image.frombuffer('RGBA',(w,hh),buf,'raw','BGRA',0,1).convert('RGB'); im.save(path)
    g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(h,hdc); return im
VK={'a':0x41,'b':0x42,'x':0x58,'y':0x59,'q':0x51,'w':0x57,'m':0x4D,'n':0x4E,'up':0x26,'down':0x28,'left':0x25,'right':0x27,'enter':0x0D,'bs':0x08,'t':0x54,'g':0x47,'f':0x46,'h':0x48,'1':0x31,'2':0x32,'3':0x33,'4':0x34}
def child_render(h):
    res=[]
    @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def cb(c,l): res.append(c); return True
    u.EnumChildWindows(h,cb,0); return res
def key(h,k,hold=0.12):
    vk=VK[k]; sc=u.MapVirtualKeyW(vk,0)
    targets=[h]+child_render(h)
    for t in targets: u.PostMessageW(t,0x100,vk,1|(sc<<16))
    time.sleep(hold)
    for t in targets: u.PostMessageW(t,0x101,vk,1|(sc<<16)|0xC0000000)
    time.sleep(0.15)
def touch(h,x,y,hold=0.15):
    """x,y in bottom-screen coords (320x240); assumes default layout 1280x480 client region"""
    r=W.RECT(); u.GetClientRect(h,ctypes.byref(r))
    # locate render child containing point
    cx=480+x; cy=273+y
    best=None
    for c in child_render(h):
        if not u.IsWindowVisible(c): continue
        rc=W.RECT(); u.GetWindowRect(c,ctypes.byref(rc))
        pt=W.POINT(cx,cy); u.ClientToScreen(h,ctypes.byref(pt))
        if rc.left<=pt.x<rc.right and rc.top<=pt.y<rc.bottom:
            area=(rc.right-rc.left)*(rc.bottom-rc.top)
            if best is None or area<best[0]: best=(area,c,pt.x-rc.left,pt.y-rc.top)
    _,c,lx,ly=best
    lp=(ly<<16)|lx
    u.PostMessageW(c,0x200,0,lp); u.PostMessageW(c,0x201,1,lp); time.sleep(hold)
    u.PostMessageW(c,0x202,0,lp); time.sleep(0.15)
def kbd_dialog(text):
    for h,p,t in windows():
        if t=='Azahar':
            for ch in text: u.PostMessageW(h,0x102,ord(ch),1); time.sleep(0.03)
            time.sleep(0.3)
            u.PostMessageW(h,0x100,0x0D,0x1C0001);time.sleep(0.1);u.PostMessageW(h,0x101,0x0D,0xC01C0001)
            return True
    return False
