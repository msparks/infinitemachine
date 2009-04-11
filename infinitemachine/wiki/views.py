import logging
import os

import django.http
import django.template.loader

from infinitemachine import settings
from infinitemachine import util
from infinitemachine.wiki import document


@util.log_elapsed_total
@util.cached
def _render(docname, template=None):
  if template is None:
    template = 'index.html'

  doc = document.Document(docname)
  if not doc.exists():
    raise django.http.Http404

  authors = [x[0] for x in settings.MANAGERS]
  values = {'document': doc,
            'toplevel': docname.split('/')[0],
            'settings': settings,
            'title': doc.title(),
            'title_shortname': document.header_short_name(doc.title()),
            'site_title': getattr(settings, 'SITE_TITLE', ''),
            'author': ', '.join(authors)}

  rendered = django.template.loader.render_to_string(template, values)
  return rendered


@util.log_elapsed_total
def index(request, docname):
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(levelname)s - %(message)s')
  response = django.http.HttpResponse(_render(docname), status=200)
  return response


def handler404(request):
  path_info = request.META['PATH_INFO']
  rendered = django.template.loader.render_to_string('404.html',
                                                     {'page_title': '404'})
  response = django.http.HttpResponse(rendered, status=404)
  return response


def handler500(request):
  rendered = django.template.loader.render_to_string('404.html',
                                                     {'page_title': '500'})
  response = django.http.HttpResponse(rendered, status=404)
  return response
