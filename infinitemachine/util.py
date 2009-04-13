import logging
import sha
import time

from django.core.cache import cache

from infinitemachine import settings


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


def cached(func):
  def x(*args, **kwargs):
    args_list = list(args) + list(kwargs)
    args_hash = sha.new(str(args_list)).hexdigest()
    sitekey = sha.new(settings.SECRET_KEY).hexdigest()[0:16]
    key = 'im_%s_func_%s_%s' % (sitekey, func.__name__, args_hash)
    value = cache.get(key)
    if not value:
      value = func(*args, **kwargs)
      cache.set(key, value)
      logging.debug('Cached func %s as %s' % (func.__name__, key))
    return value
  x.__name__ = func.__name__
  return x
