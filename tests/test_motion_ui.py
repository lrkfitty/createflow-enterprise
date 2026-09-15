"""Exercise the actual Motion UI with fake credits and a fake provider."""
from pathlib import Path
import textwrap
import unittest
from streamlit.testing.v1 import AppTest

source = (Path(__file__).resolve().parents[1] / 'app.py').read_text()
start = source.index('        ref_video_url = None\n        wan_char_swap = False', source.index('key="wan_studio_flavor_select"'))
end = source.index('# TAB 8: CHARACTER STUDIO', start)
body = textwrap.dedent(source[start:source.rfind('# ==========================================', start, end)])
setup = '''
import os
import streamlit as st
import sys, types
fake_adapter = types.ModuleType('execution.generate_wan')
fake_adapter.sanitize_prompt_for_provider = lambda text: text
sys.modules['execution.generate_wan'] = fake_adapter
wan_model_flavor = 'Seedance 2.5 (Reference-to-Video)'
rig_anim_res = {'primary_image_path': 'https://example.test/bar.png', 'extra_ref_paths': ['https://example.test/angeil.png', 'https://example.test/danni.png'], 'reference_labels': {'https://example.test/bar.png':'Location: Bar', 'https://example.test/angeil.png':'Character: Angeil', 'https://example.test/danni.png':'Character: Danni'}}
anim_image_path = rig_anim_res['primary_image_path']
st.session_state.current_user = {'username':'test'}
class Auth:
    def deduct_credits(self, *args):
        st.session_state['charges'] = st.session_state.get('charges', 0) + 1
        return True
auth_mgr = Auth()
def get_user_out_dir(*args): return 'output'
def generate_wan_video(**kwargs):
    if kwargs.get('dry_run'):
        return {'status':'prepared', 'payload':{'prompt':kwargs['prompt']}}
    st.session_state['submits'] = st.session_state.get('submits', 0) + 1
    return {'status':'success'}
'''

class MotionUITests(unittest.TestCase):
    def ready(self):
        at = AppTest.from_string(setup + body).run()
        self.assertFalse(at.exception)
        at.checkbox(key='wan_previz_mode').check().run()
        at.text_area(key='wan_previz_blocking').set_value('Angeil holds the glass. Danni is beside her.').run()
        at.text_input(key='wan_studio_ref_url_input').set_value('https://example.test/camera.mp4').run()
        at.text_area(key='wan_anim_prompt').set_value('Angeil drinks while Danni watches.').run()
        return at

    def test_review_then_submit(self):
        at = self.ready()
        at.button(key='wan_review_anim').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.dataframe), 1)
        self.assertNotIn('charges', at.session_state)
        at.button(key='wan_run_anim').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['charges'], 1)
        self.assertEqual(at.session_state['submits'], 1)

    def test_change_after_review_blocks_charge(self):
        at = self.ready()
        at.button(key='wan_review_anim').click().run()
        at.text_area(key='wan_anim_prompt').set_value('Danni stands.').run()
        at.button(key='wan_run_anim').click().run()
        self.assertTrue(at.error)
        self.assertNotIn('charges', at.session_state)

    def test_no_review_blocks_charge(self):
        at = self.ready()
        at.button(key='wan_run_anim').click().run()
        self.assertTrue(at.error)
        self.assertNotIn('charges', at.session_state)
