import logging
import os
import re
import time

import creole
import pygments
import pygments.lexers
import pygments.formatters

import filesystem


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
  return os.path.join('/', docname)


def html_escape(text):
  '''Substitute in basic HTML entities.

  Args:
    text: input text

  Returns:
    output text with < > & replaced
  '''
  return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def attr_escape(text):
  '''HTML escape and also replace quotes.

  Args:
    text: input text

  Returns:
    replaced text
  '''
  return html_escape(text).replace('"', '&quot;')


def header_short_name(title):
  '''Return url-appropriate name for a header title.

  Args:
    title: input title text

  Returns:
    short title of a-z, 0-9, ., _, -
  '''
  if title is None:
    return u''
  title = title.lower()
  title = title.replace(' ', '_')
  title = re.sub(r'[^a-z0-9\.\_\-]', '', title)
  return title


class Rules:
  # For the link targets:
  proto = r'http|https|ftp|nntp|news|mailto|telnet|file|irc'
  page = r'(?P<page_addr>\#.*)'
  extern = r'(?P<extern_addr>(?P<extern_proto>%s):.*)' % proto
  intern = r'(?P<intern_addr>[^/].*)'
  interwiki = r'((?P<inter_wiki>[a-zA-Z]+)>(?P<inter_term>.*))'


# Expression to combine rules from Rules class for identifying link targets
ADDR_RE = re.compile('|'.join([
  Rules.page,
  Rules.extern,
  Rules.interwiki,
  Rules.intern
]), re.X | re.U)  # for addresses


class Link(object):
  '''Class representing an anchor tag.

  Attributes:
    See constructor.
  '''
  def __init__(self, href, text, target=None, css_class=None):
    '''Constructor.

    Args:
      href: url string
      text: link text
      target: (optional) target string ("_top", "_blank", etc)
      css_class: (optional) CSS class to assign to link
    '''
    self.href = href
    self.text = text
    self.target = target
    self.css_class = css_class

  def to_html(self):
    '''Format link as an HTML string.

    Returns:
      unicode string of <a> tag
    '''
    return (u'<a href="%s"%s%s>%s</a>' %
            (attr_escape(self.href),
             self.target and (' target="%s"' % self.target) or u'',
             self.css_class and (' class="%s"' % self.css_class) or u'',
             self.text))


class InterwikiLinker(object):
  '''Create links to other web apps or wikis.

  Attributes:
    link: Link object
  '''
  # TODO(ms): this should not be here, and instead in site settings
  _WIKITABLE = {'wp': 'http://en.wikipedia.org/wiki/',
                'g': 'http://www.google.com/search?q='}

  def __init__(self, wikikey, term, text=None, target=None):
    '''Constructor.

    Args:
      wikikey: keyword for external wiki
      term: term on external wiki to link to
      text: (optional) alternate text to use for link
      target: (optional) override the default link target of "_blank"
    '''
    if wikikey not in self._WIKITABLE:
      raise ValueError, '"%s" is not a recognized wiki keyword' % wikikey
    if text is None:
      text = term
    if target is None:
      target = '_blank'

    href = u'%s%s' % (self._WIKITABLE[wikikey], term)
    css_class = u'iw iw_%s' % wikikey
    self.link = Link(href, text, target=target, css_class=css_class)


class LinkNode(object):
  def __init__(self, ds, node, inside=None):
    '''Link node object.

    Args:
      ds: DocumentSet
      node: DocNode for a link
    '''
    self._ds = ds
    self._node = node
    self._target = node.content
    self._inside = inside

    if inside:
      self._inside_empty = False
    else:
      self._inside = html_escape(self._target)
      self._inside_empty = True

    m = ADDR_RE.match(self._target)
    # external links (http://...)
    if m and m.group('extern_addr'):
      self._link = Link(self._target, self._inside, target='_blank',
                        css_class='urle')
    # intrawiki links ([[articles/irssi]])
    elif m and m.group('intern_addr'):
      if self._inside_empty and self._ds.contains(self._target):
        self._inside = Document(self._target).title()
      self._link = Link(document_url(self._target),
                        self._inside, css_class='urli')
    # interwiki links ([[wp>Python]])
    elif m and m.group('inter_wiki'):
      if self._inside_empty:
        self._inside = None
      self._link = InterwikiLinker(m.group('inter_wiki'),
                                   m.group('inter_term'),
                                   text=self._inside).link
    # intrapage links ([[#foosection]])
    elif m and m.group('page_addr'):
      self._link = Link(self._target, self._inside)
    # matched ADDR_RE, but not any of the rules
    elif m:
      raise NotImplementedError
    else:
      # on-site links (/some/file)
      self._link = Link(self._target, self._inside)

  def to_html(self):
    return self._link.to_html()


class PreNode(object):
  def __init__(self, node):
    '''Preformatted text node object.

    Args:
      node: DocNode
    '''
    self._content = node.content
    self._escape = True
    self._raw = False
    self._lexer = None

    while True:
      m = re.search(r'^\s*(noescape|raw|lang)\s*:\s*(\w+)\s*', self._content)
      if not m:
        break

      key = m.group(1).lower()
      value = m.group(2).lower()

      if key == 'noescape' and value == 'true':
        self._escape = False
      elif key == 'raw' and value == 'true':
        self._raw = True
      elif key == 'lang':
        self._lexer = value

      self._content = re.sub(m.group(0), u'', self._content)

  def to_html(self):
    def tag(content, raw):
      return raw and content or u'<pre>%s</pre>' % content

    if self._lexer:
      if self._lexer == 'guess':
        lexer = pygments.lexers.guess_lexer(self._content)
      else:
        lexer = pygments.lexers.get_lexer_by_name(self._lexer)

      formatter = pygments.formatters.HtmlFormatter(linenos=True,
                                                    cssclass='syntax')
      return pygments.highlight(self._content, lexer, formatter)

    if self._escape:
      return tag(html_escape(self._content), self._raw)
    else:
      return tag(self._content, self._raw)


class HtmlEmitter(object):
  '''
  Generate HTML output for the document
  tree consisting of DocNodes.
  '''
  def __init__(self, ds, root, omit_title=False, omit_summary=False):
    self._ds = ds
    self._level = 0
    self.root = root
    self._omit_title = omit_title
    self._omit_title_done = False
    self._omit_summary = omit_summary
    self._seen_level2_header = False

  def get_text(self, node):
    '''Try to emit whatever text is in the node.'''
    try:
      return node.children[0].content or ''
    except:
      return node.content or ''

  def document_emit(self, node):
    return self.emit_children(node)

  def text_emit(self, node):
    return html_escape(node.content)

  def separator_emit(self, node):
    return u'<hr>'

  def paragraph_emit(self, node):
    inside = self.emit_children(node)
    if inside:
      s = inside.split(' ')
      if s[0].lower() in ('note:', 'tip:', 'important:', 'warning:'):
        return u'<p class="%s">%s</p>\n' % (s[0].lower()[:-1], ' '.join(s[1:]))
    return u'<p>%s</p>\n' % inside

  def bullet_list_emit(self, node):
    if self._level:
      return u'<ul class="lvl%s">\n%s</ul>\n' % (self._level,
                                                 self.emit_children(node))
    else:
      return u'<ul>\n%s</ul>\n' % self.emit_children(node)

  def number_list_emit(self, node):
    if self._level:
      return u'<ol class="lvl%s">\n%s</ol>\n' % (self._level,
                                                 self.emit_children(node))
    else:
      return u'<ol>\n%s</ol>\n' % self.emit_children(node)

  def list_item_emit(self, node):
    return u'<li>%s</li>\n' % self.emit_children(node)

  def table_emit(self, node):
    return u'<table>\n%s</table>\n' % self.emit_children(node)

  def table_row_emit(self, node):
    return u'<tr>%s</tr>\n' % self.emit_children(node)

  def table_cell_emit(self, node):
    return u'<td>%s</td>' % self.emit_children(node)

  def table_head_emit(self, node):
    return u'<th>%s</th>' % self.emit_children(node)

  def emphasis_emit(self, node):
    return u'<i>%s</i>' % self.emit_children(node)

  def strong_emit(self, node):
    return u'<b>%s</b>' % self.emit_children(node)

  def header_emit(self, node):
    ret = u''
    if node.level == 1 and self._omit_title and not self._omit_title_done:
      self._omit_title_done = True
      return u''
    if node.level > 1:
      self._seen_level2_header = True

    if self._level:
      ret += u'</div>\n\n'
    ret += (u'<h%d><a name="%s">%s</a></h%d>\n' %
            (node.level, header_short_name(node.content),
             html_escape(node.content), node.level))
    ret += u'<div class="lvl%s">\n' % node.level
    self._level = node.level
    return ret

  def code_emit(self, node):
    return u'<code>%s</code>' % html_escape(node.content)

  def link_emit(self, node):
    inside = None
    if node.children:
      inside = self.emit_children(node)
    return LinkNode(self._ds, node, inside).to_html()

  def image_emit(self, node):
    # FIXME(ms): this code is really ugly.
    target = node.content
    text = self.get_text(node)
    m = ADDR_RE.match(target)

    # pull class from text if possible
    if text.startswith('_') and text.endswith('_'):
      css_class = 'center'
      text = text[1:-1]
    elif text.startswith('_'):
      css_class = 'right'
      text = text[1:]
    elif text.endswith('_'):
      css_class = 'left'
      text = text[:-1]
    else:
      css_class = None
    class_str = css_class and (' class="%s"' % css_class) or ''

    if m:
      if m.group('extern_addr'):
        s = target.split("?", 2)
        if len(s) == 2:
          target, args = s
          width_str = u' width="%s"' % args
        else:
          width_str = None

        if width_str:
          return (u'<a href="%s" class="lightbox">'
                  '<img src="%s"%s%s alt="%s" /></a>' %
                  (attr_escape(target), attr_escape(target), class_str,
                   width_str, attr_escape(text)))
        else:
          return u'<img src="%s"%s%s alt="%s" />' % (
            attr_escape(target), class_str, width_str, attr_escape(text))
      elif m.group('intern_addr'):
        s = target.split("?", 2)
        if len(s) == 2:
          target, args = s
          width_str = u' width="%s"' % args
        else:
          width_str = None

        if width_str:
          return (u'<a href="%s" class="lightbox">'
                  '<img src="%s"%s%s alt="%s" /></a>' %
                  (source_url(attr_escape(target)),
                   source_url(attr_escape(target)),
                   class_str, width_str, attr_escape(text)))
        else:
          return (u'<img src="%s"%s alt="%s" />' %
                  (source_url(attr_escape(target)),
                   class_str, attr_escape(text)))
      elif m.group('inter_wiki'):
        raise NotImplementedError
    return (u'<img src="%s"%s alt="%s" />' %
            (attr_escape(target), class_str, attr_escape(text)))

  def macro_emit(self, node):
    inside = self.emit_children(node)
    return u'<%s>%s</%s>' % (node.content, inside, node.content)

  def break_emit(self, node):
    return u'<br />'

  def preformatted_emit(self, node):
    return PreNode(node).to_html()

  def default_emit(self, node):
    '''Fallback function for emitting unknown nodes.'''
    raise TypeError

  def emit_children(self, node):
    '''Emit all the children of a node.'''
    return u''.join([self.emit_node(child) for child in node.children])

  def emit_node(self, node):
    '''Emit a single node.'''
    if (self._omit_summary and node.kind not in ('document', 'header')
        and not self._seen_level2_header):
      return u''

    emit = getattr(self, '%s_emit' % node.kind, self.default_emit)
    return emit(node)

  def emit(self):
    '''Emit the document represented by self.root DOM tree.'''
    ret = self.emit_node(self.root)
    if self._level:
      ret += u'</div>\n\n'
    return ret


class Parser(creole.Parser):
  '''Convenience Parser class.'''
  pass


class TOC(object):
  class NodeList(list):
    level = 1

  class Node(object):
    def __init__(self, level, title, children=None):
      self.level = level
      self.title = title
      self.children = children

    def __repr__(self):
      return u'<Node "%s">' % self.title

  def __init__(self):
    self._toc = self.NodeList()
    self._cur = self._toc
    self._level_stack = [self._toc]

  def _cut_root_node(self):
    '''Get the TOC tree without the root node, if one exists.

    Returns:
      NodeList or None
    '''
    if len(self._toc) == 1 and type(self._toc[0]) == self.Node:
      return self._toc[0].children
    else:
      return self._toc

  def add_header(self, level, title):
    if level == len(self._level_stack):
      node = self.Node(level, title)
      self._cur.append(node)
    elif level > len(self._level_stack):
      newlevel = self.NodeList()
      newlevel.level = level
      if self._cur:  # node exists at previous level
        self._cur[-1].children = newlevel
      else:  # node does not exist at previous level, create one
        newnode = self.Node(len(self._level_stack), u'', newlevel)
        self._cur.append(newnode)
      self._cur = newlevel
      self._level_stack.append(newlevel)
      self.add_header(level, title)
    else:  # level < len(self._level_stack)
      self._level_stack.pop()
      self._cur = self._level_stack[len(self._level_stack) - 1]
      self.add_header(level, title)

  def _to_html_rec(self, item, level_adjust=False):
    if item is None:
      return ''
    level_comp = level_adjust and -1 or 0
    item.level += level_comp
    if type(item) == self.Node:
      return (u'%s<li><a href="#%s">%s</a>%s</li>\n' %
              ('  ' * item.level,
               header_short_name(item.title),
               item.title,
               self._to_html_rec(item.children, level_adjust)))
    elif type(item) == self.NodeList:
      return (u'\n%s<ol>\n%s%s</ol>\n' %
              ('  ' * (item.level - 1),
               u''.join([self._to_html_rec(x, level_adjust) for x in item]),
               '  ' * (item.level - 1)))
    else:
      raise TypeError

  def to_html(self, cut_root_node=True):
    if cut_root_node:
      toc = self._cut_root_node()
    else:
      toc = self._toc
    if toc == self._toc:
      cut_root_node = False
    return self._to_html_rec(toc, level_adjust=cut_root_node)

  def size(self, cut_root_node=True):
    '''Get the number of items and subitems in the table of contents.

    Returns:
      integer
    '''
    def _rec_size(node_list):
      s = 0
      if not node_list:
        return 0
      for item in node_list:
        if type(item) == self.Node:
          s += 1 + _rec_size(item.children)
        elif type(item) == self.NodeList:
          s += _rec_size(item)
      return s

    if cut_root_node:
      toc = self._cut_root_node()
    else:
      toc = self._toc
    return _rec_size(toc)


class StructureExtractor(object):
  '''Extract structure information from a DocNode tree.'''
  def __init__(self, root):
    self.title = None
    self.summary_root = creole.DocNode()
    self.summary_root.kind = 'document'
    self.toc = TOC()

    self._seen_level2_header = False
    self._root = root
    self._process()

  def _document_process(self, node):
    return self._process_children(node)

  def _header_process(self, node):
    if self.title is None:
      self.title = node.content
    if node.level > 1:
      self._seen_level2_header = True
    self.toc.add_header(node.level, node.content)

  def _process_children(self, node):
    '''Process all the children of a node.'''
    for child in node.children:
      self._process_node(child)

  def _process_node(self, node):
    if node.kind not in ('document', 'header') and not self._seen_level2_header:
      self.summary_root.children.append(node)

    method = getattr(self, '_%s_process' % node.kind, None)
    if method:
      method(node)

  def _process(self):
    self._process_node(self._root)


class DocumentSet(object):
  def __init__(self, fs):
    self._fs = fs
    self._map = {}
    self._fillMap()

  def contains(self, name):
    return (name in self._map)

  def document(self, name):
    if not self.contains(name):
      return None
    return self._map[name]

  def list(self):
    return sorted(self._map.keys())

  def _fillMap(self):
    filenames = self._fs.list()
    for filename in filenames:
      file = self._fs.file(filename)
      (docname, ext) = os.path.splitext(filename)

      # Only attempt to Documentize .txt files for now.
      if ext == '.txt':
        self._map[docname] = Document(self, docname, file)


class Document(object):
  def __init__(self, ds, name, file):
    '''Constructor.

    Args:
      ds: DocumentSet to which this document belongs
      name: name of document
      file: filesystem.File object
    '''
    self._ds = ds
    self._name = name
    self._file = file
    self._document = None
    self._structure = None
    self._exists = True

  def __repr__(self):
    return '<Document "%s">' % self.name()

  def _parse(self):
    start = time.time()
    self._content = self._file.content()
    if type(self._content) != unicode:
      self._content = unicode(self._content, 'utf-8', 'ignore')
    self._document = Parser(self._content).parse()
    logging.debug('Done parsing. Elapsed: %.3fs' % (time.time() - start))

    start = time.time()
    self._structure = StructureExtractor(self._document)
    logging.debug('Done extracting structure. Elapsed: %.3fs' %
                  (time.time() - start))

  def name(self):
    return self._name

  def title(self):
    # check local structure first
    if self._structure:
      return self._structure.title or os.path.basename(self.name())

    self._parse()
    return self._structure.title or os.path.basename(self.name())

  def to_html(self):
    if not self._document or not self._structure:
      self._parse()
    emitter = HtmlEmitter(self._ds, self._document,
                          omit_title=True, omit_summary=True)
    return emitter.emit().encode('utf-8', 'ignore')

  def summary(self):
    if not self._structure:
      self._parse()
    emitter = HtmlEmitter(self._ds, self._structure.summary_root)
    return emitter.emit().encode('utf-8', 'ignore')

  def toc(self):
    if not self._structure:
      self._parse()
    return self._structure.toc

  def breadcrumbs(self):
    bc = []
    bc_split = self.name().split('/')
    for i, segment in enumerate(bc_split):
      if segment == 'index':
        break
      sub_dn = '/'.join(bc_split[0:(i+1)])
      bc_elem = (sub_dn, self.__class__(sub_dn).title())
      bc.append(bc_elem)
    return bc