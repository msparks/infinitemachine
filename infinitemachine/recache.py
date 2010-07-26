#!/usr/bin/python
'''
Recaching utility for Infinite Machine.

This will force a re-render of all pages in the content repository.
'''
import logging
import optparse
import os
import sys
import time
sys.path.append('..')
os.environ['DJANGO_SETTINGS_MODULE'] = 'infinitemachine.settings'

import util

from infinitemachine import settings
from infinitemachine.wiki import filesystem
from infinitemachine.wiki import render


class PcacheOptions(object):
  def __init__(self):
    self._target = None
    self._ext = None

  def targetDirIs(self, dir):
    self._target = dir

  def targetDir(self):
    return self._target

  def extIs(self, ext):
    self._ext = ext

  def ext(self):
    return self._ext


def _foreachItemInTree(tree, root, func, *args):
  if root is None:
    root = ''

  for key in sorted(tree):
    path = os.path.join(root, key)
    value = tree[key]

    if type(value) == filesystem.Tree:
      _foreachItemInTree(value, path, func, *args)
    else:
      func(path, *args)


def callForeachDocument(tree, func, *args):
  _foreachItemInTree(tree, None, func, *args)


def cacheDocument(docname):
  print 'Caching %s...  ' % docname,
  start = time.time()
  render.cachedRender(docname, force=True)
  print '%.3fs' % (time.time() - start)


def cacheTree(tree):
  callForeachDocument(tree, cacheDocument)


def writePersistentCache(docname, options):
  print 'Pcaching %s...   ' % docname,
  start = time.time()
  target = options.targetDir()
  ext = options.ext()
  if ext is None:
    ext = ''

  # Create file names.
  target_file = '%s%s' % (os.path.join(target, docname), ext)
  temp_file = '%s~' % target_file

  # Render content.
  content = render.render(docname)

  # Ensure directory exists.
  dir_path = os.path.dirname(target_file)
  try:
    os.makedirs(dir_path)
  except os.error:
    pass

  # Write to the temporary file.
  fh = open(temp_file, 'w')
  if not fh:
    errorAndExit('Failed to open %s' % temp_file)
  fh.write(content)
  fh.close()

  # Rename to target file.
  try:
    os.rename(temp_file, target_file)
  except OSError, e:
    errorAndExit('failed to rename: %s' % e)

  print '%.3fs' % (time.time() - start)


def writePersistentCaches(tree, options):
  callForeachDocument(tree, writePersistentCache, options)


def errorAndExit(msg):
  print msg
  sys.exit(1)


def main():
  parser = optparse.OptionParser()
  parser.add_option('-p', '--pcache', action='store_true',
                    help='write to persistent cache')
  (options, args) = parser.parse_args()

  if options.pcache:
    pcache_dir = getattr(settings, 'PCACHE_DIR', None)
    if pcache_dir is None:
      errorAndExit('PCACHE_DIR option not set in settings.py.')

    if not os.path.isdir(pcache_dir):
      errorAndExit('pcache directory %s does not exist. '
                   'Create it first.' % pcache_dir)

    if not os.access(pcache_dir, os.R_OK | os.W_OK | os.X_OK):
      errorAndExit('permission denied on %s' % pcache_dir)

    print 'Persistent caching enabled. Writing to %s.' % pcache_dir

  fs = filesystem.GitFilesystem(settings.CONTENT_DIR)
  tree = fs.tree()

  cacheTree(tree)

  if options.pcache:
    pcache_options = PcacheOptions()
    pcache_options.targetDirIs(pcache_dir)
    pcache_options.extIs(getattr(settings, 'PCACHE_EXT', None))
    writePersistentCaches(tree, pcache_options)


if __name__ == '__main__':
  main()