"""Unit inputs are labelled synthetic; integration invokes real downloaded models."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from app.profiles import dimensions,PROFILES
from app.planner import build_timeline,duplicate
from app.music import analyze_music
from app.engine import ambient,ff,probe
from app.vision import readiness


def synthetic_candidate(index):
    # Planner-only fixture, never a substitute for inference in production.
    vector=np.zeros(512);vector[index]=1
    return dict(source=index%5,start=(index//5)*4,available=4.,rejected=False,
                phash=format(index*78123491813243,'064b')[-64:],embedding=vector.tolist(),
                rgb_mean=[95+index,120,140],quality_score=.8,composition=.7,aesthetic_proxy=.6,
                tag=['coast','people','architecture','transport','nature'][index%5],
                scene_scores={'coast':.6 if index%5==0 else .01,'people':.8 if index%5==1 else 0},
                motion=.012+index*.0003,shake=.002,semantic_confidence=.8,anchor=[.5,.5],labels=[],objects=[])


def grid_music(duration):
    return dict(beats=list(np.arange(.5,duration,.5)),climax=duration*.68)


class InstallGuardTests(unittest.TestCase):
    def test_missing_weights_are_an_error_not_fake_ai(self):
        from app import vision
        with tempfile.TemporaryDirectory() as d, patch.object(vision,'MODEL_DIR',Path(d)):
            self.assertFalse(vision.readiness()['ready'])
            with self.assertRaisesRegex(ValueError,'setup-ai-windows'):
                vision.LocalVision()


class PlannerTests(unittest.TestCase):
    def test_four_phases_unique_quantized_timeline_and_variants(self):
        candidates=[synthetic_candidate(i) for i in range(35)]
        music=grid_music(36)
        first=build_timeline(candidates,[],music,36,'cinematic',0)
        second=build_timeline(candidates,[],music,36,'cinematic',1)
        self.assertEqual({c['name'] for c in first['chapters']},{'opening','development','climax','ending'})
        self.assertAlmostEqual(sum(s['length'] for s in first['timeline']),36)
        self.assertEqual(len(first['timeline']),len({(s['source'],s['start']) for s in first['timeline']}))
        self.assertNotEqual(first['fingerprint'],second['fingerprint'])
        for s in first['timeline']:
            self.assertAlmostEqual(s['timeline']*30,round(s['timeline']*30),places=4)
            self.assertLessEqual(s['length']+s['transition']+(.3 if s['ramp'] else 0),s['available']+.001)

    def test_styles_change_pacing_and_no_ramp_for_relaxing(self):
        candidates=[synthetic_candidate(i) for i in range(45)]
        fast=build_timeline(candidates,[],grid_music(30),30,'tiktok')
        slow=build_timeline(candidates,[],grid_music(30),30,'relaxing')
        self.assertGreater(len(fast['timeline']),len(slow['timeline']))
        self.assertFalse(any(s['ramp'] for s in slow['timeline']))

    def test_duplicate_bad_and_insufficient_footage(self):
        a=synthetic_candidate(0)
        self.assertTrue(duplicate(a,dict(a)))
        with self.assertRaisesRegex(ValueError,'chưa đủ'):
            build_timeline([a]*20,[],grid_music(30),30)
        a['rejected']=True
        with self.assertRaisesRegex(ValueError,'Không có cảnh'):
            build_timeline([a],[],grid_music(30),30)

    def test_dimensions_all_modes(self):
        self.assertEqual(dimensions('4k','16:9'),(3840,2160))
        self.assertEqual(dimensions('4k','9:16'),(2160,3840))
        self.assertEqual(dimensions('1080p','16:9'),(1920,1080))
        self.assertEqual(dimensions('1080p','9:16'),(1080,1920))
        with self.assertRaises(ValueError):dimensions('8k','1:1')


class MusicTests(unittest.TestCase):
    def test_real_beats_energy_and_excerpt(self):
        import wave
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'click.wav';t=np.arange(8000*24)/8000
            signal=np.sin(2*np.pi*180*t)*np.exp(-np.mod(t,.5)*65)*.5
            signal*=np.where(t<10,.1,1)
            with wave.open(str(path),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes((signal*32767).astype('<i2').tobytes())
            report=analyze_music(path,15)
            self.assertGreater(report['start'],5)
            self.assertAlmostEqual(report['bpm'],120,delta=5)
            self.assertGreater(len(report['beats']),15)
            self.assertGreater(report['confidence'],.15)
            self.assertTrue(7.5<=report['climax']<=12.3)

    def test_silence_rejected_without_fake_beats(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'silence.wav'
            ff('-f','lavfi','-i','anullsrc=r=8000:cl=mono','-t',16,path)
            with self.assertRaisesRegex(ValueError,'im lặng'):analyze_music(path,15)


@unittest.skipUnless(readiness()['ready'],'Install AI dependencies and real pretrained weights first')
class RealVisionTests(unittest.TestCase):
    def test_real_model_loaded_and_no_network_download(self):
        from app.vision import get_vision
        with patch('torch.hub.download_url_to_file',side_effect=AssertionError('Runtime model download prohibited')):
            vision=get_vision()
            rgb=np.zeros((256,256,3),np.uint8);rgb[:,::16]=255
            result=vision.infer(rgb)
        self.assertEqual(result['inference'],'pretrained-local')
        self.assertEqual(len(result['embedding']),512)
        self.assertAlmostEqual(float(np.linalg.norm(result['embedding'])),1,places=4)
        self.assertFalse(result['aesthetic_model'])
        self.assertEqual(len(result['labels']),5)

    def test_known_public_photos_when_available(self):
        from PIL import Image
        from app.vision import get_vision
        root=Path(os.environ.get('QTC_SAMPLE_DIR','work/ai-samples'))
        if not all((root/p).is_file() for p in ['dog.jpg','astronaut.png']):self.skipTest('Run scripts/prepare_ai_samples.py to fetch public fixtures')
        vision=get_vision()
        dog=vision.infer(np.asarray(Image.open(root/'dog.jpg').convert('RGB')))
        person=vision.infer(np.asarray(Image.open(root/'astronaut.png').convert('RGB')))
        self.assertEqual(dog['labels'][0]['label'],'Samoyed')
        self.assertGreater(dog['labels'][0]['confidence'],.6)
        self.assertTrue(any(o['label']=='dog' for o in dog['objects']))
        self.assertTrue(any(o['label']=='person' and o['confidence']>.6 for o in person['objects']))


if __name__=='__main__':unittest.main()
