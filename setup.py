version = '0.1-dev'
from setuptools import setup, find_packages

setup(
    name = 'Flask-Fragment',
    version = version,
    license = 'MIT',
    author = 'Alexey Poryadin',
    author_email='alexey.poryadin@gmail.com',
    description='Flask extension to implement fragment caching',
    packages = ['flask_fragment'],
    install_requires = [
        'Flask',
    ],
)