"""Optional end-to-end tests with genuine model inference and public photo clips.
Prepare fixtures explicitly with scripts/prepare_ai_samples.py. Nothing downloads
while these tests or the editor are running.
"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.vision import readiness
from app.engine import probe

SAMPLES=Path(os.environ.get('QTC_SAMPLE_DIR','work/ai-samples')).resolve()
HAVE_SAMPLES=all((SAMPLES/f'sample-{i}.mp4').is_file() for i in range(5)) and (SAMPLES/'music.wav').is_file()


@unittest.skipUnless(readiness()['ready'] and HAVE_SAMPLES,'Install local AI and explicitly prepare public fixtures')
class EndToEndAI(unittest.TestCase):
    def test_actual_inference_story_render_and_regeneration_cache(self):
        from app.ai_editor import render_ai
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'first'
            videos=[SAMPLES/f'sample-{i}.mp4' for i in range(5)]
            first=render_ai(videos,SAMPLES/'music.wav',folder,15,test_size=(180,320))
            self.assertFalse(first['analysis_reused'])
            self.assertEqual(first['mode'],'local-ai')
            self.assertEqual(first['privacy']['external_ai_api_calls'],0)
            self.assertEqual({c['name'] for c in first['chapters']},{'opening','development','climax','ending'})
            self.assertTrue(first['output']['fully_decoded'])
            self.assertTrue(any(o['label']=='person' for s in first['selected'] for o in s['objects']))
            self.assertAlmostEqual(first['output']['duration'],15,delta=.25)
            self.assertTrue(all(s['inference']=='pretrained-local' for s in first['selected']))
            with patch('app.ai_editor.analyze_video',side_effect=AssertionError('Analysis should be reused')):
                second=render_ai(videos,SAMPLES/'music.wav',Path(d)/'second',15,variant=1,cache_folder=folder,test_size=(180,320))
            self.assertTrue(second['analysis_reused'])
            self.assertNotEqual(first['fingerprint'],second['fingerprint'])


@unittest.skipUnless(HAVE_SAMPLES and os.environ.get('QTC_TEST_4K')=='1','Set QTC_TEST_4K=1 for actual 4K encodes')
class ActualFormats(unittest.TestCase):
    def test_all_export_formats(self):
        from app.rendering import render_timeline
        from app.profiles import dimensions
        video=SAMPLES/'sample-0.mp4';meta=probe(video)
        # Renderer-only synthetic timeline fixture. Semantic inference is verified above.
        shot={'source':0,'start':0.,'length':2.,'transition':0.,'ramp':False,
              'anchor':[.5,.5],'rgb_mean':[100.,110.,120.],'phase':'opening'}
        with tempfile.TemporaryDirectory() as d:
            for resolution in ['1080p','4k']:
                for aspect in ['9:16','16:9']:
                    with self.subTest(resolution=resolution,aspect=aspect):
                        folder=Path(d)/(resolution+'-'+aspect.replace(':','-'));folder.mkdir()
                        width,height=dimensions(resolution,aspect)
                        output=render_timeline([video],[meta],{'path':SAMPLES/'music.wav','start':0},
                            {'timeline':[shot],'style':'cinematic','duration':2},folder,width,height,False,lambda *a:None)
                        self.assertEqual((output['width'],output['height']),(width,height))
                        self.assertTrue(output['fully_decoded'])

if __name__=='__main__':unittest.main()
