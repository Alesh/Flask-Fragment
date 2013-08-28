# -*- coding: utf-8 -*-
"""
    flask.ext.fragment
    ------------------
    
    Flask extension to implement fragment caching.
    
    :copyright: (c) 2013 by Alexey Poryadin.
    :license: MIT, see LICENSE for more details.
"""
import flask
import jinja2
import inspect
from functools import partial
from flask import Flask, Blueprint
from flask import _app_ctx_stack as stack
from flask_fragment.utilites import Compressor
from flask_fragment.utilites import BMemcache as Memcache


class Fragment(object):
    """ Extension class """
    body_prefix = 'fragment:'
    lock_prefix = 'fragment:lock:'
    fresh_prefix = 'fragment:fresh:'

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)


    def __call__(self, mod, cache=None, resethandler=None):
        """Decorator to define function as fragment cached view
        
        Args:
            mod: Flask app or blueprint
            cache: The cache timeout value or None if not need to cache.
        """
        def decorator(fragment_view):
            endpoint = fragment_view.__name__
            fragment_view.cache_timeout = cache
            fragment_view.cache_endpoint = endpoint
            fragment_view.cache_resethandler = resethandler
            if isinstance(mod, Blueprint):
                rule = '/_inc/{0}.{1}'.format(mod.name, endpoint)
            else:
                rule = '/_inc/{0}'.format(endpoint)
            fragment_view.args_names = list(inspect.getargspec(fragment_view).args)
            for arg_name in fragment_view.args_names:
                rule += '/<{0}>'.format(arg_name)
            mod.add_url_rule(rule, endpoint, fragment_view)
            return fragment_view
        return decorator
    

    def init_app(self, app):
        self.app = app
        # injects `fragment` function to the context of templates
        self.app.context_processor(lambda: {'fragment': self._fragment_tmpl_func})


    @property
    def memcache(self):
        """Returns memcache object or None if fragment caching disabled."""
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, '_fragment_memcache'):
                ctx._fragment_memcache = Memcache(ctx, flask.current_app.config)
            return ctx._fragment_memcache
        return None
    

    @property
    def lock_timeout(self):
        """Returns lock timeout. Default value 180."""
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, '_fragment_lock_timeout'):
                ctx._fragment_lock_timeout = flask.current_app.config.get('FRAGMENT_LOCK_TIMEOUT', 180)
            return ctx._fragment_lock_timeout
        return None
    
    
    def resethandler(self, fragment_view):
        """Decorator sets reset fragment cache handler for `fragment_view` function."""
        def decorator(handler):
            fragment_view.cache_resethandler = handler
            return handler
        return decorator        


    def reset(self, target, *args, **kwargs):
        """Resets cache for fragment cached view
        
        Args:
            target: Endpoint or the view itself.
        """
        if isinstance(target, str):
            fragment_view = flask.current_app.view_functions.get(target)
            if fragment_view is None:
                raise ValueError('Not found view for endpoint "{0}"'.format(target))
        else:
            fragment_view = target
        if fragment_view.cache_resethandler is None:
            # Tries default resethandler handler
            try:
                for N in range(0, len(args)):
                    kwargs[fragment_view.args_names[N]] = args[N]
                url = flask.url_for(fragment_view.cache_endpoint, **kwargs)
            except Exception as exc:
                raise RuntimeError('Cannot reset cache for "{0}",'
                    ' resethandler is not set and default handler canot'
                    ' build URL. Detail: "{1}"'.format(fragment_view, exc))
            self.reset_url(url)
        else:
            fragment_view.cache_resethandler(*args, **kwargs)
        
    
    def reset_url(self, url):
        """Resets cache for URL
        
        Args:
            url: URL value
        """
        if self.memcache:
            self._cache_reset(url)


    def _fragment_tmpl_func(self, endpoint, *args, **kwargs):
        """Template context function that renders fragment cached view.
        
        Accepts `*args`, `**kwargs` that must match by the number and by the
        order of parameters from  function that defined with 'endpoint'.
        
        Args:
            endpoint: The endpoint name.
        """
        func = flask.current_app.view_functions.get(endpoint)
        if func is not None:
            for N in range(0, len(args)):
                kwargs[func.args_names[N]] = args[N]
            url = flask.url_for(endpoint, **kwargs)
            return self._render(url, func.cache_timeout, partial(func, **kwargs))
        raise ValueError('Not found view for endpoint "{0}"'.format(endpoint))


    def _render(self, url, timeout, deferred_view):
        if self.memcache and timeout:
            if not self._cache_valid(url):
                self._cache_prepare(url, timeout, deferred_view)
            return jinja2.Markup('<!--# include virtual="{0}" -->'.format(url))
        else:
            return jinja2.Markup(deferred_view())

    def _cache_valid(self, url):
        return bool(self.memcache.get(self.fresh_prefix+url) or False)
    
    def _cache_reset(self, url):
        self.memcache.delete(self.fresh_prefix+url)
    
    def _cache_prepare(self, url, timeout, deferred_view):
        successed_lock = self.memcache.add(self.lock_prefix+url, 1, self.lock_timeout)
        if successed_lock:
            result = Compressor.unless_prefix+(deferred_view()).encode('utf-8')
            self.memcache.set(self.body_prefix+url, result, timeout+self.lock_timeout)
            self.memcache.set(self.fresh_prefix+url, 1, timeout)
            self.memcache.delete(self.lock_prefix+url)

    def _create_nginx_config(self, file_name, backend_host=None, backend_port=None,
                             frontend_host=None, frontend_port=None, memcached_host=None,
                             memcached_port=None, body_prefix=None):
        """Creates nginx config file"""
        import os.path
        frontend = flask.current_app.config.get('SERVER_NAME')
        frontend = (frontend or 'localhost') + ':80'
        frontend_host = frontend_host or frontend.split(':')[0]
        frontend_port = frontend_port or int(frontend.split(':')[1])
        source_name = os.path.join(os.path.dirname(__file__), 'preserve', 'nginx.conf')
        with open(source_name) as source:
            conf = source.read() % dict(
                frontend_host = frontend_host, frontend_port = frontend_port,
                backend_host = backend_host or '127.0.0.1',
                backend_port = backend_port or 5000,
                memcached_host = memcached_host or '127.0.0.1',
                memcached_port = memcached_port or 11211,
                body_prefix = body_prefix or self.body_prefix)
            with open(file_name, 'w') as file:
                file.write(conf)