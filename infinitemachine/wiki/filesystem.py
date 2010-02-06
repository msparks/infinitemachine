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

    start_path = '.'

    head = repo.heads[0]
    git_tree = self._tree_root(head.commit.tree, start_path)
    if git_tree is None:
      return None
    return self._tree(start_path, start_path, git_tree)

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
      repo = git.Repo(self.root())
    except (git.errors.InvalidGitRepositoryError, git.errors.NoSuchPathError):
      return None

    if docname == '':
      docname = 'index'
    docname = os.path.normpath(docname)
    basename = os.path.basename(docname)
    head = repo.heads[0]
    tree = self._tree_root(head.commit.tree, os.path.dirname(docname))
    if tree is None:
      return None

    if '%s.txt' % basename in tree:
      blob = tree['%s.txt' % basename]
    elif basename in tree and 'index.txt' in tree[basename]:
      blob = tree[basename]['index.txt']
    else:
      blob = None

    return blob