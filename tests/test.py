import unittest
import os
import os.path
import sys
import json

from mock import patch
from tornado.testing import AsyncHTTPTestCase, gen_test

# add application root to sys.path
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(APP_ROOT, '..'))

# import your app module
import geoipapi.web

# Create your Application for testing
app = geoipapi.web.Application()


class TestHandlerBase(AsyncHTTPTestCase):

    def get_app(self):
        return app


class TestBucketHandler(TestHandlerBase):

    def test_no_ip(self):
        response = self.fetch('/v1', method='GET')

        self.assertEqual(response.code, 404)

    def test_invalid_ip(self):
        response = self.fetch('/v1/127.0.', method='GET')
        self.assertEqual(response.code, 404)

    def test_unknown_ip(self):
        response = self.fetch('/v1/127.0.0.1', method='GET')
        self.assertEqual(response.code, 404)

    def test_valid_ips(self):
        ips = ['31.135.220.58',
               '84.200.69.55',
               '87.130.66.243',
               '128.101.101.101']

        for ip in ips:
            response = self.fetch('/v1/{}'.format(ip), method='GET')

            data = json.loads(response.body)

            self.assertEqual(response.code, 200)
            self.assertEquals(response.headers['Content-Type'],
                'application/json; charset="utf-8"')

            self.assertIsInstance(data, dict)
            self.assertIn('ip', data)
            self.assertIn('country', data)
            self.assertIn('continent', data)
            self.assertIn('code', data['country'])
            self.assertIn('name', data['country'])
            self.assertIn('code', data['continent'])
            self.assertIn('name', data['continent'])

    def test_cors_header(self):
        response = self.fetch('/v1/{}'.format('128.101.101.101'), method='GET')

        self.assertEquals(response.headers['Access-Control-Allow-Headers'],
                'X-Requested-With, Content-Type, Content-Length, Accept')
        self.assertEquals(response.headers['Access-Control-Allow-Methods'],
                'GET')
        self.assertEquals(response.headers['Access-Control-Allow-Origin'],
                '*')

