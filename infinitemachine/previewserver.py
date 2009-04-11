#!/usr/bin/python
import getopt
import os
import sys
import django.core.management
from django.core.management.commands import runserver
import django.utils.autoreload

try:
  sys.path.append('..')
  from infinitemachine import settings
except ImportError:
  sys.stderr.write('Error: cannot import settings\n')
  sys.exit(1)


def show_help():
  text = '''previewserver.py - Infinite Machine preview server

This server can be used to preview content and quickly change core settings.

usage: previewserver.py [options] <content directory>
  -i    IP address to listen on [0.0.0.0]
  -p    server port number [8010]
  -c    Enable caching backend
  -d    Disable debug mode
  -r    Treat content directory as a repository'''
  print text


def start_server(ip, port):
  global django_server
  django.core.management.setup_environ(settings)
  django_server = runserver.Command()
  django_server.handle(addrport='%s:%s' % (ip, port), use_autoreloader=False)


def main():
  # network settings
  ip = '0.0.0.0'
  port = 8010

  caching = False
  debug = True
  repository = False

  opts, args = getopt.gnu_getopt(sys.argv[1:], 'i:p:cdrh', ['help'])
  for o, a in opts:
    if o == '-p':
      port = a
    if o == '-i':
      ip = a
    if o == '-c':
      caching = True
    if o == '-d':
      debug = False
    if o == '-r':
      repository = True
    if o == '--help' or o == '-h':
      show_help()
      sys.exit(0)  # FIXME(ms): because of the autoreloader, this doesn't work

  if not args:
    args = ['.']

  content_dir = os.path.abspath(args[0])
  if not os.path.isdir(content_dir):
    print '"%s" must exist and be a directory' % content_dir
    content_dir = os.path.abspath('.')
    sys.exit(1)

  print '>> Starting..'

  # modify settings
  if not caching:
    settings.CACHE_BACKEND = 'dummy://'
  print '   * Using cache backend: %s' % settings.CACHE_BACKEND

  settings.DEBUG = debug
  print '   * Debug mode is %s.' % (debug and 'enabled' or 'disabled')

  settings.CONTENT_DIR = content_dir
  settings.USE_FILESYSTEM = not repository

  if repository:
    print '   * Content repository: %s' % os.path.abspath(content_dir)
  else:
    print '   * Content directory: %s' % os.path.abspath(content_dir)

  print ''
  start_server(ip, port)


if __name__ == '__main__':
  django.utils.autoreload.main(main)
