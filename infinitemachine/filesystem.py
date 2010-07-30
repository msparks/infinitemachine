import logging
import os
import time

import git


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


class GitDocument(File):
  def __init__(self, docname, blob):
    self._docname = docname
    self._blob = blob

  def content(self):
    return self._blob.data


class Tree(dict):
   pass


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


class GitFilesystem(Filesystem):
  def document(self, docname):
    pieces = os.path.normpath(docname).split('/')
    tr = self.tree()
    while tr is not None and len(pieces) > 0:
      if pieces[0] not in tr:
        return None
      tr = tr[pieces.pop(0)]
      if isinstance(tr, GitDocument):
        return tr

    # no pieces left, try index if we're at a directory
    if isinstance(tr, Tree) and 'index' in tr:
      obj = tr['index']
      if isinstance(obj, GitDocument):
        return obj

    return None

  def tree(self, root=None):
    try:
      repo = git.Repo(self.root())
    except (git.errors.InvalidGitRepositoryError, git.errors.NoSuchPathError):
      return None

    head = repo.heads[0]
    return self._tree(repo.tree(head))

  def _tree(self, obj):
    if obj.type == 'blob':
      docname = obj.path
      return docname.endswith('.txt') and GitDocument(docname[:-4], obj) or None
    elif obj.type == 'tree':
      tr = Tree()
      subobjs = obj.trees
      subobjs.extend(obj.blobs)
      for subobj in subobjs:
        basename = os.path.basename(subobj.path)
        if subobj.type == 'blob' and basename.endswith('.txt'):
          basename = basename[:-4]
        subtree = self._tree(subobj)
        if subtree is not None:
          tr[basename] = self._tree(subobj)
      return tr

  def content(self, docname):
    doc = self.document(docname)
    return doc is not None and doc.content() or None