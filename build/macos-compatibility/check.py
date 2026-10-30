#!/usr/bin/env python3
"""Report declared x86_64 deployment requirements; does not emulate old macOS."""
import argparse
import importlib.util
import json
import plistlib
import struct
from pathlib import Path

spec = importlib.util.spec_from_file_location('resources', Path(__file__).resolve().parents[1] / 'nextcloud-intel/adapt-resources.py')
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)


def version(value):
    parts = tuple(int(p) for p in value.split('.'))
    return (parts + (0, 0, 0))[:3]


def binary_minimums(path, cpu=0x01000007):
    """Read deployment load commands from the requested Mach-O slice."""
    with path.open('rb') as f:
        size = path.stat().st_size
        header = f.read(8)
        if len(header) != 8:
            raise ValueError(f'Truncated header: {path}')
        offset, limit = 0, size
        if header[:4] in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
            count = struct.unpack('>I', header[4:])[0]
            wide = header[3] == 0xbf
            stride = 32 if wide else 20
            matches = []
            for _ in range(count):
                entry = f.read(stride)
                if len(entry) != stride:
                    raise ValueError(f'Truncated fat header: {path}')
                arch = struct.unpack('>I', entry[:4])[0]
                start, length = struct.unpack('>QQ' if wide else '>II', entry[8:24] if wide else entry[8:16])
                if arch == cpu:
                    matches.append((start, length))
            if len(matches) != 1:
                raise ValueError(f'Expected exactly one target architecture: {path}')
            offset, length = matches[0]
            limit = offset + length
            if offset < 8 + count * stride or limit > size:
                raise ValueError(f'Invalid architecture bounds: {path}')
        f.seek(offset)
        header = f.read(32)
        if header[:4] != b'\xcf\xfa\xed\xfe' or len(header) != 32:
            raise ValueError(f'Expected little-endian 64-bit Mach-O: {path}')
        arch, _, _, ncmds, command_bytes = struct.unpack('<IIIII', header[4:24])
        if arch != cpu or offset + 32 + command_bytes > limit:
            raise ValueError(f'Invalid Mach-O header: {path}')
        end = offset + 32 + command_bytes
        targets = []
        for _ in range(ncmds):
            position = f.tell()
            raw = f.read(8)
            if len(raw) != 8:
                raise ValueError(f'Truncated load command: {path}')
            cmd, length = struct.unpack('<II', raw)
            if length < 8 or position + length > end:
                raise ValueError(f'Invalid load-command bounds: {path}')
            if cmd in (0x24, 0x32):
                if length < (16 if cmd == 0x24 else 24):
                    raise ValueError(f'Truncated deployment command: {path}')
                if cmd == 0x32:
                    platform = struct.unpack('<I', f.read(4))[0]
                    if platform != 1:
                        raise ValueError(f'Expected macOS platform, found {platform}: {path}')
                encoded = struct.unpack('<I', f.read(4))[0]
                targets.append(f'{encoded >> 16}.{(encoded >> 8) & 255}.{encoded & 255}')
            f.seek(position + length)
        if f.tell() != end:
            raise ValueError(f'Load-command count/size mismatch: {path}')
        return targets


def report(app):
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    files = []
    for p in sorted(app.rglob('*')):
        if p.is_symlink() or not p.is_file():
            continue
        arch = resources.architectures(p)
        if arch is None:
            continue
        if 0x01000007 not in arch:
            raise ValueError(f'No x86_64 slice: {p}')
        targets = binary_minimums(p)
        if not targets:
            raise ValueError(f'Missing deployment load command: {p}')
        files.append({'path': str(p.relative_to(app)), 'minimum_macos': max(targets, key=version)})
    if not files:
        raise ValueError('No native files found')
    bundle_min = info.get('LSMinimumSystemVersion', '0')
    declared_min = max([bundle_min] + [f['minimum_macos'] for f in files], key=version)
    return {
        'app': app.name,
        'bundle_minimum': bundle_min,
        'maximum_native_minimum': declared_min,
        'systems': {name: {'meets_declared_minimum': version(v) >= version(declared_min),
                           'runtime_tested': False}
                    for name, v in [('Monterey', '12'), ('Sequoia', '15'), ('Tahoe', '26')]},
        'limitation': 'Declared deployment requirements only. Does not validate API availability, GPU, OCLP, document editing or launch on these systems.',
        'native_files': files,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = report(args.app)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'native_files'}, indent=2))
    print(f'Checked {len(result["native_files"])} native files')
