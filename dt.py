import subprocess,numpy as np,wave,itertools
class DT:
    def __init__(s):
        s.p=subprocess.Popen(['/home/claude/engine/dtserver-x86'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd='/tmp/rt');s.p.stdout.readline()
    def r(s,txt):
        s.p.stdin.write(f'/tmp/rt/tune.wav\t{txt}\n');s.p.stdin.flush();s.p.stdout.readline()
        w=wave.open('/tmp/rt/tune.wav');return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768,w.getframerate()
dt=DT()
def seg(x,sr):
    a=np.abs(x);on=np.argmax(a>0.01);off=len(a)-np.argmax(a[::-1]>0.01)
    L=off-on;return x[on+int(L*.25):on+int(L*.75)]
def env(y,sr):
    w=y*np.hanning(len(y));S=np.abs(np.fft.rfft(w,8192))+1e-9;ls=20*np.log10(S)
    c=np.fft.irfft(ls);lift=24;c[lift:-lift]=0;e=np.fft.rfft(c).real[:len(ls)]
    f=np.fft.rfftfreq(8192,1/sr);m=(f>150)&(f<4000);return e[m]-e[m].mean(),S,f
def measure(voice,pn,vowels=('iy','eh','aa','ow','uw'),pre=''):
    envs=[];rms=[];cen=[];crest=[]
    for v in vowels:
        x,sr=dt.r(f'[:phoneme on][:{voice}]{pre}[{v}<500,{pn}>]');y=seg(x,sr)
        e,S,f=env(y,sr);envs.append(e)
        rms.append(20*np.log10(np.sqrt((y**2).mean())+1e-9));cen.append((S*f).sum()/S.sum());crest.append(20*np.log10(np.abs(y).max()/np.sqrt((y**2).mean())))
    sep=np.mean([np.sqrt(((a-b)**2).mean()) for a,b in itertools.combinations(envs,2)])
    return dict(rms=np.mean(rms),cen=np.mean(cen),crest=np.mean(crest),sep=sep)
def henv(y,sr,f0):
    w=y*np.hanning(len(y));N=1<<15;S=np.abs(np.fft.rfft(w,N))+1e-9;f=np.fft.rfftfreq(N,1/sr)
    hs=np.arange(1,int(4000/f0)+1)*f0;amps=[]
    for h in hs:
        m=(f>h*0.94)&(f<h*1.06);amps.append(20*np.log10(S[m].max()))
    grid=np.linspace(100,4000,200);e=np.interp(grid,hs,amps)
    return e-e.max()
def clarity(voice,pn,pre='',vowels=('iy','eh','aa','ow','uw'),mod=None,f0mul=1.0):
    f0=440*2**((pn+35-69)/12)*f0mul;envs=[]
    for v in vowels:
        vv=mod(v) if mod else v
        x,sr=dt.r(f'[:phoneme on][:{voice}]{pre}[{vv}<500,{pn}>]');envs.append(henv(seg(x,sr),sr,f0))
    return np.mean([np.sqrt(((a-b)**2).mean()) for a,b in itertools.combinations(envs,2)])
def lowm(voice,pn,pre=''):
    f0=440*2**((pn+35-69)/12);envs=[];cr=[];rm=[];cen=[]
    for v in ('iy','eh','aa','ow','uw'):
        x,sr=dt.r(f'[:phoneme on][:{voice}]{pre}[{v}<500,{pn}>]');y=seg(x,sr);envs.append(henv(y,sr,f0))
        cr.append(20*np.log10(np.abs(y).max()/np.sqrt((y**2).mean())));rm.append(20*np.log10(np.sqrt((y**2).mean())))
        S=np.abs(np.fft.rfft(y*np.hanning(len(y))));f=np.fft.rfftfreq(len(y),1/sr);cen.append((S*f).sum()/S.sum())
    cl=np.mean([np.sqrt(((a-b)**2).mean()) for a,b in itertools.combinations(envs,2)])
    return f'crest {np.mean(cr):4.1f} rms {np.mean(rm):5.1f} cen {np.mean(cen):4.0f} clar {cl:4.1f}'
