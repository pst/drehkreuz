#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from time import strftime, time

import feedparser

from jinja2 import (Environment as JinjaEnvironment,
                    FileSystemBytecodeCache,
                    FileSystemLoader,
                    Markup)

import misaka

from prometheus_client import Summary

import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.web

from webassets import Environment as AssetsEnvironment
from webassets.ext.jinja2 import AssetsExtension
from webassets.filter import register_filter
from webassets.filter.libsass import LibSass

import yaml


class EngineMixin(object):
    get_data_time = Summary('get_data_time',
                            'Time spent getting data.',
                            ['src', 'format'])

    def initialize(self):
        loader = FileSystemLoader([
            self.settings['template_path'],
            self.settings['snippet_path']])
        assets_env = AssetsEnvironment(
            self.settings['static_path'], self.static_url(''))
        register_filter(LibSass)

        self.template_env = JinjaEnvironment(
            loader=loader,
            extensions=[AssetsExtension],
            bytecode_cache=FileSystemBytecodeCache())

        self.template_env.assets_environment = assets_env

        self.template_env.filters['stylesheet_tag'] = self.stylesheet_tag
        self.template_env.filters['javascript_tag'] = self.javascript_tag
        self.template_env.filters['theme_image_url'] = self.theme_image_url
        self.template_env.filters['strftime'] = self.strftime
        self.template_env.filters['markdown'] = self.markdown

        self.template_env.globals.update(self.get_globals())

        self.site = self.settings['site']
        self.client = tornado.httpclient.AsyncHTTPClient()

    def stylesheet_tag(self, name):
        href = name
        if not name.startswith('http'):
            href = self.static_url(name)
        return ('<link type="text/css"'
                ' rel="stylesheet"'
                ' media="screen"'
                ' href="{0}">'.format(href))

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

    def markdown(self, text, ctx=dict()):
        md = misaka.Markdown(
            misaka.HtmlRenderer(),
            extensions=('fenced-code',))
        tpl = JinjaEnvironment().from_string(text)
        print(ctx)
        return Markup(md(tpl.render(**ctx)))

    def get_globals(self):
        globals = {
            'site_env': os.environ.get('SITE_ENV', 'production'),
            'arguments': self.request.arguments,
            'host': self.request.host,
            'remote_ip': self.request.remote_ip,
            'path': self.request.path,
            'uri': self.request.uri,
            'method': self.request.method,
            'protocol': self.request.protocol}
        return globals

    @tornado.gen.coroutine
    def get_data_remote(self, src):
        request = tornado.httpclient.HTTPRequest(src)
        try:
            response = yield self.client.fetch(request)
        except tornado.httpclient.HTTPClientError as e:
            raise tornado.web.HTTPError(e.code)
        return response.body

    @tornado.gen.coroutine
    def get_data_local(self, src):
        path = os.path.join(self.settings['data_path'], src)
        try:
            with open(path) as f:
                return f.read()
        except IOError:
            raise tornado.web.HTTPError(404)

    def parse_data(self, format, data):
        if format == 'json':
            parsed_data = json.loads(data)
        elif format == 'yaml':
            parsed_data = yaml.safe_load(data)
        elif format == 'rss':
            parsed_data = feedparser.parse(data)
        return parsed_data

    @tornado.gen.coroutine
    def get_data(self, source, named_groups=None):
        start_time = time()
        data = None
        src = source['src']
        format = source['format']

        if named_groups:
            src = src.format(**named_groups)

        if src.startswith('http'):
            data = yield self.get_data_remote(src)
        else:
            data = yield self.get_data_local(src)

        parsed_data = self.parse_data(format, data)

        time_delta = time() - start_time
        self.get_data_time.labels(src, format).observe(time_delta)

        return parsed_data

    def get_page(self, slug):
        routes = self.site['routes']
        pages = self.site['pages']

        for route in routes:
            match = route.fullmatch(slug)
            if match:
                named_groups = {
                    k: match.groups()[v-1]
                    for k, v in route.groupindex.items()}
                return route.pattern, pages[route.pattern], named_groups

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
