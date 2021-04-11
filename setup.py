#!/usr/bin/env python3

from distutils.core import setup

from setuptools import find_packages

requirements = [
    "aiohttp",
    "requests",
    "matplotlib"
]

setup(name='dash-emulator',
      version='0.1',
      description='A headless player to emulate the playback of MPEG-DASH streams',
      author='Yang Liu',
      author_email='yang.jace.liu@linux.com',
      url='https://github.com/Yang-Jace-Liu/dash-emulator',
      packages=find_packages(),
      install_requires=requirements
      )
