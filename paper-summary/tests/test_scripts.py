"""Offline regression checks; run with python -m unittest discover -s tests -v."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
PROCESS = SKILL / 'scripts' / 'process_images.py'
EXTRACT = SKILL / 'scripts' / 'extract_images.py'


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root / 'work' / 'extracted'
        self.images.mkdir(parents=True)
        self.md = self.root / 'work' / 'summary.md'
        self.md.write_text('<img src="images/Paper-method.png" />\n'
                           '<!-- RENAME: figure_01.png -> Paper-method.png -->\n', encoding='utf-8')
        (self.images / 'figure_01.png').write_bytes(b'used image')
        (self.images / 'figure_02.png').write_bytes(b'unused image')
        (self.images / 'image_index.json').write_text('{}')
        self.output = self.root / 'outputs' / 'paper'

    def run_script(self, *extra):
        return subprocess.run([sys.executable, str(PROCESS), str(self.md), '-d', str(self.images),
                               '-o', str(self.output / 'images'), '--md-output-dir', str(self.output),
                               '--no-webp', *extra], capture_output=True, text=True, encoding='utf-8')

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_dry_run_changes_nothing(self):
        before = self.snapshot()
        result = self.run_script('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_archive_keeps_image_reference_valid(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        final_md = self.output / 'summary.md'
        self.assertIn('images/Paper-method.png', final_md.read_text(encoding='utf-8'))
        self.assertNotIn('RENAME', final_md.read_text(encoding='utf-8'))
        self.assertEqual((self.output / 'images' / 'Paper-method.png').read_bytes(), b'used image')
        self.assertFalse(self.md.exists())
        self.assertEqual(list(self.images.iterdir()), [])

    def test_archive_collision_aborts_before_changes(self):
        destination = self.output / 'images'
        destination.mkdir(parents=True)
        (destination / 'Paper-method.png').write_bytes(b'historical image')
        before = self.snapshot()
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_markdown_collision_aborts_before_changes(self):
        self.output.mkdir(parents=True)
        (self.output / 'summary.md').write_text('historical note')
        before = self.snapshot()
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_rename_path_traversal_aborts_before_changes(self):
        self.md.write_text('<!-- RENAME: figure_01.png -> ../escaped.png -->', encoding='utf-8')
        before = self.snapshot()
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_no_index_preserves_unused_images(self):
        (self.images / 'image_index.json').unlink()
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual((self.images / 'figure_02.png').read_bytes(), b'unused image')

    def test_archive_path_guard_aborts_before_changes(self):
        guarded = self.root / 'images' / 'existing'
        self.images.rename(self.root / 'extracted-backup')
        guarded.mkdir(parents=True)
        (guarded / 'figure_01.png').write_bytes(b'historical image')
        self.images = guarded
        before = self.snapshot()
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(before, self.snapshot())


class ExtractionTests(unittest.TestCase):
    def test_invalid_page_syntax_fails_without_model_dependencies(self):
        for pages in ['0', '3-1', 'nope', '']:
            result = subprocess.run([sys.executable, str(EXTRACT), 'paper.pdf', '--pages', pages],
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b'ModuleNotFoundError', result.stderr)

    def test_only_selected_pages_are_rendered(self):
        # Isolate Windows stream setup, replace model/rendering dependencies and
        # verify actual page requests and the generated index without downloads.
        code = r'''
import importlib.util, json, pathlib, sys, types
extract_path, out = sys.argv[1:]
calls = []
class Image:
    def crop(self, bbox): return self
    def save(self, path): pathlib.Path(path).write_bytes(b'cropped image')
def render(path, first_page, last_page):
    assert first_page == last_page
    calls.append(first_page)
    return [Image()]
pdf = types.ModuleType('pdf2image')
pdf.pdfinfo_from_path = lambda path: {'Pages': 6}
pdf.convert_from_path = render
sys.modules['pdf2image'] = pdf
class Loader:
    @classmethod
    def from_pretrained(cls, *a, **k): return cls()
models = types.ModuleType('transformers')
models.AutoProcessor = models.AutoModelForCausalLM = Loader
sys.modules['transformers'] = models
spec = importlib.util.spec_from_file_location('extract', extract_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.tf_id_detection = lambda *a: {'bboxes': [[0, 0, 5, 5]], 'labels': ['figure']}
mod.extract_images_from_pdf('example.pdf', out, pages=[2, 5])
assert calls == [2, 5], calls
index = json.loads((pathlib.Path(out) / 'image_index.json').read_text(encoding='utf-8'))
assert index['total_pages'] == 6
assert [x['page'] for x in index['extracted_items']] == [2, 5]
try:
    mod.extract_images_from_pdf('example.pdf', out + '-invalid', pages=[7])
except ValueError:
    pass
else:
    raise AssertionError('out-of-range pages were accepted')
'''
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-c', code, str(EXTRACT), str(Path(tmp) / 'extracted')],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
