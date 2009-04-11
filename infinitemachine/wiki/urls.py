from django.conf.urls.defaults import *

urlpatterns = patterns('infinitemachine.wiki.views',
                       (r'^(.*)$', 'index'))

handler404 = 'infinitemachine.wiki.views.handler404'
handler500 = 'infinitemachine.wiki.views.handler500'
