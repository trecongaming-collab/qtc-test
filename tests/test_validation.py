import tempfile
import unittest
from pathlib import Path
from app.engine import ff
from app.validation import content_metrics


class ExportContent(unittest.TestCase):
    def test_real_image_and_audible_audio(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'valid.mp4'
            ff('-f','lavfi','-i','testsrc2=s=96x160:r=30:d=2','-f','lavfi','-i','sine=f=220:r=48000:d=2',
               '-c:v','libx264','-threads',2,'-c:a','aac','-shortest',path)
            result=content_metrics(path,2)
            self.assertTrue(result['picture_and_sound_checked'])
            self.assertGreater(result['audio_rms'],.001)

    def test_black_frame_not_accepted_as_a_valid_picture(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'black.mp4'
            ff('-f','lavfi','-i','color=black:s=96x160:r=30:d=2','-f','lavfi','-i','sine=f=220:r=48000:d=2',
               '-c:v','libx264','-threads',2,'-c:a','aac','-shortest',path)
            with self.assertRaisesRegex(ValueError,'ảnh phẳng'):content_metrics(path,2)

    def test_silent_export_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'silent.mp4'
            ff('-f','lavfi','-i','testsrc2=s=96x160:r=30:d=2','-f','lavfi','-i','anullsrc=r=48000:cl=mono',
               '-t',2,'-c:v','libx264','-threads',2,'-c:a','aac',path)
            with self.assertRaisesRegex(ValueError,'RMS'):content_metrics(path,2)

if __name__=='__main__':unittest.main()
