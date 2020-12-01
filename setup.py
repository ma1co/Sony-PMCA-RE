from __future__ import print_function
import os
from glob import glob
from subprocess import check_output

from setuptools import setup, find_packages

PKG_DIR = os.path.dirname(os.path.realpath(__file__))

def git_cmd(p, args):
    g = ['git', '-C', p]
    return check_output(g + args).decode('UTF-8').strip().lstrip('v')

def git_version(p):
    ver_all = git_cmd(p, ['describe', '--tags', '--dirty=.dirty'])
    ver_tag = git_cmd(p, ['describe', '--tags', '--abbrev=0'])
    return ver_tag +  ver_all[len(ver_tag):].replace('-', '.dev', 1).replace('-', '+', 1)

with open('README.md') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

if os.path.exists('version.txt'):
    with open('version.txt') as f:
        version = f.read().strip()
else:
    version = git_version(PKG_DIR)

setup(
    name='Sony-PMCA-RE',
    version=version,
    install_requires=requirements,
    author='ma1co',
    author_email='ma1co@users.noreply.github.com',
    packages=find_packages(exclude=('build', 'dist',)),
    include_package_data=True,
    url='https://github.com/ma1co/Sony-PMCA-RE',
    license='MIT',
    description='Reverse engineering Sony PlayMemories Camera Apps',
    long_description=long_description,
    scripts=['pmca-console',
             'pmca-gui'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
