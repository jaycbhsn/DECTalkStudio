import json,subprocess,sys,os
from concurrent.futures import ThreadPoolExecutor
cc=sys.argv[1].split(); outdir=sys.argv[2]; os.makedirs(outdir,exist_ok=True)
objs=json.load(open('/home/claude/engine/objs.json'))
api=[k for k in objs if k[0]=='ttsapi_mme.o'][0][2]
def comp(item):
    o,src,flags=item
    r=subprocess.run(cc+['-c','-O2','-w','-fcommon','-std=gnu89','-fno-strict-aliasing','-DDEC']+flags+[src,'-o',f'{outdir}/{o}'],capture_output=True,text=True,errors='replace')
    return o,r.returncode,r.stderr[-1500:]
items=objs+[('dtserver.o','/home/claude/engine/dtserver.c',api)]
with ThreadPoolExecutor(16) as ex:
    for o,rc,err in ex.map(comp,items):
        if rc: print('FAIL',o,err)
print('done')
