import json
import unittest

from calculator import server


class ServerEndpointsTest(unittest.TestCase):
    def setUp(self):
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()

    def test_index_returns_html(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('text/html', rv.content_type)

    def test_static_file_served(self):
        rv = self.client.get('/static/css/styles.css')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue('text/css' in rv.content_type or 'text/plain' in rv.content_type)
        # Ensure any underlying file handles are released to avoid ResourceWarning
        try:
            rv.close()
        except Exception:
            pass

    def test_maps_list_endpoint(self):
        rv = self.client.get('/maps/list')
        # If processed_maps doesn't exist the endpoint returns 404 with an error
        if not server.PROCESSED_MAPS_DIR.is_dir():
            self.assertEqual(rv.status_code, 404)
            data = rv.get_json()
            self.assertIn('error', data)
        else:
            self.assertEqual(rv.status_code, 200)
            data = rv.get_json()
            self.assertIn('maps', data)
            self.assertIsInstance(data['maps'], list)

    def test_serve_map_data_404(self):
        rv = self.client.get('/maps/this_map_does_not_exist/metadata.json')
        self.assertEqual(rv.status_code, 404)


if __name__ == '__main__':
    unittest.main()
