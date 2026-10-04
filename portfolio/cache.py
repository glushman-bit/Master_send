import uuid

from django.core.cache import cache

CACHE_VERSION_KEY = 'portfolio:cache_version'
CACHE_TIMEOUT = 300


def get_cache_version():
    version = cache.get(CACHE_VERSION_KEY)

    if version is None:
        version = uuid.uuid4().hex
        cache.set(CACHE_VERSION_KEY, version, timeout=None)

    return version


def make_portfolio_cache_key(query_string):
    version = get_cache_version()

    return f'portfolio:{version}:list:{query_string}'


def invalidate_portfolio_cache():
    version = uuid.uuid4().hex
    cache.set(CACHE_VERSION_KEY, version, timeout=None)
