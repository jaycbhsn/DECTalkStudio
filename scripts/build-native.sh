#!/usr/bin/env bash
# Cross-compiles the DECtalk render server (engine/dtserver.c + DECtalk) as static Linux executables
# for Android's three common processor types, and copies DECtalk's dictionary into the app.
# Needs: zig (pip install ziglang==0.13.0 works; set ZIG to override), and scripts/build-dectalk.sh done.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DECTALK="${DECTALK_DIR:-$ROOT/third_party/dectalk}"
if [ -n "${ZIG:-}" ]; then read -ra ZIGCMD <<< "$ZIG"; elif command -v zig >/dev/null; then ZIGCMD=(zig); else ZIGCMD=(python3 -m ziglang); fi
cd "$ROOT"
for pair in "aarch64-linux-musl arm64-v8a" "arm-linux-musleabihf armeabi-v7a" "x86_64-linux-musl x86_64"; do
  set -- $pair
  python3 scripts/xbuild.py engine/objs.json "build/obj-$1" --extra engine/dtserver.c=ttsapi_mme.o -- "${ZIGCMD[@]}" cc -target "$1"
  mkdir -p "android/lib/$2"
  "${ZIGCMD[@]}" cc -target "$1" -static -s build/obj-$1/*.o -o "android/lib/$2/libdtserver.so" -lm
  echo "built android/lib/$2/libdtserver.so"
done
mkdir -p android/assets/dectalk/dic
cp "$DECTALK/dist/dic/dtalk_us.dic" android/assets/dectalk/dic/
grep -E '^(licenses|licensepassword|US_dict|US_udict|Default_lang|LANG:us)' "$DECTALK/dist/DECtalk.conf" > android/assets/dectalk/DECtalk.conf
echo "copied dictionary and DECtalk.conf into android/assets/dectalk"
