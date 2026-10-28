#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_required(path: str, old: str, new: str, min_count: int = 1):
    p = ROOT / path
    text = p.read_text()
    count = text.count(old)
    if count < min_count:
        raise RuntimeError(f"{path}: expected at least {min_count} occurrence(s) of {old!r}, found {count}")
    p.write_text(text.replace(old, new))
    print(f"patched {path}: {count} replacement(s)")


# The 9.3.6 macOS build was intentionally introduced as Apple-Silicon-only.
# Add a generic macOS predicate while keeping is_apple_silicon() intact for
# places that genuinely need to distinguish the CPU architecture.
common = "core/Common/3dParty/build_3rdparty_common.py"
replace_required(
    common,
    'def is_windows() -> bool:\n    return sys.platform == "win32"\n',
    'def is_windows() -> bool:\n    return sys.platform == "win32"\n\ndef is_macos() -> bool:\n    return sys.platform == "darwin"\n',
)

# Dependencies whose macOS implementation is architecture-neutral/native.
for rel in (
    "core/Common/3dParty/openssl/nc-build.py",
    "core/Common/3dParty/icu/nc-build.py",
    "core/Common/3dParty/qt/nc-build.py",
    "core/Common/3dParty/zlib-ng/nc-build.py",
    "core/Common/3dParty/openssl-hash/nc-build.py",
):
    replace_required(rel, "nc.is_apple_silicon()", "nc.is_macos()")

# V8 already derives target_cpu from platform.machine(); its macOS-specific
# setup is valid for both arm64 and x64. The arm64-only bitfield workaround is
# separately gated on targetarch == 'arm64', so broadening these OS checks does
# not apply that workaround to Intel.
replace_required(
    "core/Common/3dParty/v8/nc-build.py",
    "nc.is_apple_silicon()",
    "nc.is_macos()",
    min_count=5,
)

# CEF uses different Spotify prebuilt platform names for Intel and Apple Silicon.
replace_required(
    "core/Common/3dParty/cef/nc-build.py",
    '    elif nc.is_apple_silicon():\n        return "macosarm64"\n',
    '    elif nc.is_macos():\n        return "macosarm64" if nc.is_arm64() else "macosx64"\n',
)

# Boost's macOS branch hard-coded architecture=arm. Keep clang on both Mac
# architectures but select the b2 architecture from the actual target CPU.
boost = "core/Common/3dParty/boost/nc-build.py"
replace_required(
    boost,
    "if nc.is_linux() or nc.is_apple_silicon():",
    "if nc.is_linux() or nc.is_macos():",
)
replace_required(
    boost,
    '    if nc.is_apple_silicon():\n        build_cmd.append( "toolset=clang" )\n        build_cmd.append( "architecture=arm" )\n        build_cmd.append( "address-model=64" )\n',
    '    if nc.is_macos():\n        build_cmd.append( "toolset=clang" )\n        build_cmd.append( "architecture=arm" if nc.is_arm64() else "architecture=x86" )\n        build_cmd.append( "address-model=64" )\n',
)

# The Xcode target/scheme name still contains '-arm', but the target itself is
# otherwise usable for x86_64. Remove the explicit architecture exclusion;
# the workflow also passes ARCHS=x86_64 and ONLY_ACTIVE_ARCH=YES.
pbx = ROOT / "desktop-apps/macos/Euro-Office.xcodeproj/project.pbxproj"
text = pbx.read_text()
needle = "\t\t\t\tEXCLUDED_ARCHS = x86_64;\n"
count = text.count(needle)
if count == 0:
    raise RuntimeError("Xcode project: EXCLUDED_ARCHS = x86_64 not found")
pbx.write_text(text.replace(needle, ""))
print(f"patched Xcode project: removed {count} x86_64 exclusion(s)")

print("macOS Intel compatibility patches applied")
