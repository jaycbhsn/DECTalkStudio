#!/usr/bin/env bash
# Builds and signs the Android app: dist/DECtalkStudio.apk
# Needs (Ubuntu/Debian): android-sdk-platform-23 aapt zipalign apksigner dalvik-exchange, a JDK,
# and scripts/build-native.sh done (it puts the engine in lib/ and the dictionary in assets/dectalk/).
# Signing: uses $KEYSTORE (default android/release.keystore, created on first run) with
# $KEYSTORE_PASS (default "dectalk"; set your own). Keep the keystore safe and out of git:
# Android only installs an update over an existing copy if it's signed with the same key.
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_SDK:-/usr/lib/android-sdk}"; JAR="$SDK/platforms/android-23/android.jar"
KEYSTORE="${KEYSTORE:-release.keystore}"; PASS="${KEYSTORE_PASS:-dectalk}"
for f in lib/arm64-v8a/libdtserver.so assets/dectalk/dic/dtalk_us.dic; do
  [ -f "$f" ] || { echo "Missing android/$f: run scripts/build-native.sh first" >&2; exit 1; }
done
rm -rf build && mkdir -p build/gen build/classes ../dist
aapt package -f -m -J build/gen -M AndroidManifest.xml -S res -I "$JAR"
javac --release 8 -nowarn -cp "$JAR" -d build/classes $(find src build/gen -name '*.java') 2>&1 | grep -v "^warning\|bootstrap\|^1 warning" || true
dalvik-exchange --dex --min-sdk-version=23 --output=build/classes.dex build/classes
aapt package -f -M AndroidManifest.xml -S res -A assets -I "$JAR" -F build/unsigned.apk
(cd build && aapt add unsigned.apk classes.dex >/dev/null && cp -r ../lib . && for f in lib/*/libdtserver.so; do aapt add unsigned.apk "$f" >/dev/null; done)
zipalign -f -p 4 build/unsigned.apk build/aligned.apk
if [ ! -f "$KEYSTORE" ]; then
  echo "Creating a new signing key: $KEYSTORE"
  keytool -genkeypair -keystore "$KEYSTORE" -storepass "$PASS" -keypass "$PASS" -alias dectalk -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=DECtalk Studio" >/dev/null 2>&1
fi
apksigner sign --ks "$KEYSTORE" --ks-pass "pass:$PASS" --key-pass "pass:$PASS" --ks-key-alias dectalk --out ../dist/DECtalkStudio.apk build/aligned.apk
apksigner verify ../dist/DECtalkStudio.apk && echo "built dist/DECtalkStudio.apk"
