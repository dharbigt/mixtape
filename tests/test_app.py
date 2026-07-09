# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from app import create_app


class AppSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_public_index_renders(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_admin_requires_authentication(self) -> None:
        response = self.client.get('/admin', follow_redirects=False)
        self.assertIn(response.status_code, (302, 401))

    def test_login_page_renders(self) -> None:
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
