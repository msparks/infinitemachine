from django.conf.urls.defaults import *

urlpatterns = patterns('infinitemachine.blog.views',
                       (r'^$', 'index'),
                       (r'^(.*)$', 'entry'))
