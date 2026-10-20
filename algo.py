import numpy as np
V={ # default hs, sm, natural pitch Hz, female, maxShrink(high), lowGrow
 'np':(100,3,100,0,.18,.10),'nb':(100,4,208,1,.06,0),'nh':(115,12,89,0,.18,.10),'nf':(90,46,155,0,.06,.05),
 'nd':(105,100,110,0,.18,.10),'nk':(77,5,296,1,.06,0),'nu':(95,60,240,1,.06,0),'nr':(95,24,106,1,.06,0),'nw':(100,100,200,1,.04,0)}
clamp=lambda x,a,b:max(a,min(b,x))
def plan(m,voice,s=0.75):
    hs0,sm0,ap,fem,shrink,grow=V[voice]
    if s<=0:
        r=m
        while r<36:r+=12
        while r>72:r-=12
        return dict(r=r,semi=0,hs=hs0,sm=sm0)
    mm=m;k=0
    while mm>77:mm-=12
    while mm<31:mm+=12
    r=clamp(mm,36,72);semi=mm-r;rate=2**(semi/12)
    f0=440*2**((mm-69)/12)
    up=clamp((np.log2(f0/ap)-0.8)/0.6,0,1)
    down=max(clamp((np.log2(ap/f0)-0.3)/1.0,0,1),clamp((48-mm)/12,0,1)*0.7)
    hfx=1-shrink*up*s+grow*down*s
    lo=round(hs0*0.94) if fem else 65
    hs=round(clamp(hs0*hfx*rate,lo,130))
    sm=round(clamp(sm0+30*down*s,0,100))
    return dict(r=r,semi=semi,hs=hs,sm=sm,sounding=mm)
