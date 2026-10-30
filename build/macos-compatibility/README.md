# Intel macOS deployment inspection

`check.py <app> <report.json>` uses Python's binary-file reader.
It checks each regular Mach-O file has an x86_64 slice, reads that slice's
LC_BUILD_VERSION or LC_VERSION_MIN_MACOSX directly from the Mach-O headers, and compares the
maximum declared deployment minimum with Monterey 12, Sequoia 15 and Tahoe 26.
It also includes the outer bundle's LSMinimumSystemVersion in that maximum.
Missing architecture or deployment metadata fails inspection.

The Nextcloud Intel adaptation workflow runs the inspection on the adapted
bundle before signing/packaging, and includes the per-file JSON in its output
artifact. Inspection does not rebuild or change the application.

A declared minimum is necessary but not sufficient for compatibility. This
report does not validate API availability, weak linking, GPU behavior, OCLP,
launch, editing, save or export. No runtime compatibility is claimed. If
Monterey is below the declared minimum, identify the specific dependencies
from the JSON and rebuild those with a supported deployment target; do not
simply lower LSMinimumSystemVersion.
