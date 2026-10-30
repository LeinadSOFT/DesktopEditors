#!/usr/bin/env python3
"""Report declared x86_64 deployment requirements; does not emulate old macOS."""
import argparse
import importlib.util
import json
import plistlib
import re
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location('resources', Path(__file__).resolve().parents[1] / 'nextcloud-intel/adapt-resources.py')
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)


def version(value):
    parts = tuple(int(p) for p in value.split('.'))
    return (parts + (0, 0, 0))[:3]


def minimums(output):
    result = []
    for block in re.split(r'Load command \d+', output):
        if 'cmd LC_BUILD_VERSION' in block:
            found = re.search(r'^\s*minos\s+([\d.]+)', block, re.M)
        elif 'cmd LC_VERSION_MIN_MACOSX' in block:
            found = re.search(r'^\s*version\s+([\d.]+)', block, re.M)
        else:
            continue
        if found:
            result.append(found[1])
    return result


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
        output = subprocess.run(['otool', '-arch', 'x86_64', '-l', str(p)],
                                text=True, capture_output=True, check=True).stdout
        targets = minimums(output)
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
