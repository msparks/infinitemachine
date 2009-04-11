import logging
import os

import django.http
import django.template.loader

from infinitemachine import settings
from infinitemachine import util
from infinitemachine.wiki import document


BLOG_BASE = 'blog'


@util.log_elapsed_total
@util.cached
def _render(entries, template=None):
  if template is None:
    template = 'blog.html'

  authors = [x[0] for x in settings.MANAGERS]
  values = {'entries': entries,
            'toplevel': BLOG_BASE,
            'settings': settings,
            'title': 'Blog',
            'site_title': getattr(settings, 'SITE_TITLE', ''),
            'author': ', '.join(authors)}

  rendered = django.template.loader.render_to_string(template, values)
  return rendered


@util.log_elapsed_total
def index(request):
  from pprint import pprint
  entries = document.Documents(BLOG_BASE)
  pprint(entries)

  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(levelname)s - %(message)s')
  response = django.http.HttpResponse(_render(entries), status=200)
  return response


@util.log_elapsed_total
def entry(request, docname):
  from pprint import pprint
  docname = os.path.normpath(os.path.join(BLOG_BASE, docname))

  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(levelname)s - %(message)s')
  response = django.http.HttpResponse(_render(docname), status=200)
  return response
