from dt import *
import json
D={'np':(100,122),'nb':(100,208),'nh':(115,89),'nf':(90,155),'nd':(100,110),'nk':(77,296),'nu':(95,240),'nr':(95,106),'nw':(100,200)}
out={}
for v,(hs,ap) in D.items():
    for pn in [29,33,37]:
        f0=440*2**((pn+35-69)/12);exc=np.log2(f0/ap)
        r={f:clarity(v,pn,pre=f'[:dv hs {round(hs*f)}]') for f in [1.0,.94,.88,.82]}
        best=max(r,key=r.get)
        print(f'{v} midi{pn+35} oct_above_ap {exc:4.2f} '+' '.join(f'{k}:{x:.1f}' for k,x in r.items())+f'  best {best}',flush=True)
