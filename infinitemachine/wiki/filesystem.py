import logging
import os
import time

import git


class Document(object):
  '''Class representing a wiki document on a filesystem.'''
  def __init__(self, parent, docname):
    self._docname = docname
    self._parent = parent

  def __repr__(self):
    return '<Document "%s">' % self._docname

  def content(self):
    return self._parent.content(self._docname)

  def docname(self):
    return self._docname


class GitDocument(Document):
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

  def root(self):
    return self._root

  def document(self, docname):
    return self._document_path(docname) and Document(self, docname) or None

  def content(self, docname):
    filename = self._document_path(docname)
    if not filename:
      return None
    fh = open(filename, 'r')
    content = fh.read()
    fh.close()
    return content

  def tree(self, root=None):
    if root is None:
      root = self._root
    if not os.path.isdir(root):
      return None

    tr = {}
    for filename in os.listdir(root):
      filepath = os.path.join(root, filename)
      if os.path.isfile(filepath) and filepath.endswith('.txt'):
        docname = os.path.normpath(os.path.join(root, filename))
        tr[filename[:-4]] = Document(self, docname[:-4])
      elif os.path.isdir(filepath):
        sub_tree = self.tree(os.path.join(root, filename))
        if sub_tree:
          tr[filename] = sub_tree
    return Tree(tr)

  def _document_path(self, docname):
    '''Get the filesystem path for a given document name.

    Args:
      docname: wiki path to document (e.g., 'articles/irssi')

    Returns:
      filesystem path string or None
    '''
    docname = os.path.normpath(docname)
    filename = os.path.join(self._root, docname)

    if os.path.exists('%s.txt' % filename):
      filename = '%s.txt' % filename
    elif os.path.isdir(filename) and os.path.exists('%s/index.txt' % filename):
      filename = os.path.join(filename, 'index.txt')
    else:
      return None
    return filename


class GitFilesystem(Filesystem):
  def document(self, docname):
    return self._blob(docname) and Document(self, docname) or None

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
      tr = {}
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
    pieces = os.path.normpath(docname).split('/')
    tr = self.tree()
    while tr is not None and len(pieces) > 0:
      if pieces[0] not in tr:
        return None
      tr = tr[pieces.pop(0)]
      if type(tr) == GitDocument:
        return tr.content()