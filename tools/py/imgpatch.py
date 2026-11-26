"""bclim 이미지 한글화 명세 (원본 md5 기준)"""
import hashlib,numpy as np
from PIL import Image,ImageDraw,ImageFont
import bclim,plate,textimg
import os; ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
def caution_lower(im):
    out=np.zeros_like(im); out[...,3]=255
    f=ImageFont.truetype(ROOT+'NanumSquareNeo-bRg.ttf',12*4)
    lines=['게임 소프트웨어를 권리자의 허락 없이 인터넷을','통해 배포·전송하는 것은 저작권을 침해하는','위법 행위이며, 민사·형사상 법적 제재를','받을 수 있습니다.',None,'또한 위법한 배포임을 알면서 다운로드하는','행위도 사적 사용 목적의 복제가 아니며','위법입니다.',None,'여러분의 이해와 협조를 부탁드립니다.']
    ys=[55,72,89,106,None,128,145,162,None,185]
    pil=Image.new('L',(320*4,240*4),0); d=ImageDraw.Draw(pil)
    gb=f.getbbox('한')
    for t,y in zip(lines,ys):
        if t: d.text((25*4,y*4-gb[1]),t,font=f,fill=255)
    m=np.asarray(pil.resize((320,240),Image.LANCZOS))
    out[...,0]=out[...,1]=out[...,2]=m
    return out
def caution_upper(im):
    out=im.copy(); reg=out[100:133,168:256]
    red=reg[...,0].astype(int); col=np.median(reg[red>150][:,:3],0)
    reg[...,:3]=0
    f=ImageFont.truetype(ROOT+'NanumSquareNeo-eHv.ttf',22*4)
    pil=Image.new('L',(88*4,33*4),0); gb=f.getbbox('주의')
    ImageDraw.Draw(pil).text((2*4-gb[0],9*4-gb[1]),'주의',font=f,fill=255)
    m=np.asarray(pil.resize((88,33),Image.LANCZOS),np.float32)[...,None]/255
    reg[...,:3]=(col[None,None,:]*m).astype(np.uint8)
    return out
def specs(names):
    """names: dict 'abiNNN'/'itmNNN'/'smnNNN' -> ko name. returns {md5: func(img)->img} built lazily by caller using get_by_index"""
    S={}
    T=lambda spec:(lambda im: textimg.process(im,spec))
    P=lambda spec:(lambda im: textimg.process2(im,spec))
    S[965]=T([{'text':'파워업 몬스터','wide':1}]); S[966]=T([{'text':'스피드 업','wide':1}]); S[967]=T([{'text':'줌업 트리거','wide':1}])
    S[968]=T([{'text':'웨이브 스피드','wide':1}]); S[969]=T([{'text':'물음표 트리거','wide':1}]); S[970]=T([{'text':'랜덤 스피드','wide':1}])
    S[971]=T([{'text':'스토익 저지','wide':1}]); S[972]=T([{'text':'체인 어택','wide':1}]); S[973]=T([{'text':'프리즈 스코어','wide':1}]); S[974]=T([{'text':'HP 체인지','wide':1}])
    S[1072]=T([{'text':'다음 설명으로 넘어갈까요?','wide':1}])
    S[1203]=T([{'text':'오늘의 추천!','box':[12,0,67,11],'wide':1,'ink':8}])
    S[1204]=T([{'text':'퀵 스타트 등록됨','box':[16,0,127,13],'wide':1}])
    S[1205]=T([{'text':'퀵 스타트 등록됨','box':[16,0,127,13],'wide':1}])
    S[1864]=T([{'text':'보스 토벌 보상','wide':1}])
    S[1049]=P([{'text':'로 일시정지 메뉴를 표시합니다','box':[66,12,226,30],'align':'l','wide':1,'t':1}])
    for i in (1102,1104,2365,2366): S[i]=P([{'text':'뒤로','box':[22,6,62,28],'thr':0.45,'t':0.8}])
    S[1237]=P([{'text':'전곡','box':[6,8,52,30],'thr':0.7,'t':1.2}])
    S[2377]=caution_upper
    S[2376]=caution_lower
    return S

def relabel(im,box,text,font='EB',pad=1):
    x0,y0,x1,y1=box; out=im.copy(); reg=out[y0:y1+1,x0:x1+1].astype(np.float32)
    border=np.concatenate([reg[0],reg[-1],reg[:,0],reg[:,-1]])
    bg=np.median(border,0)
    d=np.abs(reg-bg).sum(-1); tcol=np.median(reg[d>=np.percentile(d,97)],0)
    L=reg[:,0].copy(); Rr=reg[:,-1].copy(); t=np.linspace(0,1,reg.shape[1])[None,:,None]; reg[:]=L[:,None]*(1-t)+Rr[:,None]*t
    H=y1-y0+1-2*pad; W=x1-x0+1-2*pad
    lines=text.split('\n'); lh=H/len(lines)
    ttf=textimg.FONTS[font]; S=4
    pil=Image.new('L',(W*S,H*S),0); dr=ImageDraw.Draw(pil)
    p=int(min(lh*0.8,13)*S)
    while p>8:
        f=ImageFont.truetype(ttf,p)
        if max(f.getbbox(l)[2]-f.getbbox(l)[0] for l in lines)<=W*S*1.25: break
        p-=4
    f=ImageFont.truetype(ttf,p); gb=f.getbbox('한')
    for k,l in enumerate(lines):
        b=f.getbbox(l); lw=b[2]-b[0]
        tmp=Image.new('L',(lw+8,int(lh*S)),0); ImageDraw.Draw(tmp).text((-b[0]+4,(lh*S-(gb[3]-gb[1]))/2-gb[1]),l,font=f,fill=255)
        if lw>W*S: tmp=tmp.resize((W*S,tmp.size[1]),Image.LANCZOS)
        pil.paste(tmp,((W*S-tmp.size[0])//2,int(k*lh*S)))
    m=np.asarray(pil.resize((W,H),Image.LANCZOS),np.float32)[...,None]/255
    sub=reg[pad:pad+H,pad:pad+W]; sub[:]=sub*(1-m)+tcol*m
    out[y0:y1+1,x0:x1+1]=np.clip(reg,0,255).astype(np.uint8)
    return out
def RL(*items):
    def f(im):
        for box,t in items: im=relabel(im,box,t)
        return im
    return f
TUT={2465:RL(([4,42,58,63],'터치\n스타일'),([73,42,127,63],'버튼\n스타일'),([143,42,196,63],'하이브리드\n스타일'),([212,42,268,63],'원핸드\n스타일')),
 2466:RL(([10,56,91,79],'빠른 템포의\n배틀 곡'),([117,56,196,79],'느긋한\n필드 곡'),([224,56,303,79],'극적인\n이벤트 곡')),
 2467:RL(([89,17,133,29],'트리거'),([168,17,242,29],'저스트 서클')),
 2469:RL(([2,49,102,62],'터치 트리거'),([118,49,218,62],'슬라이드 트리거'),([233,49,333,62],'홀드 트리거'),([2,67,102,96],'터치하기'),([118,67,218,96],'화살표 방향\n슬라이드'),([233,67,333,96],'길이만큼\n터치 후 떼기')),
 2480:RL(([106,11,194,22],'저스트 서클')),2484:RL(([32,12,124,22],'홀드 미드포인트')),
 2487:RL(([14,4,143,16],'실버 컬러 트리거')),2488:RL(([14,4,135,15],'크리티컬 히트 트리거')),
 2491:RL(([196,3,252,15],'HP 게이지'),([64,21,110,39],'대미지')),
 2492:RL(([84,5,122,19],'이번')),2493:RL(([84,5,122,19],'누계'))}
_old=specs
def specs(names):
    S=_old(names); S.update(TUT); return S
_old2=specs
def specs(names):
    S=_old2(names)
    P=lambda spec:(lambda im: textimg.process2(im,spec))
    S[2116]=P([{'text':'리더','box':[2,10,40,26],'ink':9}]); S[2118]=P([{'text':'멤버','box':[2,10,40,26],'ink':9}])
    return S
_old3=specs
def specs(names):
    S=_old3(names)
    S[1293]=RL(([7,15,51,43],'전곡')); S[1320]=RL(([8,13,34,28],'전곡'))
    return S

# ---- 타이틀 로고 하단 문구 ----
LOGO_KO='시어트리듬 파이널 판타지 커튼콜'
def _logo_mask(text, font='Galmuri11-Bold.ttf', size=12):
    f=ImageFont.truetype(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/tools/galmuri/'+font,size)
    w=int(f.getlength(text))+4; pil=Image.new('L',(w,size+6),0)
    ImageDraw.Draw(pil).text((2,2),text,font=f,fill=255)
    m=np.asarray(pil)>127; ys=np.nonzero(m.any(1))[0]; xs=np.nonzero(m.any(0))[0]
    return m[ys.min():ys.max()+1, xs.min():xs.max()+1]
def _cols(ref):
    a=ref[...,3]>200; L=ref[...,:3].astype(int).sum(-1)
    fill=np.median(ref[a&(L<np.percentile(L[a],30))][:,:3],0)
    edge=np.median(ref[a&(L>np.percentile(L[a],75))][:,:3],0)
    return fill,edge
def _draw_logo_text(out, cx, top, fill, edge, silhouette=False):
    import cv2
    m=_logo_mask(LOGO_KO); h,w=m.shape
    pad=1 if not silhouette else 3
    M=np.zeros((h+2*pad,w+2*pad),np.uint8); M[pad:-pad,pad:-pad]=m
    E=cv2.dilate(M,np.ones((2*pad+1,2*pad+1),np.uint8)).astype(bool)
    x0=int(cx-(w+2*pad)/2); y0=top-pad
    H,W=out.shape[:2]
    for yy in range(M.shape[0]):
        for xx in range(M.shape[1]):
            Y=y0+yy; X=x0+xx
            if not(0<=Y<H and 0<=X<W): continue
            if silhouette:
                if E[yy,xx]: out[Y,X]=(255,255,255,255)
            elif M[yy,xx]: out[Y,X,:3]=fill; out[Y,X,3]=255
            elif E[yy,xx]: out[Y,X,:3]=edge; out[Y,X,3]=255
    return out
def logo_strip(im):
    fill,edge=_cols(im); out=np.zeros_like(im)
    return _draw_logo_text(out, im.shape[1]/2, 1, fill, edge)
def logo_main(im):
    ref=im[170:188]; fill,edge=_cols(ref)
    out=im.copy(); out[170:]=0
    return _draw_logo_text(out, 160, 172, fill, edge)
def logo_back(im):
    out=im.copy(); out[171:]=0
    return _draw_logo_text(out, 161, 173, None, None, silhouette=True)
_old4=specs
def specs(names):
    S=_old4(names); S[2411]=logo_strip; S[2408]=logo_main; S[2409]=logo_back
    return S
