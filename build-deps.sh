#!/bin/sh
# Cross-compiles what Domino-Chain needs that webOS lacks into prefix/, for 32-bit ARM (Cortex-A55,
# softfp, like webOS's userland). libpng16, zlib and freetype the TV has, and the toolchain's sysroot.
# - SDL 2.30.12 for webOS (webosbrew's build, the one RetroArch and ioquake3 ship), unpacked as is;
# - SDL2_mixer 2.8.0 (Ogg Vorbis through stb_vorbis) and SDL2_ttf 2.22.0, shared;
# - Lua 5.4.7 and FriBidi 1.0.16, static.
# On the first run it downloads the openlgtv webOS toolchain into toolchain/.
set -e
cd "$(dirname "$0")"
TOP=$PWD
T=${WEBOS_TOOLCHAIN:-$TOP/toolchain/arm-webos-linux-gnueabi_sdk-buildroot}
TC_URL=https://github.com/openlgtv/buildroot-nc4/releases/download/2026.08-webos/arm-webos-linux-gnueabi_sdk-buildroot-x86_64.tar.gz
# the openlgtv webOS toolchain, downloaded on the first run
if [ ! -x "$T/bin/cmake" ]; then
	mkdir -p toolchain
	curl -fL "$TC_URL" | tar -xz -C toolchain
	"$T/relocate-sdk.sh"
fi
TC=$T/bin/arm-webos-linux-gnueabi
P=$TOP/prefix
B=$TOP/build/deps
D=$TOP/downloads
export TMPDIR=$TOP/build/tmp
mkdir -p "$P/lib" "$P/include" "$B" "$D" "$TMPDIR"
ARCH="-mcpu=cortex-a55 -mfpu=neon-fp-armv8 -mfloat-abi=softfp"
CF="$ARCH -O2 -fPIC"
J=$(nproc)

fetch() { # url sha256
	f=$D/$(basename "$1")
	[ -f "$f" ] || curl -fL -o "$f" "$1"
	echo "$2  $f" | sha256sum -c - >/dev/null || { echo "checksum mismatch: $f" >&2; exit 1; }
	echo "$f"
}
unpack() { # tarball dir
	rm -rf "$B/$2"; mkdir -p "$B/$2"; tar -xf "$1" -C "$B/$2" --strip-components=1
}
cm() { # srcdir builddir [cmake args...]
	s=$1 b=$2; shift 2
	"$T/bin/cmake" -S "$s" -B "$b" -DCMAKE_TOOLCHAIN_FILE="$T/share/buildroot/toolchainfile.cmake" \
		-DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$P" -DCMAKE_PREFIX_PATH="$P" \
		-DCMAKE_C_FLAGS="$CF" -DCMAKE_CXX_FLAGS="$CF" "$@" >"$b.log" 2>&1 || { tail -30 "$b.log"; exit 1; }
	"$T/bin/cmake" --build "$b" -j"$J" >>"$b.log" 2>&1 || { tail -30 "$b.log"; exit 1; }
	"$T/bin/cmake" --install "$b" >>"$b.log" 2>&1
}
step() { [ -f "$B/.done-$1" ] && { echo "= $1 (done)"; return 1; }; echo "= $1"; }
done_() { touch "$B/.done-$1"; }

if step sdl2; then
	f=$(fetch https://github.com/webosbrew/SDL-webOS/releases/download/release-2.30.12-webos.1/SDL2-2.30.12-webos-abi.tar.gz \
		b43c05b26c0a0431a2b26a9b7036a24d8a34989441aeb87dd2825c1b50cbe83b)
	tar -xzf "$f" -C "$P"
	# its config points at the build machine's prefix; make it point where it now lies
	sed -i "s|^prefix=.*|prefix=$P|" "$P/lib/pkgconfig/sdl2.pc"
	done_ sdl2
fi
if step sdl2_mixer; then
	f=$(fetch https://github.com/libsdl-org/SDL_mixer/releases/download/release-2.8.0/SDL2_mixer-2.8.0.tar.gz \
		1cfb34c87b26dbdbc7afd68c4f545c0116ab5f90bbfecc5aebe2a9cb4bb31549)
	unpack "$f" sdl2_mixer
	cm "$B/sdl2_mixer" "$B/sdl2_mixer-build" -DBUILD_SHARED_LIBS=ON -DSDL2MIXER_VENDORED=OFF -DSDL2MIXER_SAMPLES=OFF \
		-DSDL2MIXER_VORBIS=STB -DSDL2MIXER_OPUS=OFF -DSDL2MIXER_FLAC=OFF -DSDL2MIXER_MOD=OFF -DSDL2MIXER_MIDI=OFF \
		-DSDL2MIXER_MP3=OFF -DSDL2MIXER_WAVPACK=OFF -DSDL2MIXER_GME=OFF -DSDL2MIXER_CMD=OFF -DSDL2MIXER_WAVE=ON
	done_ sdl2_mixer
fi
if step sdl2_ttf; then
	f=$(fetch https://github.com/libsdl-org/SDL_ttf/releases/download/release-2.22.0/SDL2_ttf-2.22.0.tar.gz \
		d48cbd1ce475b9e178206bf3b72d56b66d84d44f64ac05803328396234d67723)
	unpack "$f" sdl2_ttf
	cm "$B/sdl2_ttf" "$B/sdl2_ttf-build" -DBUILD_SHARED_LIBS=ON -DSDL2TTF_VENDORED=OFF -DSDL2TTF_SAMPLES=OFF \
		-DSDL2TTF_HARFBUZZ=OFF -DSDL2TTF_PLUTOSVG=OFF
	done_ sdl2_ttf
fi
if step lua; then
	f=$(fetch https://www.lua.org/ftp/lua-5.4.7.tar.gz 9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30)
	unpack "$f" lua
	make -C "$B/lua/src" -j"$J" liblua.a CC="$TC-gcc" AR="$TC-ar rcu" RANLIB="$TC-ranlib" \
		MYCFLAGS="$CF -DLUA_USE_LINUX" >"$B/lua.log" 2>&1 || { tail -30 "$B/lua.log"; exit 1; }
	cp "$B/lua/src/liblua.a" "$P/lib/"
	cp "$B/lua/src/lua.h" "$B/lua/src/luaconf.h" "$B/lua/src/lualib.h" "$B/lua/src/lauxlib.h" "$B/lua/src/lua.hpp" "$P/include/"
	mkdir -p "$P/lib/pkgconfig"
	printf 'prefix=%s\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\n\nName: Lua\nDescription: Lua\nVersion: 5.4.7\nLibs: -L${libdir} -llua -lm\nCflags: -I${includedir}\n' "$P" > "$P/lib/pkgconfig/lua.pc"
	done_ lua
fi
if step fribidi; then
	f=$(fetch https://github.com/fribidi/fribidi/releases/download/v1.0.16/fribidi-1.0.16.tar.xz \
		1b1cde5b235d40479e91be2f0e88a309e3214c8ab470ec8a2744d82a5a9ea05c)
	unpack "$f" fribidi
	# its generated tables come from programs built for the build machine (CC_FOR_BUILD)
	(cd "$B/fribidi" &&
		PATH="$T/bin:$PATH" ./configure --host=arm-webos-linux-gnueabi --prefix="$P" --disable-shared --enable-static \
			--disable-docs CC="$TC-gcc" CFLAGS="$CF" CC_FOR_BUILD=gcc >"$B/fribidi.log" 2>&1 &&
		PATH="$T/bin:$PATH" make -j"$J" >>"$B/fribidi.log" 2>&1 && PATH="$T/bin:$PATH" make install >>"$B/fribidi.log" 2>&1) ||
		{ tail -30 "$B/fribidi.log"; exit 1; }
	done_ fribidi
fi
echo "deps in $P"
