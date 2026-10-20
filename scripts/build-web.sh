#!/usr/bin/env bash
# Builds the web version: DECtalk compiled to WebAssembly, its threads turned into green threads
# (web/fiber.c + Binaryen Asyncify), embedded with the dictionary into one HTML file: dist/dectalk-studio.html
# Needs: zig 0.13 exactly (newer clang crashes on DECtalk's synthesizer; set ZIG13, default "python3 -m ziglang"
# after `pip install ziglang==0.13.0`), Node.js for wasm-opt (or set WASM_OPT), and scripts/build-dectalk.sh done.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DECTALK="${DECTALK_DIR:-$ROOT/third_party/dectalk}"
read -ra Z <<< "${ZIG13:-python3 -m ziglang}"
read -ra WASM_OPT <<< "${WASM_OPT:-npx --yes -p binaryen@116.0.0 wasm-opt}"
ver="$("${Z[@]}" version)"; case "$ver" in 0.13.*) ;; *) echo "warning: zig $ver; the web build is tested with 0.13 (newer versions crash on DECtalk)" >&2;; esac
cd "$ROOT"; mkdir -p build dist
FLAGS=(-target wasm32-wasi -D__linux__ -D__unix__ -D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_MMAN
       -DPATH_MAX=4096 -DENOSR=63 -include "$ROOT/web/fb.h" -I"$DECTALK/src/dapi/src")
python3 scripts/xbuild.py web/objs_web.json build/obj-wasm --extra web/dtweb.c=ttsapi_mme.o --extra web/audio_stub.c=playaud.o -- "${Z[@]}" cc "${FLAGS[@]}"
"${Z[@]}" cc -target wasm32-wasi -O2 -c web/fiber.c -o build/obj-wasm/fiber.o
"${Z[@]}" cc -target wasm32-wasi -mexec-model=reactor -O2 build/obj-wasm/*.o -o build/dectalk.raw.wasm \
  -lwasi-emulated-signal -lwasi-emulated-process-clocks -Wl,--export=malloc -Wl,--export=free \
  -Wl,--export=__stack_pointer -Wl,--export-table -Wl,-z,stack-size=1048576 -Wl,--strip-all
"${WASM_OPT[@]}" build/dectalk.raw.wasm --asyncify --pass-arg=asyncify-imports@env.fb_yield,env.fb_exit -O3 --strip-debug -o build/dectalk.wasm
gzip -9 -n -c build/dectalk.wasm > build/dectalk.wasm.gz
gzip -9 -n -c "$DECTALK/dist/dic/dtalk_us.dic" > build/dic.gz
grep -E '^(licenses|licensepassword|US_dict|US_udict|Default_lang|LANG:us)' "$DECTALK/dist/DECtalk.conf" > build/DECtalk.conf
python3 web/build_page.py dist/dectalk-studio.html
