import logging
import os

import django.http
import django.template.loader

from infinitemachine import settings
from infinitemachine import util
from infinitemachine.wiki import cache
from infinitemachine.wiki import document
from infinitemachine.wiki import render


@util.log_elapsed_total
def index(request, docname):
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(levelname)s - %(message)s')
  rendered = render.cachedRender(docname)
  response = django.http.HttpResponse(rendered, status=200)
  return response


def handler404(request):
  authors = [x[0] for x in settings.MANAGERS]
  path_info = request.META['PATH_INFO']
  values = {'path_info': path_info,
            'settings': settings,
            'site_title': getattr(settings, 'SITE_TITLE', ''),
            'author': ', '.join(authors)}
  rendered = django.template.loader.render_to_string('404.html', values)
  response = django.http.HttpResponse(rendered, status=404)
  return response


def handler500(request):
  authors = [x[0] for x in settings.MANAGERS]
  path_info = request.META['PATH_INFO']
  values = {'path_info': path_info,
            'settings': settings,
            'site_title': getattr(settings, 'SITE_TITLE', ''),
            'author': ', '.join(authors)}
  rendered = django.template.loader.render_to_string('500.html', values)
  response = django.http.HttpResponse(rendered, status=500)
  return response
