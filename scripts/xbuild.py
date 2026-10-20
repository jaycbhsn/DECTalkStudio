#!/usr/bin/env python3
"""Compiles DECtalk's US English engine (the same objects its own Linux build links into libtts_us.so)
plus extra C files, in parallel, with any compiler command.

usage: xbuild.py OBJS_JSON OUT_DIR [--extra FILE.c=FLAGS_FROM.o ...] [--] CC [CC args ...]

OBJS_JSON lists each object with its source and DECtalk's own -D/-I flags; {DECTALK} is the DECtalk
checkout (env DECTALK_DIR) and {DICBUILD} its generated dictionary headers (made by DECtalk's `make`).
An --extra file is compiled with the flags of the named DECtalk object."""
import glob, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dectalk = os.path.abspath(os.environ.get('DECTALK_DIR', os.path.join(root, 'third_party', 'dectalk')))
args = sys.argv[1:]
objs_json, out = args[0], args[1]
args = args[2:]
extras = []
while args and args[0] == '--extra':
    extras.append(args[1].split('=')); args = args[2:]
if args and args[0] == '--': args = args[1:]
cc = args
dic = glob.glob(os.path.join(dectalk, 'src/dapi/build/dic/*/us/release'))
if not dic:
    sys.exit(f'No generated dictionary headers under {dectalk}/src/dapi/build/dic: run scripts/build-dectalk.sh first.')
sub = lambda s: s.replace('{DECTALK}', dectalk).replace('{DICBUILD}', os.path.dirname(os.path.dirname(dic[0])))
objs = [(o, sub(src), [sub(f) for f in fl]) for o, src, fl in json.load(open(objs_json))]
flags_of = {o: fl for o, _, fl in objs}
items = objs + [(os.path.splitext(os.path.basename(f))[0] + '.o', os.path.abspath(f), flags_of[ref]) for f, ref in extras]
os.makedirs(out, exist_ok=True)
base = ['-c', '-O2', '-w', '-fcommon', '-std=gnu89', '-fno-strict-aliasing', '-DDEC']
def comp(it):
    o, src, fl = it
    r = subprocess.run(cc + base + fl + [src, '-o', os.path.join(out, o)], capture_output=True, text=True, errors='replace')
    return o, r.returncode, r.stderr[-1500:]
failed = 0
with ThreadPoolExecutor(os.cpu_count() or 4) as ex:
    for o, rc, err in ex.map(comp, items):
        if rc: failed += 1; print('FAILED', o, err, file=sys.stderr)
if failed: sys.exit(f'{failed} file(s) failed to compile')
print(f'compiled {len(items)} files into {out}')
