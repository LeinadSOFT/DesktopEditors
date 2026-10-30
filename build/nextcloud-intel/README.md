# Unofficial Nextcloud Office Intel adaptation

This repackages the successful x86_64 app from Actions run `40976870151`
(commit `e402c67`) with non-native resources from the official Nextcloud
Office 9.3.6 ARM64 DMG. Both distributions use the same pinned 9.3.6 core,
desktop SDK and desktop-apps sources. It is not an official Nextcloud release,
is not notarized, and does not carry Nextcloud's signing identity.

The separate `Nextcloud Office Intel adaptation` workflow avoids rebuilding
the native SDK. It requires the original `macos-intel-x86_64` artifact to remain
available (currently retained for seven days). If it expires, regenerate the
Intel build and explicitly update the input run ID after verifying its commit.

The official DMG is downloaded from `nextcloud-releases/Office-DesktopEditors`
tag `v9.3.6` and checked against its published SHA-256. The script copies only
the asset catalog, icons, login/editor/provider web resources, license files
and localized bundle descriptions. It preserves native NIBs, converter,
frameworks, helpers, executable name and native entitlements. All Mach-O files
must contain x86_64 and remain byte-for-byte identical during resource copying.
The outer app is then signed ad hoc and verified recursively before packaging.

The Intel input has a stale 9.3.1 display version in its Info.plist despite
being built from the pinned 9.3.6 sources; the adaptation corrects that metadata.
The app uses a separate local bundle identifier and identifies the adaptation
in its About notice. Existing legal notices remain included.

A successful packaging run verifies architecture, signatures and DMG integrity,
not interactive behavior. Test launch, local DOCX/XLSX/PPTX editing, saving,
PDF export and Nextcloud connection on a real Intel Mac before relying on it.
