import logging
import sha
import time


def log_elapsed(func):
  def x(*args, **kwargs):
    start = time.time()
    ret = func(*args, **kwargs)
    logging.debug('%.3fs "%s"' % ((time.time() - start), func.__name__))
    return ret
  return x


def log_elapsed_total(func):
  def x(*args, **kwargs):
    start = time.time()
    ret = func(*args, **kwargs)
    logging.debug('Total: %.3fs "%s"' % ((time.time() - start), func.__name__))
    return ret
  x.__name__ = func.__name__
  return x