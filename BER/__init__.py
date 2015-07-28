import yaml
from functools import wraps

import tornado.web
from jinja2 import TemplateNotFound

from mitte import EngineMixin

def force_https(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print 'before setting'
        if not args[0].settings.get('force_https', True):
            print 'after setting'
            return f(*args, **kwargs)

        print 'before localhost'
        if args[0].request.host.startswith('localhost:'):
            print 'after localhost'
            return f(*args, **kwargs)

        print 'before protocol https'
        if not args[0].request.protocol == 'https':
            print 'after protocol https'
            args[0].redirect(
                'https://{0}{1}'.format(
                    args[0].request.host, args[0].request.uri),
                permanent=True)
        return f(*args, **kwargs)

    return wrapper

def init_site(site_path):
    with open(site_path) as f:
        site = yaml.load(f)

    return site

class PageHandler(EngineMixin, tornado.web.RequestHandler):

    def write_error(self, status_code, **kwargs):
        slug = "/{}".format(status_code)
        try:
            page_slug, page = self.get_page(slug)
            template = self.get_template('{0}.html'.format(status_code))
        except tornado.web.HTTPError or TemplateNotFound:
            super(PageHandler, self).write_error(status_code, **kwargs)
        else:
            error_response = template.render(site=self.site, page=page)

            self.write(error_response)
            self.finish()

    @force_https
    @tornado.web.removeslash
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, slug=None):
        page_slug, page = self.get_page(slug)

        data_sources = {}
        if 'data_sources' in page:
            sources = page['data_sources']
            for name in sources:
                source_slug = slug[len(page_slug.strip('*')):]
                data = yield self.get_data(sources[name], slug=source_slug)
                data_sources[name] = data

        if 'published' in page and page['published'] == False:
            raise tornado.web.HTTPError(404)

        if 'tpl_name' in page:
            template = self.get_template(page['tpl_name'])
        else:
            template = self.get_template_by_slug(slug)

        response = template.render(site=self.site, page=page, **data_sources)

        self.write(response)
        self.finish()
