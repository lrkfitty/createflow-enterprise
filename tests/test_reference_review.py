import ast
import base64
import os
from pathlib import Path
import re
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

from execution.reference_review import build_review, fingerprint

ROOT = Path(__file__).resolve().parents[1]
# Load only the real adapter functions: no dotenv or production credentials.
module = ast.parse((ROOT / 'execution/generate_wan.py').read_text())
functions = ast.Module(body=[n for n in module.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
network = types.SimpleNamespace(post=Mock(), get=Mock(), RequestException=ConnectionError)
namespace = dict(os=os, time=time, base64=base64, re=re, requests=network)
exec(compile(functions, 'generate_wan.py', 'exec'), namespace)
generate = namespace['generate_wan_video']

class ReferenceTests(unittest.TestCase):
    def setUp(self):
        network.post.reset_mock()
        network.get.reset_mock()
        network.post.side_effect = None
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'ATLASCLOUD_API_KEY': 'offline-test-only'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.images = ['https://example.test/bar.png', 'https://example.test/angeil.png', 'https://example.test/danni.png']
        self.labels = dict(zip(self.images, ['Location: Bar', 'Character: Angeil', 'Character: Danni']))

    def review(self, **kw):
        args = dict(prompt='Angeil lifts her glass. Danni watches.', images=self.images, videos=['https://example.test/camera.mp4'], audios=[], labels=self.labels, previz=True, blocking='Angeil holds the glass; Danni sits beside her.', duration=10)
        args.update(kw)
        return build_review(**args)

    def prepare(self, **kw):
        args = dict(prompt='Angeil lifts a glass.', image_path=self.images[0], extra_images=self.images[1:], ref_video_path='https://example.test/camera.mp4', model='bytedance/seedance-2.5/reference-to-video', duration=10, dry_run=True, output_folder=self.temp.name)
        args.update(kw)
        return generate(**args)

    def test_environment_is_not_character(self):
        rows, prompt = self.review()
        self.assertIn('@Image2: Character: Angeil', prompt)
        self.assertEqual(rows[0]['Role'], 'Location: Bar')
        self.assertIn('camera trajectory', prompt)

    def test_reorder_rebuilds_tags(self):
        _, prompt = self.review(images=list(reversed(self.images)))
        self.assertIn('@Image1: Character: Danni', prompt)

    def test_duplicate_slots_survive_adapter(self):
        result = self.prepare(extra_images=[self.images[0], self.images[1]])
        self.assertEqual(result['status'], 'prepared')
        self.assertEqual(result['payload']['reference_images'], [self.images[0], self.images[0], self.images[1]])
        network.post.assert_not_called()

    def test_stale_tags_blocked(self):
        with self.assertRaisesRegex(ValueError, 'old'):
            self.review(prompt='@Image1 is Angeil.')

    def test_missing_tag_blocked(self):
        with self.assertRaisesRegex(ValueError, 'no attached'):
            self.review(previz=False, prompt='@Image10 speaks.')

    def test_requires_proxy_assignment(self):
        with self.assertRaises(ValueError):
            self.review(blocking='')

    def test_reference_limit_not_truncated(self):
        with self.assertRaises(ValueError):
            self.review(images=self.images * 11)

    def test_missing_file_blocked(self):
        with self.assertRaises(ValueError):
            self.review(images=['/missing/image.jpg'])

    def test_changed_bytes_invalidate_review(self):
        path = Path(self.temp.name) / 'same.png'
        path.write_bytes(b'first')
        first = fingerprint(self.review(images=[str(path)]))
        path.write_bytes(b'second')
        self.assertNotEqual(first, fingerprint(self.review(images=[str(path)])))

    def test_explicit_reference_mode_and_resolution(self):
        result = self.prepare(resolution='4K Ultra HD')
        self.assertEqual(result['payload']['omni_reference_task_type'], 'reference')
        self.assertEqual(result['payload']['resolution'], '4k-esr')
        network.post.assert_not_called()

    def test_missing_video_never_submitted(self):
        self.assertEqual(self.prepare(ref_video_path='/missing/video.mp4')['status'], 'failed')
        network.post.assert_not_called()

    def test_failed_upload_never_submitted(self):
        video = Path(self.temp.name) / 'video.mp4'
        video.write_bytes(b'video')
        uploader = types.ModuleType('execution.s3_uploader')
        uploader.upload_file_obj = Mock(return_value=None)
        with patch.dict('sys.modules', {'execution.s3_uploader': uploader}):
            self.assertEqual(self.prepare(ref_video_path=str(video))['status'], 'failed')
        network.post.assert_not_called()

    def test_timeout_not_replayed(self):
        network.post.side_effect = ConnectionError('timeout')
        result = self.prepare(dry_run=False)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(network.post.call_count, 1)

    def test_prepared_payload_reaches_submit_unchanged(self):
        result = self.prepare()
        network.post.return_value = types.SimpleNamespace(status_code=400)
        self.prepare(dry_run=False, prepared_payload=result['payload'])
        self.assertEqual(network.post.call_args.kwargs['json'], result['payload'])

if __name__ == '__main__':
    unittest.main()
