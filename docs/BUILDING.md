# Pinned source and artifact preparation

The first release uses the **qualified b76fe98 runtime**, not the newer upstream
API adaptation under review. The latter has host validation and still needs PS5
requalification. Keep those identities separate.

| Component | Source |
|---|---|
| Native YARG host and hot-subpage ntdll | `Gudui/prospero-win` commit `b76fe98a0635cea79064c7a2942f14452bcbb1c3` |
| Paired XInput PRX and PE DLLs | same fork, `9a67d5e60dbbd43c269cfb14031c0234b5bcb8b4`; sink source is unchanged in b76fe98 |
| Base runtime | official prospero-win v0.3.0, commit `404cac6ebbb236d2486d2796fd28b9bd39f2caa6` |
| Wine | `490f6d5dcbb2a5047345b8af88d114bbcaad69a8` plus the pinned fork's patches |
| Title foundation | `9c0b994a048521af6fb84c73ded364504fe250e9` |
| Module foundation | `30597512539e7edfde079cbcaf4a626bc0a948c5` |

## Host Wine for prefix preparation

Run these at a Linux prompt (on Windows, enter `wsl.exe -d Ubuntu -u root`
from PowerShell first). The following uses root-owned Linux directories, so no
Windows-checkout safe-directory exception is needed. Install the standard Wine
build prerequisites for your distribution first; use prospero-win's
`docs/WINE_PS5_BUILD.md` and `tools/build_host_wine.sh` for its requirements.

```bash
mkdir -p /root/src
git clone https://github.com/Gudui/prospero-win /root/src/prospero-win-yarg
git -C /root/src/prospero-win-yarg checkout --detach b76fe98a0635cea79064c7a2942f14452bcbb1c3
git init /root/src/wine-yarg
git -C /root/src/wine-yarg remote add origin https://gitlab.winehq.org/wine/wine.git
git -C /root/src/wine-yarg fetch --depth 1 origin 490f6d5dcbb2a5047345b8af88d114bbcaad69a8
git -C /root/src/wine-yarg checkout --detach FETCH_HEAD
cd /root/src/prospero-win-yarg
tools/build_host_wine.sh --source /root/src/wine-yarg --work .deps/wine-host --jobs 8
```

The executable is `.deps/wine-host/install/usr/bin/wine`. Leave root WSL with
`exit` to return to Windows PowerShell. This is host-only work, not a console launch.

## Reproducing native/runtime artifacts

Use the source commits above and the public PS5 Payload SDK/foundations pinned
by their build scripts. The qualified builds used Clang 18.1.8 for the native
title, SDK LLVM 21.1.8 for Wine, and the retained title-specific Lapy helper:

```text
lapy.elf SHA-256: 5525c1deb7ffe70a3462a1aba3cf586c6ac0828d04af869b80466e22a69dc0e3
target title: PPSA99400
protocol SHA-256: bb02c4aa814eaba7a7a423a31b29ff41f786212c2953678cf29434e85fa0f869
```

The MIT helper is the same owned PPSA99400 artifact validated in the hardware
runs, not the stock PPSA99995 helper. Its source lineage is retained in
`SOURCES.txt` and the linked campaign scripts below. Do not substitute a helper
for another title or claim a fresh build is target-qualified from hashes alone.

Native build options:

```text
PW_TITLE_ID=PPSA99400 PW_TITLE_NAME=YARG PW_FIXED_PROFILE=yarg
PW_HOME_EXIT_LOADEXEC=1 PW_USB360_CAPTURE=0
PW_FOUNDATION_READY=1 PS5_NATIVE_FOUNDATION=<pinned prepared foundation>
PW_LAPY_HELPER_DIR=<verified PPSA99400 helper and manifest>
PW_LAPY_ELF_SHA256=5525c1deb7ffe70a3462a1aba3cf586c6ac0828d04af869b80466e22a69dc0e3
```

Build with the fork's `tools/build_native.sh`; build Wine modules with
`tools/build_wine_ps5.sh`, the pinned Wine and prepared title/module foundations.
No generic graphics or SDK change belongs in this wrapper.

The exact campaign build commands and identities are preserved in
[GuitarHeroPs5](https://github.com/Gudui/GuitarHeroPs5), notably
`tools/build_guitar_xinput_runtime.sh`, `tools/build_guitar_usb_read.sh`,
`tools/stage_guitar_xinput_api.py` and `tools/stage_guitar_hot_subpage.py`.

`tools/build_overlay.py` packages those already built, manifest-checked artifacts.
It verifies both campaign manifests and the native/helper hashes, overlays the
exact qualified files, extracts SELF integrity with the pinned native tool, and
produces a deterministic ZIP. It does not rebuild or contact a console:

```bash
python3 tools/build_overlay.py \
  --baseline /path/to/verified-v030-YARG-title \
  --native /path/to/b76fe98/dist/PPSA99400 \
  --stagec /path/to/verified-stagec-package \
  --fix /path/to/verified-hot-subpage-package \
  --self-tool /path/to/pinned/ps5-native-tool \
  --output build/yarg-ps5-overlay-v0.1.0.zip
```

The release's source archive and upstream `LICENSES/` records accompany the
binary overlay. Official YARG and the base runtime are downloaded from their
original releases, rather than republished by this repository.
