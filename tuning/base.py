from dt import *
for v in ['np','nb','nh','nk']:
    print(v)
    for pn in [1,4,7,13,19,25,29,33,37]:
        m=measure(v,pn);print(f'  pn{pn:2d} midi{pn+35} rms {m["rms"]:6.1f} cen {m["cen"]:5.0f} crest {m["crest"]:5.1f} clarity {m["sep"]:5.2f}')
