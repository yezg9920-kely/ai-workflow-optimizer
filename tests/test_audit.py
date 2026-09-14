import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1]/'scripts/audit.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

class AuditTests(unittest.TestCase):
    def test_quoted_description(self):
        meta, body, warnings = audit.metadata('---\nname: sample\ndescription: "Read: only when asked"\n---\nBody')
        self.assertEqual(meta['description'], 'Read: only when asked')
        self.assertEqual(body, 'Body'); self.assertEqual(warnings, [])

    def test_folded_crlf(self):
        meta, _, warnings = audit.metadata('---\r\nname: test\r\ndescription: >-\r\n  first\r\n  second\r\nmetadata:\r\n  field: test\r\n---\r\nbody')
        self.assertEqual(meta['description'], 'first second'); self.assertEqual(warnings, [])

    def test_uncertain_yaml_is_not_validated(self):
        _, _, warnings = audit.metadata('---\nname: test\ndescription: read: more\n---\n')
        self.assertIn('description_yaml_needs_review', warnings)

    def test_missing_frontmatter(self):
        self.assertIn('missing_or_unclosed_frontmatter', audit.metadata('# text')[2])

    def test_duplicate_field(self):
        self.assertIn('duplicate_name', audit.metadata('---\nname: a\nname: b\ndescription: x\n---\n')[2])

    def test_read_only_and_config_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p=root/'SKILL.md';p.write_text('---\nname: t\ndescription: test\n---\nbody')
            (root/'config.toml').write_text('secret_marker = "PRIVATE"')
            before={str(f):f.read_bytes() for f in root.iterdir()}
            result=audit.inventory([root])
            self.assertEqual(len(result['files']),1)
            self.assertNotIn('PRIVATE',str(result))
            self.assertEqual(before,{str(f):f.read_bytes() for f in root.iterdir()})

    def test_missing_links_and_fenced_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'SKILL.md';(p.parent/'exists.md').write_text('ok')
            p.write_text('---\nname: t\ndescription: test\n---\n[a](exists.md) [b](gone.md) [c](https://example.com)\n```md\n[x](example-only.md)\nAlways read\n```')
            row=audit.inspect(p)
            self.assertEqual(row['missing_links'],['gone.md'])
            self.assertNotIn('unconditional_read_candidate',row['candidates'])

    def test_overlap_not_usage_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['one','two']:
                d=root/name;d.mkdir();(d/'SKILL.md').write_text('---\nname: same\ndescription: test\n---\nbody')
            result=audit.inventory([root,root/'one'])
            self.assertEqual(len(result['files']),2)
            self.assertEqual(len(result['identical_file_candidates']),1)
            self.assertEqual(len(result['same_name_candidates']['same']),2)
            self.assertEqual(result['scope'],'disk_inventory_not_active_session_or_usage')

    def test_symlinks_and_private_dirs_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); actual=root/'actual';actual.mkdir();(actual/'SKILL.md').write_text('# text')
            (root/'alias').symlink_to(actual,target_is_directory=True)
            hidden=root/'memories';hidden.mkdir();(hidden/'SKILL.md').write_text('PRIVATE')
            result=audit.inventory([root,root/'alias'])
            self.assertEqual(len(result['files']),1)
            self.assertEqual(result['errors'][0]['error'],'symlink_root_skipped')

    def test_bounded_file_read_and_bad_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'SKILL.md';p.write_bytes(b'x'*(audit.MAX_BYTES+1))
            self.assertEqual(audit.inspect(p)['error'],'file_too_large')
            p.write_bytes(b'\xff')
            self.assertEqual(audit.inspect(p)['error'],'UnicodeDecodeError')

    def test_inaccessible_root_reported(self):
        with patch.object(Path, 'is_symlink', side_effect=PermissionError('denied')):
            result=audit.inventory(['/inaccessible'])
            self.assertEqual(result['errors'][0]['error'],'PermissionError')

    def test_missing_root_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(audit.inventory([Path(tmp)/'absent'])['errors'][0]['error'],'missing_root')

if __name__=='__main__':
    unittest.main()
