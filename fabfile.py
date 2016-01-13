import os
import re
import shutil

from fabric.api import abort, env, lcd, local, prefix, put, puts, \
    require, run, sudo, task
from fabric.colors import green, yellow
from fabric.context_managers import cd, hide, settings
from fabric.contrib import files
from fabric.contrib.console import confirm

import pidman

##
# automated build/test tasks
##


def all_deps():
    '''Locally install all dependencies.'''
    local('pip install -r pip-install-req.txt')
    local('pip install -r pip-dev-req.txt')
    if os.path.exists('pip-local-req.txt'):
        local('pip install -r pip-local-req.txt')

@task
def test():
    '''Locally run all tests.'''
    if os.path.exists('test-results'):
        shutil.rmtree('test-results')

    # sample command once we convert to django-nose
    local('python manage.py test --with-coverage --cover-package=%(project)s --cover-xml --with-xunit' \
        % env)
    # convert .coverage file to coverage.xml
    local('coverage xml')

@task
def doc():
    '''Locally build documentation.'''
    with lcd('docs'):
        local('make clean html')


@task
def build():
    '''Run a full local build/test cycle.'''
    all_deps()
    test()
    doc()

