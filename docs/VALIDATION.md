# Initial release validation

Host validation on 2026-11-01:

- Nine installer tests pass on Windows: traversal/symlink rejection, corrupt
  downloads, complete package verification, existing destination preservation,
  corrupt transfer refusal, publish order, rollback and ELF code integrity.
- A fresh prefix was created by the pinned upstream installer with the prepared
  host Wine. DXVK 2.6.2 installation completed.
- The complete staged installation verifies **4,055 files**, including **19**
  native/SELF/PRX integrity records.
- All **449 official YARG application files** match the release ZIP byte for byte.
- The generated launch profile matches the console-qualified profile:
  `4a51544c5a5eb3a01df0b7ab9e888b0ff0b4279aba4ccbafbf52fe17df17cce0`.

An initial verifier rejected the prefix/profile parent directories after prefix
creation. The directory allowlist was corrected and regression-tested; the same
complete stage was reverified and finalized without rerunning Wine initialization.

The qualified runtime overlay has independent PS5 firmware 5.50 evidence for
stable YARG startup, DualSense/X-plorer input and hotplug. The installer deployment
has **not** been run against a fresh PS5 destination. The GitHub PR adaptations
to the newer upstream input ABI also remain target-pending; this release uses
the earlier qualified binary overlay.

This is an experimental first-install release, not an in-place updater. No
gameplay scoring, timing calibration, other firmware/controller models or three
simultaneous USB controllers are claimed by the installer checks.

# Nightly b4161 validation

Host validation on 2026-11-06, for the release that installs YARG nightly **b4161**
(`YARG_b4161-Windows-x64.zip`, SHA-256 `8511fe04…523a`, matching GitHub's published digest;
YARG commit `3e22931`) instead of v0.15.0:

- The nine installer tests pass.
- `prepare` with the same host Wine created a fresh prefix and installed DXVK 2.6.2;
  `verify` checks **4,069 files**.
- All **463 YARG application files** match the nightly ZIP byte for byte, with none
  missing or added.
- The DualSense profile is written to `YARC/YARG/nightly/profiles/`, where a nightly
  build keeps its user data. The nightly still reads its version-2 bindings file, and
  its device hash and auto-connect code are unchanged from v0.15.0.
- The launch profile is unchanged (`4a51544c…`). All 1,786 title/runtime files are
  identical to the v0.1.0 package.

**Not yet run on a PS5.** The nightly is a different YARG build (346 commits after
v0.15.0, same Unity 6000.3.5f2), so its console startup, input and audio are unqualified.
