# Intel macOS deployment inspection

`check.py <app> <report.json>` runs on macOS with Xcode command-line tools.
It checks each regular Mach-O file has an x86_64 slice, reads that slice's
LC_BUILD_VERSION or LC_VERSION_MIN_MACOSX with `otool`, and compares the
maximum declared deployment minimum with Monterey 12, Sequoia 15 and Tahoe 26.
It also includes the outer bundle's LSMinimumSystemVersion in that maximum.
Missing architecture or deployment metadata fails inspection.

The separate workflow consumes the adapted DMG from run `41044816146`,
verifies its disk image and recursive code signature, and publishes JSON with
the per-file requirements. It does not rebuild or change the application.

A declared minimum is necessary but not sufficient for compatibility. This
report does not validate API availability, weak linking, GPU behavior, OCLP,
launch, editing, save or export. No runtime compatibility is claimed. If
Monterey is below the declared minimum, identify the specific dependencies
from the JSON and rebuild those with a supported deployment target; do not
simply lower LSMinimumSystemVersion.
