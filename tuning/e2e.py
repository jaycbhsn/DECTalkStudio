from dt import *
from algo import *
from scipy.signal import resample_poly
from fractions import Fraction
def shift(x,semi):
    if semi==0:return x
    fr=Fraction(2**(semi/12)).limit_denominator(200);return resample_poly(x,fr.denominator,fr.numerator)
def render(voice,m,s,vw):
    p=plan(m,voice,s);rate=2**(p['semi']/12)
    pre=f"[:dv hs {p['hs']} sm {p['sm']}]" if s>0 else ''
    x,sr=dt.r(f"[:phoneme on][:{voice}]{pre}[{vw}<{round(500*rate)},{p['r']-35}>]")
    y=seg(shift(x,p['semi']),sr)
    rms=20*np.log10(np.sqrt((y**2).mean()))
    if s>0: y=y*10**(clamp((-12-rms)*0.8*s,-6,9)/20)
    sounding=p.get('sounding',p['r']+0) if s>0 else p['r']
    return y,sounding
res={}
for voice in V:
  for s in [0,0.75]:
    hi=[];lo=[];loud=[];ok=0;n=0
    for m in range(31,78,3):
        envs=[];cr=[];rm=[]
        for vw in ('iy','eh','aa','ow','uw'):
            y,snd=render(voice,m,s,vw);f0=440*2**((snd-69)/12)
            envs.append(henv(y,11025,f0));cr.append(20*np.log10(np.abs(y).max()/np.sqrt((y**2).mean())));rm.append(20*np.log10(np.sqrt((y**2).mean())))
        cl=np.mean([np.sqrt(((a-b)**2).mean()) for a,b in itertools.combinations(envs,2)])
        if m>=64:hi.append(cl)
        if m<=43:lo.append(np.mean(cr))
        loud.append(np.mean(rm));ok+=(snd==m);n+=1
    res[(voice,s)]=(np.mean(hi),np.mean(lo),np.std(loud),ok/n)
  o=res[(voice,0)];w=res[(voice,0.75)]
  print(f"{voice}: high-note clarity {o[0]:.1f}->{w[0]:.1f} | low-note buzz {o[1]:.1f}->{w[1]:.1f} dB | loudness spread {o[2]:.1f}->{w[2]:.1f} dB | correct pitch {o[3]*100:.0f}%->{w[3]*100:.0f}%",flush=True)
