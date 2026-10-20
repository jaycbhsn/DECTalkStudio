#!/bin/bash
set -e
cd "$(dirname "$0")"
SDK=/usr/lib/android-sdk; JAR=$SDK/platforms/android-23/android.jar
rm -rf build && mkdir -p build/gen build/classes
aapt package -f -m -J build/gen -M AndroidManifest.xml -S res -I $JAR
javac --release 8 -nowarn -cp $JAR -d build/classes $(find src build/gen -name '*.java') 2>&1 | grep -v "^warning\|bootstrap\|^1 warning" || true
dalvik-exchange --dex --min-sdk-version=23 --output=build/classes.dex build/classes
aapt package -f -M AndroidManifest.xml -S res -A assets -I $JAR -F build/unsigned.apk
cd build && aapt add unsigned.apk classes.dex >/dev/null
cp -r ../lib . && for f in lib/*/libdtserver.so; do aapt add unsigned.apk $f >/dev/null; done; cd ..
zipalign -f -p 4 build/unsigned.apk build/aligned.apk
[ -f release.keystore ] || keytool -genkeypair -keystore release.keystore -storepass dectalk -keypass dectalk -alias dectalk -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=DECtalk Studio" >/dev/null 2>&1
apksigner sign --ks release.keystore --ks-pass pass:dectalk --key-pass pass:dectalk --ks-key-alias dectalk --out DECtalkStudio.apk build/aligned.apk
apksigner verify --verbose DECtalkStudio.apk | head -5
ls -la DECtalkStudio.apk
