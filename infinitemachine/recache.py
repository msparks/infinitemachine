#!/usr/bin/python
'''
Recaching utility for Infinite Machine.

This will force a re-render of all pages in the content repository.
'''
import logging
import os
import sys
import time
sys.path.append('..')
os.environ['DJANGO_SETTINGS_MODULE'] = 'infinitemachine.settings'

import util

from infinitemachine import settings
from infinitemachine.wiki import filesystem
from infinitemachine.wiki import render


def cacheDocument(docname):
  print 'Caching %s...  ' % docname,
  start = time.time()
  render.cachedRender(docname, force=True)
  print '%.3fs' % (time.time() - start)


def cacheTree(tree, root=None):
  if root is None:
    root = ''

  for key in sorted(tree):
    path = os.path.join(root, key)
    value = tree[key]

    if type(value) == filesystem.Tree:
      cacheTree(value, path)
    else:
      cacheDocument(path)


def main():
  fs = filesystem.GitFilesystem(settings.CONTENT_DIR)
  tree = fs.tree()
  cacheTree(tree)


if __name__ == '__main__':
  main()