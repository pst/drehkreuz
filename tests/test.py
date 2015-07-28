import unittest
import os
import sys
import logging

import tornado.web
from mock import patch
from tornado.testing import AsyncHTTPTestCase, gen_test

from BER import init_site, PageHandler

# add application root to sys.path
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(APP_ROOT, '..'))

class TestApplication(tornado.web.Application):

    def __init__(self):

        base_path = os.path.abspath('.')
        settings = dict(
            template_path=os.path.join(base_path, "tests", "site", "templates"),
            snippet_path=os.path.join(base_path, "tests", "site", "snippets"),
            static_path=os.path.join(base_path, "tests", "site", "assets"),
            static_url_prefix='/assets/',
            data_path=os.path.join(base_path, "tests", "site", "data"),
            site=init_site(os.path.join(base_path, "tests", "site", "site.yaml")),
            force_https=False
        )

        log = logging.getLogger('tornado.application')

        handlers = [(r"/assets/(.*)",
                        tornado.web.StaticFileHandler,
                        dict(path=settings['static_path'])),
                    (r"(/[a-z0-9\-_\/]*)$", PageHandler)]

        tornado.web.Application.__init__(self, handlers, **settings)

test_app = TestApplication()


class TestHandlerBase(AsyncHTTPTestCase):

    def get_app(self):
        return test_app


class TestPageHandler(TestHandlerBase):

    def test_index_page(self):
        """ test that the correct template was picked, that Jinja2 was
        initialized correctly and that `site` and `page` are available in the
        template """

        response = self.fetch('/', method='GET')

        self.assertEqual(200, response.code)

        expected_title = '<title>Index - BER Test Site</title>'
        self.assertIn(expected_title, response.body)

        expected_h1 = '<h1>Index</h1>'
        self.assertIn(expected_h1, response.body)

    def test_css_assets(self):
        """ test that the Jinja2 and Webassets integration works, that our
        custom stylesheet_tag works and that css assets are served correctly
        by Tornado """

        response = self.fetch('/', method='GET')
        self.assertEqual(200, response.code)

        # CSS
        expected_stylesheet_regexp = r'<link type="text/css" rel="stylesheet" media="screen" href="/assets/dist/css/style.css[\?v=a-z0-9]*">'
        self.assertRegexpMatches(response.body, expected_stylesheet_regexp)

        css_response = self.fetch(
            '/assets/dist/css/style.css',
            method='GET')
        self.assertEqual(200, css_response.code)
        self.assertEqual(
            'text/css', css_response.headers['Content-Type'])

        expected_css = '''body {
  font: 100% Helvetica, sans-serif;
  color: #333; }
'''
        self.assertEqual(expected_css, css_response.body)

    def test_js_assets(self):
        """ test that the Jinja2 and Webassets integration works, that our
        custom javascript_tag works and that js assets are served correctly
        by Tornado """

        response = self.fetch('/', method='GET')
        self.assertEqual(200, response.code)

        # JS
        expected_script_regexp = r'<script type="text/javascript" src="/assets/dist/js/app.js[\?v=a-z0-9]*"></script>'
        self.assertRegexpMatches(response.body, expected_script_regexp)

        js_response = self.fetch(
            '/assets/dist/js/app.js',
            method='GET')
        self.assertEqual(200, js_response.code)
        self.assertEqual(
            'application/javascript', js_response.headers['Content-Type'])

        expected_js = '''var test_var = true'''
        self.assertIn(expected_js, js_response.body)

    def test_unpublished_page(self):
        """ test that pages marked as unpublished return 404 """

        response = self.fetch('/unpublished', method='GET')
        self.assertEqual(404, response.code)

    def test_page_with_data_sources(self):
        """ test that data sources are made available to the template """

        response = self.fetch('/data-sources', method='GET')
        self.assertEqual(200, response.code)

        expected_li_1 = '<li>key1: value1</li>'
        self.assertIn(expected_li_1, response.body)

        expected_li_2 = '<li>key2: value2</li>'
        self.assertIn(expected_li_2, response.body)

    def test_autodetected_and_overwritten_templates(self):
        """ test that pages specifying the tpl_name attribute get the correct
        template """

        autodetect = self.fetch('/test-tpl-name-autodetect', method='GET')
        self.assertEqual(200, autodetect.code)
        overwrite = self.fetch('/test-tpl-name-overwrite', method='GET')
        self.assertEqual(200, overwrite.code)

        self.assertEqual(autodetect.body, overwrite.body)
