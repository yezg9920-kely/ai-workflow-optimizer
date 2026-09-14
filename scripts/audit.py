#!/usr/bin/env python3
"""Read-only instruction inventory. Standard library only; not a full YAML validator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

MAX_BYTES = 512 * 1024
SKIP = {'.git', 'node_modules', '__pycache__', '.venv', 'backups', 'memories', 'sessions'}
PATTERNS = {
    'broad_trigger_candidate': r'MUST trigger|do not under-trigger|所有联网|任何任务|every substantial|just pastes a URL',
    'unconditional_read_candidate': r'Always read|always read|每次.*必须.*读|读.*每一个.*docs|每次调用先读',
    'automatic_update_candidate': r'每次.*同步|每次.*拉.*最新|第 0 步永远',
    'premature_stop_candidate': r'Do NOT render automatically|Until then, stop at preview|任何修改.*先.*同意',
}

def scalar(source):
    s = source.strip()
    if s.startswith('"'):
        try:
            return json.loads(s), 'quoted'
        except (ValueError, TypeError):
            return s, 'complex_yaml_needs_review'
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1].replace("''", "'"), 'quoted'
    if ': ' in s or s.startswith(('[', '{', '&', '*')):
        return s, 'complex_yaml_needs_review'
    return re.split(r'\s+#', s, maxsplit=1)[0], 'plain'

def metadata(text):
    match = re.match(r'\A\ufeff?---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        return {}, text, ['missing_or_unclosed_frontmatter']
    lines = match[1].splitlines()
    result, warnings = {}, []
    for i, line in enumerate(lines):
        field = re.match(r'^(name|description):\s*(.*)$', line)
        if not field:
            continue
        key, value = field.groups()
        if key in result:
            warnings.append('duplicate_' + key)
        if value in ('>', '|', '>-', '|-', '>+', '|+'):
            block = []
            for following in lines[i + 1:]:
                if following and not following[0].isspace():
                    break
                block.append(following.strip())
            result[key] = (' ' if value.startswith('>') else '\n').join(block).strip()
        else:
            result[key], kind = scalar(value)
            if kind == 'complex_yaml_needs_review':
                warnings.append(key + '_yaml_needs_review')
    for key in ('name', 'description'):
        if not result.get(key):
            warnings.append('missing_' + key)
    return result, text[match.end():], warnings

def unfenced(text):
    output, marker = [], None
    for line in text.splitlines():
        fence = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            token = fence[1][0]
            if marker is None:
                marker = token
            elif marker == token:
                marker = None
            continue
        if marker is None:
            output.append(line)
    return '\n'.join(output)

def inspect(path, description_limit=160, body_limit=8000):
    try:
        with path.open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return {'path': str(path), 'error': 'file_too_large'}
        text = data.decode('utf-8-sig')
    except (OSError, UnicodeError) as exc:
        return {'path': str(path), 'error': type(exc).__name__}
    meta, body, warnings = metadata(text) if path.name == 'SKILL.md' else ({}, text, [])
    row = {'path': str(path), 'kind': 'skill' if path.name == 'SKILL.md' else 'instructions',
           'name': meta.get('name', path.parent.name), 'description': meta.get('description', ''),
           'chars': len(text), 'body_chars': len(body), 'description_chars': len(meta.get('description', '')),
           'sha256': hashlib.sha256(data).hexdigest(), 'metadata_warnings': warnings,
           'candidates': [], 'missing_links': []}
    if row['description_chars'] > description_limit:
        row['candidates'].append('long_description')
    if len(body) > body_limit:
        row['candidates'].append('large_entrypoint')
    visible = unfenced(text)
    for key, pattern in PATTERNS.items():
        if re.search(pattern, visible):
            row['candidates'].append(key)
    for target in re.findall(r'\]\(([^\n)]+)\)', unfenced(body)):
        target = target.strip().strip('<>')
        if re.match(r'^[a-zA-Z][\w+.-]*:', target) or target.startswith(('#', '/','~')):
            continue
        target = target.split('#', 1)[0]
        if not target or any(c in target for c in ('*', '{', '}', '<', '>')):
            continue
        try:
            if not (path.parent / target).exists():
                row['missing_links'].append(target)
        except OSError:
            row['missing_links'].append(target)
    return row

def inventory(roots, description_limit=160, body_limit=8000):
    paths, errors = set(), []
    for supplied in roots:
        root = Path(supplied).expanduser().absolute()
        try:
            is_link, exists, is_file = root.is_symlink(), root.exists(), root.is_file()
        except OSError as exc:
            errors.append({'root': str(root), 'error': type(exc).__name__}); continue
        if is_link:
            errors.append({'root': str(root), 'error': 'symlink_root_skipped'}); continue
        if not exists:
            errors.append({'root': str(root), 'error': 'missing_root'}); continue
        if is_file:
            if root.name in {'SKILL.md', 'AGENTS.md', 'AGENTS.override.md'}:
                paths.add(root)
            else:
                errors.append({'root': str(root), 'error': 'unsupported_file'} )
            continue
        def onerror(exc):
            errors.append({'root': str(root), 'error': type(exc).__name__})
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(directory)/d).is_symlink())
            for name in files:
                p = Path(directory)/name
                if name in {'SKILL.md', 'AGENTS.md', 'AGENTS.override.md'} and not p.is_symlink():
                    paths.add(p)
    rows = [inspect(p, description_limit, body_limit) for p in sorted(paths)]
    by_name, by_hash = {}, {}
    for row in rows:
        if 'error' in row or row['kind'] != 'skill':
            continue
        by_name.setdefault(row['name'], []).append(row['path'])
        by_hash.setdefault(row['sha256'], []).append(row['path'])
    return {'schema_version': 1, 'scope': 'disk_inventory_not_active_session_or_usage',
            'limitations': ['Heuristic candidates require semantic review.',
                           'Metadata extraction is not full YAML validation.',
                           'No configs, credentials, memories or session logs are read.',
                           'Output contains local paths and descriptions; do not publish it without review.'],
            'thresholds': {'description_chars': description_limit, 'body_chars': body_limit},
            'files': rows, 'errors': errors,
            'same_name_candidates': {k:v for k,v in by_name.items() if len(v)>1},
            'identical_file_candidates': [v for v in by_hash.values() if len(v)>1]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', required=True, help='Explicit skill tree or instruction file; repeatable')
    parser.add_argument('--description-limit', type=int, default=160)
    parser.add_argument('--body-limit', type=int, default=8000)
    args = parser.parse_args()
    if min(args.description_limit, args.body_limit) < 1:
        parser.error('thresholds must be positive')
    print(json.dumps(inventory(args.root, args.description_limit, args.body_limit), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
