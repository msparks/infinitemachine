from django.conf.urls.defaults import *

from infinitemachine import settings
from infinitemachine.wiki.urls import handler404, handler500

urlpatterns = patterns('',
  (r'^static/content/(?P<path>.*)$',
   'django.views.static.serve',
   {'document_root': settings.CONTENT_DIR}),

  (r'^static/(?P<path>.*)$',
   'django.views.static.serve',
   {'document_root': settings.STATIC_DIR}),

  (r'^blog/?', include('infinitemachine.blog.urls')),
  (r'', include('infinitemachine.wiki.urls')),
)

