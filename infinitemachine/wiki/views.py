import logging
import os

import django.http
import django.template.loader

from infinitemachine import settings
from infinitemachine import util
from infinitemachine.wiki import cache
from infinitemachine.wiki import document


@util.log_elapsed_total
def _render(docname, template=None):
  if template is None:
    template = 'index.html'

  # attempt to fetch document from cache
  rendered = cache.get(docname)
  if rendered is not None:
    return rendered

  # load document from disk
  doc = document.Document(docname)
  if not doc.exists():
    raise django.http.Http404

  if not settings.DEBUG:
    analytics_id = getattr(settings, 'ANALYTICS_ID', None)
  else:
    analytics_id = None

  authors = [x[0] for x in settings.MANAGERS]
  values = {'document': doc,
            'toplevel': docname.split('/')[0],
            'settings': settings,
            'title': doc.title(),
            'title_shortname': document.header_short_name(doc.title()),
            'site_title': getattr(settings, 'SITE_TITLE', ''),
            'author': ', '.join(authors),
            'analytics_id': analytics_id}

  rendered = django.template.loader.render_to_string(template, values)
  cache.set(docname, rendered)

  return rendered


@util.log_elapsed_total
def index(request, docname):
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(levelname)s - %(message)s')
  response = django.http.HttpResponse(_render(docname), status=200)
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
