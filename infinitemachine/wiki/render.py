import os
import time

import django.http
import django.template.loader

from infinitemachine import settings
from infinitemachine.wiki import cache
from infinitemachine.wiki import document


def render(docname, template=None):
  # load document from disk
  doc = document.Document(docname)
  if not doc.exists():
    raise django.http.Http404

  if template is None:
    template = 'index.html'

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
  return rendered


def cachedRender(docname, template=None, timeout=None, force=False):
  if timeout is None:
    # cache for 5 years (infinitely)
    timeout = int(time.time() + 3600 * 24 * 365 * 5)

  rendered = cache.get(docname)
  if force or rendered is None:
    rendered = render(docname, template)
    cache.set(docname, rendered, timeout=timeout)

    dir, base = os.path.split(docname)
    if base == 'index':
      cache.set(dir, rendered, timeout=timeout)

  return rendered