import json
import tempfile
import unittest
from pathlib import Path

from app.engine import ff, music_grid, plan, probe, render


def candidate(i, score=5):
    return dict(source=i%2,start=(i//2)*4,score=score,sharp=100,exposure=.9,motion=3,signature=[i*.08]*108)


class Planning(unittest.TestCase):
    def test_no_repeated_intervals_and_exact_duration(self):
        candidates=[candidate(i,20-i) for i in range(20)]
        shots=plan(candidates,[{'duration':60}]*2,36,100,0)
        self.assertAlmostEqual(sum(s['length'] for s in shots),36)
        self.assertEqual(len(shots),len({(s['source'],s['start']) for s in shots}))
        self.assertEqual(shots[0]['score'],20)
        for s in shots[1:]: self.assertAlmostEqual(s['timeline']/.6,round(s['timeline']/.6))

    def test_duplicate_and_bad_footage_rejected(self):
        with self.assertRaisesRegex(ValueError,'Không đủ cảnh khác biệt'):
            plan([candidate(0)]*20,[{'duration':60}]*2,30,100,0)
        bad=candidate(0); bad['exposure']=.1
        with self.assertRaisesRegex(ValueError,'ngưỡng'):
            plan([bad],[{'duration':60}]*2,30,100,0)

    def test_music_onset_grid(self):
        import numpy as np
        import wave
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'click.wav'; t=np.arange(8000*12)/8000
            signal=np.sin(2*np.pi*180*t)*np.exp(-np.mod(t,.5)*65)*.3
            with wave.open(str(p),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes((signal*32767).astype('<i2').tobytes())
            bpm,phase,note=music_grid(p,Path(d),12)
            self.assertAlmostEqual(bpm,120,delta=5)


class Integration(unittest.TestCase):
    def test_insufficient_duration_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d); source=folder/'short.mp4'
            ff('-f','lavfi','-i','testsrc2=s=96x160:r=15:d=0.8','-c:v','libx264','-threads',2,source)
            with self.assertRaisesRegex(ValueError,'chưa đủ dựng'):
                render([source],None,folder,30,False,False,lambda *args:None,width=180,height=320)

    def test_render_actual_h264_and_aac_with_both_audio_paths(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            source=folder/'source.mp4'
            ff('-f','lavfi','-i','testsrc2=s=160x284:r=15:d=100','-vf',"eq=brightness='-0.35+0.028*floor(t/4)':eval=frame",'-c:v','libx264','-preset','ultrafast',source)
            messages=[]
            report=render([source],None,folder,30,True,True,lambda p,m:messages.append(p),width=180,height=320)
            output=probe(folder/'result.mp4')
            self.assertEqual(output['video']['codec_name'],'h264')
            self.assertEqual(output['video']['r_frame_rate'],'30/1')
            self.assertEqual(output['video']['width'],180)
            self.assertTrue(output['audio'])
            self.assertAlmostEqual(output['duration'],30,delta=.15)
            self.assertTrue(any(s['ramp'] for s in report['selected']))
            self.assertGreater(messages[-1],85)
            # Second pass: input audio + uploaded music + no speed ramp.
            with_audio=folder/'audio-source.mp4'
            ff('-i',source,'-f','lavfi','-i','sine=f=340:r=48000:d=100','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-shortest',with_audio)
            music=folder/'ambient.wav'
            second=folder/'second';second.mkdir()
            render([with_audio],music,second,31,True,True,lambda *a:None,width=180,height=320)
            self.assertAlmostEqual(probe(second/'result.mp4')['duration'],31,delta=.15)


if __name__=='__main__': unittest.main()
