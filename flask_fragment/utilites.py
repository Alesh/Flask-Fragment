# -*- coding: utf-8 -*-
"""
    flask.ext.fragment.utilites
    ---------------------------
    
    Helper functions and classes.
    
    :copyright: (c) 2013 by Alexey Poryadin.
    :license: MIT, see LICENSE for more details.
"""
import zlib
import bmemcached

def BMemcache(app, config, *args, **kwargs):
    """Returns memcache object recommended for the extension
    
    Args:
        app: Flask application instance.
        config: Flask application config.
        
    Returns:
        Object that implemented memcache interface
        or None if fragment caching disabled.
    """
    if config.get('FRAGMENT_CACHING'):
        import bmemcached
        return bmemcached.Client(**{
            'servers':  config.get('FRAGMENT_MEMCACHED_SERVERS',
                        config.get('CACHE_MEMCACHED_SERVERS', ('127.0.0.1:11211',))),
            'username': config.get('FRAGMENT_MEMCACHED_USERNAME',
                        config.get('CACHE_MEMCACHED_PASSWORD')),
            'password': config.get('FRAGMENT_MEMCACHED_PASSWORD',
                        config.get('CACHE_MEMCACHED_PASSWORD')),
            'compression': Compressor()
        })
    return None


class Compressor(object):
    """Compressor class recommended for the extension
    
    Args:
        default_compressor: Object that implemented compress/decompress ability. Dezault zlib.
    """
    unless_prefix = b'<!--INC-->'
    
    def __init__(self, default_compressor=None):
        self.real = default_compressor or zlib
    
    def compress(self, value):
        if value[0:len(self.unless_prefix)]==self.unless_prefix:
            return value
        else:
            return self.real.compress(value)

    def decompress(self, value):
        if value[0:len(self.unless_prefix)]==self.unless_prefix:
            return value
        else:
            return self.real.decompress(value)