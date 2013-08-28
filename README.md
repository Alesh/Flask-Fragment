Flask-Fragment
==============

This is Flask extension allows you to use fragment caching with using stack
**SSI+Memcached+Nginx**. It is ready for testing purpose. API is not frozen,
it will expand. The documentation is not ready, but there are enough functional
demo application and docstring in code.


Requirements
------------

Nginx must be compiled with ngx_http_ssi_module and ngx_http_memcached_module.
It is required latest `python-binary-memcached`.
    
    pip install git+https://github.com/jaysonsantos/python-binary-memcached.git

Python3 is supported, but you need install `python-binary-memcached` from my fork.
It is contain patch for Python3 compatibility.

    pip install git+https://github.com/AleshGood/python-binary-memcached.git