#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='serializ3r',
      version='0.0.2',
      description='This package allows easy parsing and serialization of database dumps and leaks.',
      author='Carson Owlett',
      author_email='Not given',
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      license='LICENSE.txt',
    )
