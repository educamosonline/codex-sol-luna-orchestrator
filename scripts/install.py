#!/usr/bin/env python3
"""Portable, preview-first installation of Sol/Luna agents and skill (Python 3.11+)."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path('skills/sol-luna-orchestrator')


def payload(root: Path = ROOT) -> dict[Path, bytes]:
    files = sorted((root / 'agents').glob('*.toml'))
    files += sorted(p for p in (root / SKILL).rglob('*') if p.is_file()
                    and '__pycache__' not in p.parts and p.suffix != '.pyc')
    if not files or not (root / SKILL / 'SKILL.md').is_file():
        raise ValueError('Incomplete repository payload')
    result = {p.relative_to(root): p.read_bytes() for p in files}
    for path, data in result.items():
        if path.parts[0] == 'agents':
            agent = tomllib.loads(data.decode('utf-8'))
            for field in ('name', 'description', 'developer_instructions'):
                if not agent.get(field):
                    raise ValueError(f'{path}: missing {field}')
            expected = 'gpt-6-sol' if agent['name'] == 'sol_reviewer' else 'gpt-6-luna'
            if agent.get('model') != expected:
                raise ValueError(f'{path}: expected {expected}')
    return result


def safe_target(home: Path, relative: Path) -> Path:
    target = home / relative
    if not target.resolve().is_relative_to(home.resolve()):
        raise ValueError(f'Target escapes Codex home: {relative}')
    # Refuse linked/junction payload paths, including links that remain in home.
    current = target
    while current != home:
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise ValueError(f'Linked target refused: {relative}')
        current = current.parent
    return target


def plan(home: Path) -> list[tuple[Path, bytes, bytes | None]]:
    changes = []
    for relative, data in payload().items():
        target = safe_target(home, relative)
        if target.exists() and not target.is_file():
            raise ValueError(f'Target is not a file: {relative}')
        before = target.read_bytes() if target.exists() else None
        if before != data:
            changes.append((relative, data, before))
    return changes


def install(home: Path, apply: bool = False, replace: bool = False) -> int:
    changes = plan(home)  # Preflight every destination before writing anything.
    for relative, data, before in changes:
        print(f'{"ADD" if before is None else "REPLACE"} {relative.as_posix()}')
        print(''.join(difflib.unified_diff(
            (before or b'').decode('utf-8', errors='replace').splitlines(True),
            data.decode('utf-8').splitlines(True),
            fromfile=f'installed/{relative.as_posix()}',
            tofile=f'package/{relative.as_posix()}')), end='')
    if not changes:
        print('Already up to date.')
        return 0
    if not apply:
        print('Preview only. Use --apply to install; --replace to back up and replace conflicts.')
        return 0
    if any(before is not None for _, _, before in changes) and not replace:
        print('Existing files differ. No changes written. Review preview, then use --apply --replace.', file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup_relative = Path('backups/sol-luna-orchestrator') / stamp
    for relative, _, before in changes:
        if before is not None:
            backup = safe_target(home, backup_relative / relative)
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(before)
    manifest = safe_target(home, Path('sol-luna-orchestrator-manifests') / f'install-{stamp}.json')
    # All backups completed before modifying any installed file.
    for relative, data, _ in changes:
        target = safe_target(home, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        'schema_version': 1, 'version': '1.0.0-gpt6',
        'backup': str(home / backup_relative),
        'files': {p.as_posix(): hashlib.sha256(data).hexdigest() for p, data in payload().items()},
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Installed in {home}. Manifest: {manifest}')
    return 0


def doctor(home: Path) -> int:
    failures = 0
    for relative, expected in payload().items():
        target = safe_target(home, relative)
        ok = target.is_file() and target.read_bytes() == expected
        print(f'{"PASS" if ok else "FIX"} {relative.as_posix()}')
        failures += not ok
    config = home / 'config.toml'
    if config.exists():
        settings = tomllib.loads(config.read_text(encoding='utf-8-sig'))
        if settings.get('agents', {}).get('enabled') is False or settings.get('features', {}).get('multi_agent') is False:
            print('FIX multi-agent tools disabled in config.toml')
            failures += 1
        if settings.get('model') != 'gpt-6-sol':
            print('INFO Select gpt-6-sol in the app or start codex -m gpt-6-sol.')
    print('INFO Local files checked only. Confirm model access and loaded agents in a new Codex session.')
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'doctor'], nargs='?', default='install')
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex'))
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    try:
        home = args.codex_home.expanduser().resolve()
        if args.command == 'doctor':
            return doctor(home)
        return install(home, args.apply, args.replace)
    except (OSError, ValueError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
