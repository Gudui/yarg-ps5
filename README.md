# YARG PS5 tile installer

Prepare a **YARG Home-screen tile** with its own prospero-win runtime. YARG stays
the official, unmodified Windows build. This repository owns installation and
packaging; generic input/runtime changes live in prospero-win.

The pinned runtime includes wired Xbox 360 X-plorer support and Wine's upstream
hot-subpage fix. The runtime/title candidate was tested on **PS5 firmware 5.50**:
stable YARG menu, DualSense and X-plorer input, USB hotplug and Home return.
The installer itself has host tests; its fresh-install path still needs a PS5
qualification. Other firmware and guitar models are not qualified.

## What gets installed

- `PPSA99400`: YARG tile, title-specific helper and private prospero-win runtime.
- `/data/prospero-win/prefixes/yarg`: fresh Wine prefix, official YARG v0.15.0,
  DXVK 2.6.2 and ordinary DualSense profile/bindings.
- `/data/prospero-win/profiles/yarg.profile`: D3D11/XInput launch settings.

No separate Prospero Win launcher tile is required. No songs, game-file patches,
console exploit, registration payload or system/database modifications are included.
You need an already prepared homebrew console, FTP and ShadowMountPlus.

**This is a first-install tool.** It refuses an existing YARG title, prefix or
profile. It never updates or overwrites your profiles, settings, scores or songs.
Keep your current installation when testing an upgrade; there is no migration
command yet.

## Prepare on Linux or WSL

Requirements: Python 3.10+, PyYAML, Git and the pinned prospero-win **host Wine**.
Use the host Wine setup in [BUILDING.md](docs/BUILDING.md); an arbitrary system
Wine is not a qualified substitute. Preparation downloads checksum-pinned releases,
creates the Wine prefix with upstream's installer, and makes portable registry and
symlink tables using upstream's prefix tool.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python yarg_ps5.py prepare --wine /path/to/prospero-host-wine --output ./dist
python yarg_ps5.py verify ./dist
```

Preparation requires disk space for downloads and the fresh prefix, and refuses
an existing output directory. `cache/` retains verified downloads. Failed preparation
may leave a named `.incoming-*` output for inspection; it is never published as a
completed package.

## Windows

Clone this repository in Windows PowerShell, then enter root WSL Ubuntu:

```powershell
git clone https://github.com/Gudui/yarg-ps5 C:\Users\YOUR_NAME\repos\yarg-ps5
wsl.exe -d Ubuntu -u root
```

If Ubuntu first asks you to create an account, complete that one-time setup
(password input is invisible), run `exit`, then rerun the root command above.
At the resulting root Ubuntu prompt, use your actual Windows username:

```bash
cd /mnt/c/Users/YOUR_NAME/repos/yarg-ps5
python3 -m venv /root/venvs/yarg-ps5
. /root/venvs/yarg-ps5/bin/activate
python -m pip install -r requirements.txt
# First build host Wine as described in docs/BUILDING.md.
python yarg_ps5.py prepare --wine /root/src/prospero-win-yarg/.deps/wine-host/install/usr/bin/wine --output ./dist
exit
```

Back in Windows PowerShell, verify and deploy using Python for Windows:

```powershell
cd C:\Users\YOUR_NAME\repos\yarg-ps5
python yarg_ps5.py verify .\dist
python yarg_ps5.py deploy .\dist --host YOUR_PS5_IP --port 2121
```

## Install and launch

Close YARG and enable anonymous FTP on the PS5. The deployment command above
uploads outside ShadowMount's scan directory and verifies every file. It publishes
the complete prefix and profile first, and the complete title folder last, with
`eboot.bin` already inside. A failed publish moves newly published components back
to staging. Existing destinations are refused before upload and rechecked before
publication. No remote deletion is used.

Refresh/register **YARG** normally in ShadowMountPlus, then launch it from Home.
Registration and physical console controls are manual. Inspect the staging/report
paths before retrying after an interrupted deployment. This tool does not repair
ShadowMount's in-memory retry latch.

The DualSense profile supplies menu navigation. An X-plorer is exposed as an
XInput GuitarAlternate device. In-game Profiles has controller-focus limitations;
profile creation may need a mouse. A two-finger DualSense touchpad click opens
prospero-win's PS5 keyboard once the intended text field has focus.

## Sources and verification

`components.json` pins every top-level download by SHA-256. The overlay contains
qualified native/input artifacts and complete ELF integrity hashes, plus source
provenance. It retains the upstream runtime's `LICENSES/`, `THIRD_PARTY.md` and
original source records. SELF read-back may be materialized ELF; verification
allows only the known nonloadable version/build-ID metadata difference, never
runtime code changes.

See [BUILDING.md](docs/BUILDING.md) for pinned sources and artifact packaging.
The installer code is MIT; downloaded components retain their own licenses.
YARG is an independent project by YARC. This repository is not an official YARG
or PlayStation release.

```bash
python -m unittest discover -s tests -v
```
