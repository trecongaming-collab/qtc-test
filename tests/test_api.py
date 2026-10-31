import unittest
from fastapi.testclient import TestClient
from app.main import app

class API(unittest.TestCase):
    def setUp(self): self.client=TestClient(app)
    def test_home_and_health(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertTrue(self.client.get('/api/health').json()['ok'])
    def test_invalid_duration_and_extension(self):
        r=self.client.post('/api/jobs',data={'duration':29},files={'videos':('x.mp4',b'test','video/mp4')})
        self.assertEqual(r.status_code,422)
        r=self.client.post('/api/jobs',files={'videos':('../../bad.exe',b'test')})
        self.assertEqual(r.status_code,422)
    def test_unknown_job_and_traversal(self):
        self.assertEqual(self.client.get('/api/jobs/not-a-uuid').status_code,404)
        self.assertEqual(self.client.get('/api/jobs/00000000-0000-0000-0000-000000000000/video').status_code,404)

if __name__=='__main__': unittest.main()
