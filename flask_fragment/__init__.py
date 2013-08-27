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
        # injects `fragment` decorator
        Flask.fragment = self._fragment_decorator
        Blueprint.fragment = self._fragment_decorator


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
    

    def reset(self, endpoint, *args, **kwargs):
        """Resets fragment cache
        
        Accepts `*args`, `**kwargs` that must match by the number and by the
        order of parameters from function that defined with 'endpoint'.
        
        Args:
            endpoint: The endpoint name.
        """
        func = flask.current_app.view_functions.get(endpoint)
        if func is not None:
            for N in range(0, len(args)):
                kwargs[func.args_names[N]] = args[N]
            for N in range(0, len(func.args_names)):
                if func.args_names[N] not in  kwargs:
                    kwargs[func.args_names[N]] = '' 
            url = flask.url_for(endpoint, **kwargs)
            pos = url.find('//')
            url = url[:pos] if pos>-0 else url
            self._cache_reset(url)
            return 
        raise ValueError('Not found view for endpoint "{0}"'.format(endpoint))    


    @staticmethod
    def _fragment_decorator(mod, timeout=None):
        """Decorator to define function as fragment cached view
        
        Args:
            timeout: The cache timeout value.
        """
        def decorator(func):
            endpoint = func.__name__
            func.cache_timeout = timeout
            if isinstance(mod, Blueprint):
                rule = '/_inc/{0}.{1}'.format(mod.name, endpoint)
            else:
                rule = '/_inc/{0}'.format(endpoint)
            func.args_names = list(inspect.getargspec(func).args)
            for arg_name in func.args_names:
                rule += '/<{0}>'.format(arg_name)
            mod.add_url_rule(rule, endpoint, func)
            return func
        return decorator


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
