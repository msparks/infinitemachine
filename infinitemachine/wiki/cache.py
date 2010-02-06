'''
infmx-specific caching routines.

Cache keys will be padded with an ID specific to the current infmx installation
to avoid clashing keys with other applications using the cache.
'''
import sha
from django.core.cache import cache
from infinitemachine import settings


def siteKey(key):
  '''Get the site-specific key from a given key.

  Args:
    key: basic key string

  Returns:
    specialized per-site key string
  '''
  sitekey = sha.new(settings.SECRET_KEY).hexdigest()[0:16]
  key = '__im_%s_%s' % (sitekey, key)
  return key


def set(key, value, timeout=30):
  '''Insert or overwrite a value in the cache.

  This uses a site-specific key.

  Args:
    key: key, not site-specific
    value: value to insert
    timeout: (optional) timeout in seconds

  Returns:
    None
  '''
  cache.set(siteKey(key), value, timeout)


def get(key, default=None):
  '''Get a value from the cache.

  This will create a site-specific key before fetching.

  Args:
    key: key, not site-specific.
    default: (optional) value to return if the key is not found

  Returns:
    value from cache or default value
  '''
  return cache.get(siteKey(key), default)


def delete(key):
  '''Delete an entry from the cache.

  This will create a site-specific key before deleting.

  Args:
    key: key, not site-specific.

  Returns:
    None
  '''
  cache.delete(siteKey(key))