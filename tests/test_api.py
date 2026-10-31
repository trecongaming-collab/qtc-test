import unittest
from fastapi.testclient import TestClient
from app.main import app


class API(unittest.TestCase):
    def setUp(self):self.client=TestClient(app)
    def test_home_health_and_config(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertTrue(self.client.get('/api/health').json()['ok'])
        config=self.client.get('/api/config').json()
        self.assertEqual(len(config['styles']),5)
        self.assertIn('4k',config['resolutions'])
        self.assertEqual(config['min_ai_videos'],5)
        self.assertFalse(config['ai']['media_upload_to_third_party'])

    def test_invalid_duration_extension_and_style(self):
        for data,name in [({'duration':14,'mode':'classic'},'x.mp4'),({'mode':'classic'},'../../bad.exe'),({'style':'made-up','mode':'classic'},'x.mp4')]:
            response=self.client.post('/api/jobs',data=data,files={'videos':(name,b'test')})
            self.assertEqual(response.status_code,422)

    def test_ai_requires_five_videos_and_music(self):
        response=self.client.post('/api/jobs',files={'videos':('x.mp4',b'test')})
        self.assertEqual(response.status_code,422)
        response=self.client.post('/api/jobs',files=[('videos',(f'{i}.mp4',b'test')) for i in range(5)])
        self.assertEqual(response.status_code,422)
        self.assertIn('nhạc',response.json()['detail'])

    def test_total_body_limit(self):
        from app.main import MAX_TOTAL
        response=self.client.post('/api/jobs',content=b'x',headers={'Content-Length':str(MAX_TOTAL+3*1024**2)})
        self.assertEqual(response.status_code,413)

    def test_unknown_job_and_invalid_regenerate(self):
        self.assertEqual(self.client.get('/api/jobs/not-a-uuid').status_code,404)
        base='/api/jobs/00000000-0000-0000-0000-000000000000'
        self.assertEqual(self.client.get(base+'/video').status_code,404)
        self.assertEqual(self.client.post(base+'/regenerate',json={}).status_code,404)
        self.assertEqual(self.client.post(base+'/regenerate',json={'style':'made-up'}).status_code,422)

if __name__=='__main__':unittest.main()
