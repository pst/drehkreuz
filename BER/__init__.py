import os
from functools import wraps
from re import compile

from jinja2 import Environment, TemplateNotFound

import tornado.web

import yaml

from .mitte import EngineMixin


def force_https(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not args[0].settings.get('force_https', True):
            return f(*args, **kwargs)

        if args[0].request.host.startswith('localhost:'):
            return f(*args, **kwargs)

        if not args[0].request.protocol == 'https':
            args[0].redirect(
                'https://{0}{1}'.format(
                    args[0].request.host, args[0].request.uri),
                permanent=True)
            raise tornado.web.Finish()
        return f(*args, **kwargs)

    return wrapper


def secure_headers(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        defaults = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'X-Content-Type-Options': 'nosniff',
            'X-Permitted-Cross-Domain-Policies': 'none'}

        secure_headers = args[0].settings.get('secure_headers', defaults)

        for d in defaults:
            if d not in secure_headers:
                secure_headers[d] = defaults[d]

        if args[0].request.protocol == 'https':
            if 'Strict-Transport-Security' not in secure_headers:
                secure_headers['Strict-Transport-Security'] = 'max-age=631152000; includeSubdomains'  # max-age 20 years  # noqa: E501

        for h in secure_headers:
            args[0].add_header(h, secure_headers[h])

        return f(*args, **kwargs)

    return wrapper


def init_site(site_path):
    with open(site_path) as f:
        t = Environment().from_string(f.read())
        site = yaml.full_load(t.render(environ=os.environ))

    site['routes'] = list(map(lambda page: compile(page), site['pages']))

    return site


class PageHandler(EngineMixin, tornado.web.RequestHandler):

    def write_error(self, status_code, **kwargs):
        # default to status_code template
        tpl_name = f'{status_code}.html'
        page = None
        try:
            # try to get custom error page from site.yaml
            _, page, _ = self.get_page(f"/{status_code}")
        except tornado.web.HTTPError:
            # if site.yaml doesn't have a page for this error code
            pass
        else:
            # overwrite with page's template if set
            if 'tpl_name' in page:
                tpl_name = page['tpl_name']

        try:
            template = self.get_template(tpl_name)
        except TemplateNotFound:
            # fall back to Tornado default error page
            super(PageHandler, self).write_error(status_code, **kwargs)
        else:
            # return our custom error page
            error_response = template.render(site=self.site, page=page)
            self.finish(error_response)

    @tornado.web.removeslash
    @secure_headers
    @force_https
    def prepare(self):
        pass

    @tornado.gen.coroutine
    def get(self, slug=None):
        page_slug, page, named_groups = self.get_page(slug)

        if 'redirect' in page:
            perm = False
            if 'permanent' in page['redirect']:
                perm = page['redirect']['permanent']
            self.redirect(page['redirect']['target'], perm)
            raise tornado.web.Finish()

        data_sources = {}
        if 'data_sources' in page:
            sources = page['data_sources']
            for name in sources:
                data = yield self.get_data(sources[name],
                                           named_groups=named_groups)
                data_sources[name] = data

        if 'published' in page and page['published'] is False:
            raise tornado.web.HTTPError(404)

        if 'content-type' in page:
            self.set_header("Content-Type", page['content-type'])

        if 'tpl_name' in page:
            template = self.get_template(page['tpl_name'])
        else:
            template = self.get_template_by_slug(slug)

        response = template.render(site=self.site, page=page, **data_sources)

        self.finish(response)
