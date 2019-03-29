import os
import sys

from BER import PageHandler, init_site

import tornado.web
from tornado.testing import AsyncHTTPTestCase


# add application root to sys.path
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(APP_ROOT, '..'))


class TestApplication(tornado.web.Application):

    def __init__(self):

        base_path = os.path.abspath('.')
        site_path = os.path.join(base_path, "tests", "site")
        settings = dict(
            template_path=os.path.join(site_path, "templates"),
            snippet_path=os.path.join(site_path, "snippets"),
            static_path=os.path.join(site_path, "assets"),
            static_url_prefix='/assets/',
            data_path=os.path.join(site_path, "data"),
            site=init_site(os.path.join(site_path, "site.yaml")),
            force_https=False,
            secure_headers={
                'X-Frame-Options': 'DENY',
                'X-Fake-Secure-Header': 'fake'}
        )

        handlers = [(r"/assets/(.*)",
                     tornado.web.StaticFileHandler,
                     dict(path=settings['static_path'])),
                    (r"(/[a-z0-9\-_\/\.]*)$", PageHandler)]

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

        expected_title = b'<title>Index - BER Test Site</title>'
        self.assertIn(expected_title, response.body)

        expected_h1 = b'<h1>Index</h1>'
        self.assertIn(expected_h1, response.body)

    def test_css_assets(self):
        """ test that the Jinja2 and Webassets integration works, that our
        custom stylesheet_tag works and that css assets are served correctly
        by Tornado """

        response = self.fetch('/', method='GET')
        self.assertEqual(200, response.code)

        # CSS
        expected_stylesheet_regexp = rb'<link type="text/css" rel="stylesheet" media="screen" href="/assets/dist/css/style.css[\?v=a-z0-9]*">'  # noqa: E501
        print(response.body)
        self.assertRegexpMatches(response.body, expected_stylesheet_regexp)

        css_response = self.fetch(
            '/assets/dist/css/style.css',
            method='GET')
        self.assertEqual(200, css_response.code)
        self.assertEqual(
            'text/css', css_response.headers['Content-Type'])

        expected_css = b'''body {
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
        expected_script_regexp = rb'<script type="text/javascript" src="/assets/dist/js/app.js[\?v=a-z0-9]*"></script>'  # noqa: E501
        self.assertRegexpMatches(response.body, expected_script_regexp)

        js_response = self.fetch(
            '/assets/dist/js/app.js',
            method='GET')
        self.assertEqual(200, js_response.code)
        self.assertEqual(
            'application/javascript', js_response.headers['Content-Type'])

        expected_js = b'''var test_var = true'''
        self.assertIn(expected_js, js_response.body)

    def test_markdown_filter(self):
        response = self.fetch('/markdown', method='GET')

        self.assertEqual(200, response.code)
        self.assertEqual(b'<h1>Markdown Test</h1>\n', response.body)

    def test_unpublished_page(self):
        """ test that pages marked as unpublished return 404 """

        response = self.fetch('/unpublished', method='GET')
        self.assertEqual(404, response.code)

    def test_page_with_data_sources(self):
        """ test that data sources are made available to the template """

        response = self.fetch('/data-sources', method='GET')
        self.assertEqual(200, response.code)

        expected_li_1 = b'<li>key1: value1</li>'
        self.assertIn(expected_li_1, response.body)

        expected_li_2 = b'<li>key2: value2</li>'
        self.assertIn(expected_li_2, response.body)

        expected_li_3 = b'<li>id: 1</li>'
        self.assertIn(expected_li_3, response.body)

    def test_data_source_errors(self):
        response = self.fetch('/data-source-404', method='GET')
        self.assertEqual(404, response.code)

    def test_autodetected_and_overwritten_templates(self):
        """ test that pages specifying the tpl_name attribute get the correct
        template """

        autodetect = self.fetch('/test-tpl-name-autodetect', method='GET')
        self.assertEqual(200, autodetect.code)
        overwrite = self.fetch('/test-tpl-name-overwrite', method='GET')
        self.assertEqual(200, overwrite.code)

        self.assertEqual(autodetect.body, overwrite.body)

    def test_wildcard_slugs_3_levels(self):

        response = self.fetch('/test-wildcard_slugs/a/b/c/test', method='GET')
        self.assertEqual(200, response.code)

        expected_h1 = b'<h1>/test-wildcard_slugs/a/b/c/test</h1>'
        self.assertIn(expected_h1, response.body)

    def test_wildcard_slugs_2_levels(self):

        response = self.fetch('/test-wildcard_slugs/a/b/test', method='GET')
        self.assertEqual(200, response.code)

        expected_h1 = b'<h1>/test-wildcard_slugs/a/b/test</h1>'
        self.assertIn(expected_h1, response.body)

    def test_wildcard_slugs_1_level(self):

        response = self.fetch('/test-wildcard_slugs/a/test', method='GET')
        self.assertEqual(200, response.code)

        expected_h1 = b'<h1>/test-wildcard_slugs/a/test</h1>'
        self.assertIn(expected_h1, response.body)

    def test_site_yaml_template_support(self):

        response = self.fetch('/test-site-yaml-template-support', method='GET')
        self.assertEqual(200, response.code)

        expected_h1 = b'<h1>set with jinja2</h1>'
        self.assertIn(expected_h1, response.body)

    def test_secure_headers_defaults(self):

        response = self.fetch('/', method='GET')
        self.assertEqual(200, response.code)

        secure_headers = [
            'X-Frame-Options',
            'X-XSS-Protection',
            'X-Content-Type-Options',
            'X-Permitted-Cross-Domain-Policies']
        for h in secure_headers:
            self.assertIn(h, response.headers)

    def test_secure_headers_settings_overwrite_defaults(self):

        response = self.fetch('/', method='GET')
        self.assertEqual(200, response.code)

        self.assertEqual(
            response.headers['X-Frame-Options'], 'DENY')

    def test_secure_headers_added_in_settings_not_in_defaults(self):

        response = self.fetch('/', method='GET')
        self.assertEqual(200, response.code)

        self.assertEqual(
            response.headers['X-Fake-Secure-Header'], 'fake')

    def test_custom_content_type(self):

        response = self.fetch('/sitemap.xml', method='GET')
        self.assertEqual(200, response.code)
        self.assertEqual(response.headers['Content-Type'], 'application/xml')

    def test_redirect(self):

        response = self.fetch(
            '/test-redirect', method='GET', follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual(response.headers['Location'], '/')

    def test_redirect_perm(self):

        response = self.fetch(
            '/test-redirect-perm', method='GET', follow_redirects=False)
        self.assertEqual(301, response.code)
        self.assertEqual(response.headers['Location'], '/')
