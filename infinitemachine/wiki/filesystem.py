import logging
import os
import time

import git

from infinitemachine import settings
from infinitemachine import util


def document_url(docname):
  '''Get the web-accessible URL for a given document name.

  Args:
    docname: wiki path to document

  Returns:
    web-accessible URL string
  '''
  return os.path.join('/', docname)


def source_url(docname):
  '''Get the web-accessible URL for a given document or image.

  This is used to create the URL for a direct link to a file from within an
  article (such as an image), which is part of the content.

  Args:
    docname: wiki path to the document or file

  Returns:
    web-accessible URL string
  '''
  return os.path.join(settings.CONTENT_URL, docname)


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


class Tree(dict):
  pass


class Filesystem(object):
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
      root = '.'
    path = os.path.join(settings.CONTENT_DIR, root)
    if not os.path.isdir(path):
      return None

    tr = {}
    for filename in os.listdir(path):
      filepath = os.path.join(path, filename)
      if os.path.isfile(filepath) and filepath.endswith('.txt'):
        docname = os.path.normpath(os.path.join(root, filename))
        tr[filename[:-4]] = Document(self, docname[:-4])
      elif os.path.isdir(filepath):
        sub_tree = self.tree(os.path.join(root, filename))
        if sub_tree:
          tr[filename] = sub_tree
    return tr

  def _document_path(self, docname):
    '''Get the filesystem path for a given document name.

    Args:
      docname: wiki path to document (e.g., 'articles/irssi')

    Returns:
      filesystem path string or None
    '''
    filename = os.path.join(settings.CONTENT_DIR, docname)
    if os.path.exists('%s.txt' % filename):
      filename = '%s.txt' % filename
    elif os.path.isdir(filename) and os.path.exists('%s/index.txt' % filename):
      filename = os.path.join(filename, 'index.txt')
    else:
      return None
    return filename


class GitFilesystem(Filesystem):
  def document(self, docname):
    return _blob(docname) and Document(self, docname) or None

  def tree(self, root=None):
    try:
      repo = git.Repo(settings.CONTENT_DIR)
    except (git.errors.InvalidGitRepositoryError, git.errors.NoSuchPathError):
      return None

    if root is None:
      root = '.'

    head = repo.heads[0]
    git_tree = self._tree_root(head.commit.tree, root)
    if git_tree is None:
      return None
    return self._tree(root, root, git_tree)

  def _tree(self, base_docname, docname, tree_root):
    docname = os.path.normpath(os.path.join(base_docname, docname))
    if type(tree_root) == git.Blob:
      return docname.endswith('.txt') and Document(self, docname[:-4]) or None
    else:  # type(tree_root) == git.Tree:
      tr = {}
      for name, root in tree_root.items():
        sub_tree = self._tree(docname, name, root)
        if sub_tree and type(sub_tree) == Document:
          tr[name[:-4]] = sub_tree
        elif sub_tree:
          tr[name] = sub_tree
      return Tree(tr)

  def content(self, docname):
    blob = self._blob(docname)
    if not blob:
      return None
    return blob.data

  def _tree_root(self, tree, root_path):
    if root_path == '.' or not root_path:
      return tree
    dirs = root_path.split('/')
    for dirname in dirs:
      if type(tree) != git.Tree or dirname not in tree:
        return None
      tree = tree[dirname]
    return tree

  def _blob(self, docname):
    '''Get a Blob object for a given docname.

    Args:
      docname: document name

    Returns:
      Blob or None
    '''
    try:
      repo = git.Repo(settings.CONTENT_DIR)
    except (git.errors.InvalidGitRepositoryError, git.errors.NoSuchPathError):
      return None

    head = repo.heads[0]
    tree = self._tree_root(head.commit.tree, os.path.dirname(docname))
    if tree is None:
      return None
    basename = os.path.basename(docname)

    if '%s.txt' % basename in tree:
      blob = tree['%s.txt' % basename]
    elif basename in tree and 'index.txt' in tree[basename]:
      blob = tree[basename]['index.txt']
    else:
      blob = None

    return blob
