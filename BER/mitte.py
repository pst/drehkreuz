#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from time import strftime

import yaml
import tornado.web
import tornado.httpserver
import tornado.httpclient
import tornado.gen
import feedparser
from jinja2 import Environment as JinjaEnvironment, FileSystemLoader
from webassets import Environment as AssetsEnvironment
from webassets.ext.jinja2 import AssetsExtension
from webassets.filter import register_filter
from webassets_libsass import LibSass


class EngineMixin(object):

    def initialize(self):
        loader = FileSystemLoader([
            self.settings['template_path'],
            self.settings['snippet_path']])
        assets_env = AssetsEnvironment(
            self.settings['static_path'], self.static_url(''))
        register_filter(LibSass)
        self.template_env = JinjaEnvironment(
            loader=loader, extensions=[AssetsExtension])
        
        self.template_env.assets_environment = assets_env

        self.template_env.filters['stylesheet_tag'] = self.stylesheet_tag
        self.template_env.filters['javascript_tag'] = self.javascript_tag
        self.template_env.filters['theme_image_url'] = self.theme_image_url
        self.template_env.filters['strftime'] = self.strftime

        self.template_env.globals.update(self.get_globals())

        self.site = self.settings['site']
        self.client = tornado.httpclient.AsyncHTTPClient()

    def stylesheet_tag(self, name):
        href = name
        if not name.startswith('http'):
            href = self.static_url(name)
        return '<link type="text/css" rel="stylesheet" media="screen" href="{0}">'.format(href)

    def javascript_tag(self, name):
        src = name
        if not name.startswith('http'):
            src = self.static_url(name)
        return '<script type="text/javascript" src="{0}"></script>'.format(src)

    def theme_image_url(self, name):
        src = name
        if not name.startswith('http'):
            src = self.static_url(name)
        return '{0}'.format(src)

    def strftime(self, time_struct, format):
        return strftime(format, time_struct)

    def get_globals(self):
        globals = {
            'site_env': os.environ.get('SITE_ENV', 'production'),
            'arguments': self.request.arguments,
            'host': self.request.host,
            'remote_ip': self.request.remote_ip,
            'path': self.request.path,
            'uri': self.request.uri,
            'method': self.request.method}
        return globals

    @tornado.gen.coroutine
    def get_data(self, source, slug=None):
        data = None
        src = source['src']

        if slug:
            src = src.format(slug)

        if src.startswith('http'):
            request = tornado.httpclient.HTTPRequest(src)
            response = yield tornado.gen.Task(self.client.fetch, request)
            data = response.body
        else:
            path = os.path.join(self.settings['data_path'], src)
            with open(path) as f:
                data = f.read()

        if source['format'] == 'json':
            parsed_data = json.loads(data)
        elif source['format'] == 'yaml':
            parsed_data = yaml.load(data)
        elif source['format'] == 'rss':
            parsed_data = feedparser.parse(data)

 
        raise tornado.gen.Return(parsed_data)

    def get_page(self, slug):
        pages = self.site['pages']

        if slug in pages:
            return slug, pages[slug]

        wildcard_slugs = []
        slug_split = slug.split('/')
        slug_length = len(slug_split)
        if slug_length > 2:
            for i in range(1, slug_length - 1):
                wcs = "/{0}/*".format('/'.join(slug_split[1:-i]))
                wildcard_slugs.append(wcs)
            for wildcard_slug in wildcard_slugs:
                if wildcard_slug in pages:
                    return wildcard_slug, pages[wildcard_slug]

        raise tornado.web.HTTPError(404)

    def get_template_by_slug(self, slug):
        tpl_name = slug
        if slug.endswith('/'):
            tpl_name += 'index.html'
        else:
            tpl_name += '.html'
        return self.get_template(tpl_name)

    def get_template(self, tpl_name):
        return self.template_env.get_template(tpl_name)
