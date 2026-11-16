#!/bin/sh
# Builds Domino-Chain for webOS into build/domino-chain, against the libraries in prefix/
# (./build-deps.sh first). On the first run it clones Domino-Chain into dc-src/ at the pinned
# commit, with patches/domino-chain-webos.patch applied. Run ./package.sh afterwards.
set -e
cd "$(dirname "$0")"
TOP=$PWD
DC_COMMIT=16826d3ec2b2df78ad46b76b2b6e6a0d2175c417
T=${WEBOS_TOOLCHAIN:-$TOP/toolchain/arm-webos-linux-gnueabi_sdk-buildroot}
if [ ! -d dc-src/.git ]; then
	git clone https://gitlab.com/domino-chain/domino-chain.gitlab.io.git dc-src
	git -C dc-src checkout -q "$DC_COMMIT"
	git -C dc-src apply ../patches/domino-chain-webos.patch
fi
TC=$T/bin/arm-webos-linux-gnueabi
P=$TOP/prefix
S=dc-src/src/domino-chain
O=build/obj
export TMPDIR=$TOP/build/tmp
mkdir -p "$O" "$TMPDIR"
J=$(nproc)

CXXFLAGS="-mcpu=cortex-a55 -mfpu=neon-fp-armv8 -mfloat-abi=softfp -O2 -funwind-tables -std=c++17 -Wall -Wextra -Wno-unused-parameter
	-DWEBOS -D_REENTRANT -DVERSION=\"$(cat dc-src/src/version)\" -DDATADIR=\"data\"
	-I$P/include -I$P/include/SDL2 -I$P/include/fribidi"
LIBS="-L$P/lib -lSDL2_ttf -lSDL2_mixer -lSDL2 -llua -lfribidi -lpng16 -lz -lm -ldl"

# the sources, as the Makefile has them (its C files too are C++), compiled when newer than their
# object or older than a header
export TC CXXFLAGS O S
ls $S/*.cpp $S/linebreak/*.c $S/sha1/*.cpp | xargs -P"$J" -n1 sh -c '
	o=$O/$(echo "${1#$S/}" | tr / _).o
	if [ ! -f "$o" ] || [ "$1" -nt "$o" ] || [ -n "$(find $S -name "*.h" -newer "$o" | head -1)" ]; then
		echo "  $1"
		$TC-g++ $CXXFLAGS -c -o "$o" "$1" || exit 255
	fi' sh
"$TC-g++" -o build/domino-chain $O/*.o $LIBS -Wl,-rpath,'$ORIGIN/lib' -Wl,--as-needed
echo "built: build/domino-chain"
