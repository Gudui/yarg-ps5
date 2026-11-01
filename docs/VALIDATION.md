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
