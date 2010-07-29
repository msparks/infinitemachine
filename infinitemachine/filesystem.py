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
  def __init__(self, root=None):
    self._root = root

  def file(self, name):
    path = self._file_path(name)
    if path is None:
      return None

    return File(name, path)

  def tree(self, root=None):
    if root is None:
      root = self._root
    if not os.path.isdir(root):
      return None

    tr = Tree()
    for filename in os.listdir(root):
      filepath = os.path.join(root, filename)
      if os.path.isfile(filepath) and filepath.endswith('.txt'):
        name = os.path.normpath(os.path.join(root, filename))
        tr[filename[:-4]] = File(name[:-4], filepath)
      elif os.path.isdir(filepath):
        sub_tree = self.tree(os.path.join(root, filename))
        if sub_tree:
          tr[filename] = sub_tree
    return tr

  def _file_path(self, name):
    '''Get the filesystem path for a given name.

    Args:
      name: nice name for file (e.g., 'articles/irssi')

    Returns:
      filesystem path string or None
    '''
    name = os.path.normpath(name)
    filename = os.path.join(self._root, name)

    if os.path.exists('%s.txt' % filename):
      filename = '%s.txt' % filename
    elif os.path.isdir(filename) and os.path.exists('%s/index.txt' % filename):
      filename = os.path.join(filename, 'index.txt')
    else:
      return None
    return filename


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