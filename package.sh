#!/bin/sh
# Packages the build (./build-deps.sh, ./build.sh) into output/<id>_<version>_all.ipk, in the layout
# ares-package produces. The app folder holds:
# - domino-chain, the game (appinfo.json's main), with its rpath on lib/;
# - lib/: webosbrew's SDL 2.30.12, SDL2_mixer, SDL2_ttf, and the toolchain's libstdc++ and libgcc_s
#   (the TV's libstdc++ is GCC 8's);
# - data/: the game's data as its Makefile installs it: the images, with the ant (art/figure.png)
#   for the figure and the dominoes, which POV-Ray renders, from Debian's domino-chain 1.1 package
#   (the same scene); the sounds, themes, levels and translations; and GNU FreeFont's FreeSans, the
#   font it uses;
# - home/: the profiles and levels solved.
set -e
cd "$(dirname "$0")"
TOP=$PWD
T=${WEBOS_TOOLCHAIN:-$TOP/toolchain/arm-webos-linux-gnueabi_sdk-buildroot}
TC=$T/bin/arm-webos-linux-gnueabi
SYSROOT=$T/arm-webos-linux-gnueabi/sysroot
P=$TOP/prefix
DL=$TOP/downloads
SRC=dc-src/src
export TMPDIR=$TOP/build/tmp
mkdir -p "$TMPDIR" "$DL"
ID=$(sed -n 's/.*"id": *"\([^"]*\)".*/\1/p' app/appinfo.json)
VER=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' app/appinfo.json)

fetch() { # url sha256
	f=$DL/$(basename "$1")
	[ -f "$f" ] || curl -fL -o "$f" "$1"
	echo "$2  $f" | sha256sum -c - >/dev/null || { echo "checksum mismatch: $f" >&2; exit 1; }
	echo "$f"
}
DEB=$(fetch http://deb.debian.org/debian/pool/main/p/pushover/domino-chain_1.1-6_amd64.deb \
	2a24bf5ce030436b98445c79a91c50330773f50fdf1a878d8b1da41428ec15bb)
FONT=$(fetch https://ftp.gnu.org/gnu/freefont/freefont-ttf-20120503.zip \
	7c85baf1bf82a1a1845d1322112bc6ca982221b484e3b3925022e25b5cae89af)

W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
D=$W/data/usr/palm/applications/$ID
G=$D/data/domino-chain
mkdir -p "$D/lib" "$G/images" "$G/sounds" "$G/themes" "$G/levels" "$D/data/fonts" "$W/data/usr/palm/packages/$ID" "$W/control"
cp app/appinfo.json app/icon.png app/largeIcon.png "$D/"
# The game runs as its own user, and the app folder is root's: home/ holds the profiles, so anyone
# may write it.
mkdir -p "$D/home"
chmod 777 "$D/home"
cp dc-src/LICENSE "$D/COPYING"
cp dc-src/AUTHORS "$D/AUTHORS"
cp build/domino-chain "$D/"
for l in libSDL2-2.0.so.0 libSDL2_mixer-2.0.so.0 libSDL2_ttf-2.0.so.0; do
	cp -L "$P/lib/$l" "$D/lib/"
done
cp -L "$SYSROOT/usr/lib/libstdc++.so.6" "$SYSROOT/lib/libgcc_s.so.1" "$D/lib/"

# the data, as the Makefile builds it
cp $SRC/images/*.png "$G/images/"
# the figure is the ant (tools/ant/make.py redraws the stick figure's frames into art/figure.png)
cp art/figure.png "$G/images/figure.png"
(mkdir -p "$W/deb" && cd "$W/deb" && ar x "$DEB" && tar -xf data.tar.* ./usr/share/games/domino-chain/images/dominoes.png)
cp "$W/deb/usr/share/games/domino-chain/images/dominoes.png" "$G/images/"
cp $SRC/sounds/*.ogg "$G/sounds/"
cp $SRC/themes/* "$G/themes/"
for d in $SRC/levels/*/; do
	n=$(basename "$d")
	cat "$d"*.level | gzip -9n > "$G/levels/$n.gz"
done
for po in $SRC/po/*.po; do
	l=$(basename "$po" .po)
	mkdir -p "$D/data/locale/$l/LC_MESSAGES"
	msgfmt -c -o "$D/data/locale/$l/LC_MESSAGES/domino-chain.mo" "$po"
done
unzip -q -j -o "$FONT" freefont-20120503/FreeSans.ttf freefont-20120503/COPYING -d "$W/font"
cp "$W/font/FreeSans.ttf" "$D/data/fonts/"
cp "$W/font/COPYING" "$D/data/fonts/COPYING"

find "$D" -type f \( -name '*.so*' -o -name domino-chain \) | while read -r f; do
	"$TC-strip" --strip-unneeded "$f"
	chmod 755 "$f"
done

# every symbol the binaries use must be defined in lib/ or on the TV: an older library of the
# same name may lack one. Needs a copy of the TV's libraries in TV_ROOT (its /lib, /usr/lib and
# /etc/ld.so.conf with the folders it names: tools/fetch-tv-libs.sh root@<tv>); skipped without one.
R=${TV_ROOT:-build/tv-root}
if [ -d "$R" ]; then
	python3 tools/check-symbols.py "$TC-readelf" "$D" "$R"
fi

printf '{\n  "id": "%s",\n  "version": "%s",\n  "app": "%s"\n}\n' "$ID" "$VER" "$ID" > "$W/data/usr/palm/packages/$ID/packageinfo.json"
SIZE=$(du -sb "$W/data" | cut -f1)
cat > "$W/control/control" <<CTL
Package: $ID
Version: $VER
Section: misc
Priority: optional
Architecture: all
Installed-Size: $SIZE
Maintainer: N/A <nobody@example.com>
Description: This is a webOS application.
webOS-Package-Format-Version: 2
webOS-Packager-Version: x.y.x
CTL
printf '2.0\n' > "$W/debian-binary"
(cd "$W/control" && tar --owner=0 --group=0 -czf ../control.tar.gz control)
(cd "$W/data" && tar --owner=0 --group=0 -czf ../data.tar.gz usr)
mkdir -p output
OUT=output/${ID}_${VER}_all.ipk
rm -f "$OUT"
# webOS rejects GNU ar output (error -5), so write the ar container as ares-package does.
python3 - "$OUT" "$W/debian-binary" "$W/control.tar.gz" "$W/data.tar.gz" <<'PY'
import os, sys, time
out = open(sys.argv[1], 'wb'); out.write(b'!<arch>\n')
for p in sys.argv[2:]:
    data = open(p, 'rb').read()
    hdr = '%-16s%-12d%-6d%-6d%-8s%-10d`\n' % (os.path.basename(p), int(time.time()), 0, 0, '100644', len(data))
    out.write(hdr.encode()); out.write(data)
    if len(data) % 2: out.write(b'\n')
out.close()
PY
# The Homebrew Channel manifest; the release publishes it next to the IPK.
python3 - "$OUT" app/appinfo.json "output/$ID.manifest.json" <<'PY'
import hashlib, json, os, sys
ipk, info, out = sys.argv[1:]
a = json.load(open(info))
m = {
    "id": a["id"], "version": a["version"], "type": a["type"], "title": a["title"],
    "appDescription": "A puzzle game: set up the dominoes so that one push topples them all",
    "iconUri": "https://raw.githubusercontent.com/pulpoff/webos-domino-chain/main/app/largeIcon.png",
    "sourceUrl": "https://github.com/pulpoff/webos-domino-chain",
    "rootRequired": False,
    "ipkUrl": os.path.basename(ipk),
    "ipkHash": {"sha256": hashlib.sha256(open(ipk, "rb").read()).hexdigest()},
}
json.dump(m, open(out, "w"), indent=2); open(out, "a").write("\n")
PY
echo "installed size: $((SIZE / 1048576)) MB"
ls -la "$OUT" "output/$ID.manifest.json"
