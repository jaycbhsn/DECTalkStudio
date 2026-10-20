#!/usr/bin/env bash
# Builds DECtalk with its own Linux build, which generates the US English dictionary
# (dist/dic/dtalk_us.dic) and the headers the cross-compiles below need.
# Needs: gcc, make, autoconf, automake, libtool.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DECTALK="${DECTALK_DIR:-$ROOT/third_party/dectalk}"
if [ ! -f "$DECTALK/src/autogen.sh" ]; then
  echo "DECtalk source not found at $DECTALK. Run: git submodule update --init" >&2; exit 1
fi
cd "$DECTALK/src"
./autogen.sh
./configure
make -j"$(nproc)"
test -f "$DECTALK/dist/dic/dtalk_us.dic" && echo "DECtalk built: $DECTALK/dist"
