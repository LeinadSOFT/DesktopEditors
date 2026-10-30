#!/usr/bin/env python3
"""Reuse non-native 9.3.6 Nextcloud resources with the existing Intel app."""
import argparse
import hashlib
import json
import plistlib
import shutil
import struct
from pathlib import Path


def architectures(path):
    with path.open('rb') as f:
        header = f.read(8)
        if len(header) < 8:
            return None
        magic = header[:4]
        if magic in (b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe'):
            return [struct.unpack('<I', header[4:])[0]]
        if magic in (b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf'):
            return [struct.unpack('>I', header[4:])[0]]
        if magic in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
            count = struct.unpack('>I', header[4:])[0]
            # Java class files share CAFEBABE but have a version, not arch count.
            if count > 64:
                return None
            stride = 32 if magic[-1] == 0xbf else 20
            result = []
            for _ in range(count):
                entry = f.read(stride)
                if len(entry) != stride:
                    raise ValueError(f'Truncated Mach-O: {path}')
                result.append(struct.unpack('>I', entry[:4])[0])
            return result
        return None


def native_manifest(app):
    result = {}
    for p in app.rglob('*'):
        if p.is_symlink() or not p.is_file():
            continue
        arch = architectures(p)
        if arch is not None:
            if 0x01000007 not in arch:
                raise ValueError(f'Native file lacks x86_64: {p}: {arch}')
            result[str(p.relative_to(app))] = hashlib.sha256(p.read_bytes()).hexdigest()
    if not result:
        raise ValueError('No Intel Mach-O files found')
    return result


def apply(source, target):
    src, dst = source / 'Contents', target / 'Contents'
    official = plistlib.loads((src / 'Info.plist').read_bytes())
    info_path = dst / 'Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    if official.get('CFBundleShortVersionString') != '9.3.6' or official.get('CFBundleIdentifier') != 'asc.nextcloud-office.Nextcloud-Office':
        raise ValueError('Expected official Nextcloud Office 9.3.6')
    if info.get('CFBundleIdentifier') != 'local.leinadsoft.euro-office-intel':
        raise ValueError('Expected the Intel app from the pinned successful run')
    before = native_manifest(target)
    resources = src / 'Resources'
    # Preserve native NIBs, converter binaries, frameworks and executable.
    selected = [resources / n for n in ('AppIcon.icns', 'Assets.car', 'login', 'editors', 'providers', 'license')]
    selected += sorted(resources.glob('file-*.icns'))
    selected += sorted(resources.glob('*.lproj/InfoPlist.strings'))
    if not all(p.exists() for p in selected) or not selected:
        raise ValueError('Missing official resources')
    for p in selected:
        for q in ([p] if p.is_file() else p.rglob('*')):
            if q.is_symlink():
                raise ValueError(f'Resource symlink is not permitted: {q}')
            if q.is_file() and architectures(q) is not None:
                raise ValueError(f'Refusing native code from ARM package: {q}')
        dest = dst / 'Resources' / p.relative_to(resources)
        if p.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(p, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    # Keep the existing executable name: renaming it could break native paths.
    for key in ('CFBundleName', 'CFBundleDisplayName'):
        info[key] = 'Nextcloud Office'
    info['CFBundleIdentifier'] = 'local.leinadsoft.nextcloud-office-intel'
    # The successful Intel run used the pinned 9.3.6 sources, but the source
    # Info.plist still carried 9.3.1. Correct that stale display metadata.
    info['CFBundleShortVersionString'] = '9.3.6'
    info['NSHumanReadableCopyright'] = official['NSHumanReadableCopyright']
    info['SUEnableAutomaticChecks'] = False
    for key, value in official.items():
        if key.startswith('NS') and key.endswith('UsageDescription'):
            info[key] = value
    info_path.write_bytes(plistlib.dumps(info))
    about_path = dst / 'Resources/about.json'
    about = json.loads(about_path.read_text())
    about['buildInfo'] = ' · unofficial Intel adaptation · 9.3.6-intel.1'
    about['legal'] += '<p>Unofficial Intel adaptation by LeinadSOFT, using Nextcloud Office 9.3.6 resources. Not an official Nextcloud release. Adaptation source: <a href="https://github.com/LeinadSOFT/DesktopEditors/tree/macos-intel">LeinadSOFT/DesktopEditors, macos-intel</a>.</p>'
    about_path.write_text(json.dumps(about, ensure_ascii=False))
    if native_manifest(target) != before:
        raise ValueError('Native binaries changed during resource adaptation')
    print(f'Applied Nextcloud resources; preserved {len(before)} Intel native files byte-for-byte')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('official_app', type=Path)
    parser.add_argument('intel_app', type=Path)
    args = parser.parse_args()
    apply(args.official_app, args.intel_app)
