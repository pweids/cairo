from setuptools import setup

setup(
  name = 'cairo',
  author = 'pweids',
  version = '0.1.0',
  install_requires = [
    'Click==7.0',
    'python-dateutil'
  ],
  packages = [
    'cairo',
    'csync'
  ],
  entry_points = {
    'console_scripts' : [
      'cairo = cairo.cli:cli',
      'csync = csync:main'
    ]
  }
)