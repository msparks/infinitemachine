import logging
import os
import time


class File(object):
  '''Class representing a file on a filesystem.'''
  def __init__(self, name, path):
    self._name = name
    self._path = path

  def __repr__(self):
    return '<filesystem.File "%s">' % self._name

  def name(self):
    return self._name

  def content(self):
    fh = open(self._path, 'r')
    content = fh.read()
    fh.close()
    return content


class Filesystem(object):
  def __init__(self, root):
    self._root = root
    self._map = {}
    self._fillMap()

  def exists(self, name):
    return (name in self._map)

  def file(self, name):
    if not self.exists(name):
      return None
    return self._map[name]

  def list(self):
    return sorted(self._map.keys())

  def _fillMap(self):
    def visit(_, dirname, names):
      for name in names:
        path = os.path.join(dirname, name)
        path = os.path.normpath(os.path.abspath(path))

        if os.path.isfile(path):
          name = os.path.relpath(path, self._root)
          # Add all files to internal map, keyed by their relative path name.
          self._map[name] = File(name, path)

    os.path.walk(self._root, visit, None)