Overview
--------

.. image:: https://travis-ci.org/emory-libraries/pidmanclient.svg?branch=develop
    :alt: Travis-CI build status
    :target: https://travis-ci.org/emory-libraries/pidmanclient

.. image:: https://coveralls.io/repos/github/emory-libraries/pidmanclient/badge.svg?branch=develop
   :target: https://coveralls.io/github/emory-libraries/pidmanclient?branch=develop
   :alt: Code Coverage

.. image:: https://codeclimate.com/github/emory-libraries/pidmanclient/badges/gpa.svg
   :target: https://codeclimate.com/github/emory-libraries/pidmanclient
   :alt: Code Climate

.. image:: https://requires.io/github/emory-libraries/pidmanclient/requirements.svg?branch=develop
     :target: https://requires.io/github/emory-libraries/pidmanclient/requirements/?branch=develop
     :alt: Requirements Status

**pidservices** provides a python module with client code for interacting
with the
`Pid Manager application <https://github.com/emory-libraries/pidman>`_
via REST API.

License
^^^^^^^

This software is distributed under the Apache 2.0 License.


Components
^^^^^^^^^^

.. note that using a ref here works fine, but it doesn't display
   correctly on the github repo homepage.

..:ref:`pidservices.clients <codedocs-client>`
``pidservices.clients``
    Python client for access to the pidman Rest API and utility methods
    for dealing with ARKs

..:ref:`pidservices.djangowrapper.shortcuts <django-shortcuts>`
``pidservices.djangowrapper.shortcuts``
    Convenience version of the REST API client initialized using
    Django settings

scripts
    The scripts directory includes some example scripts for batch processing
    pid actions, such as allocating a preseet number of ARKs or migrating
    a set of ARK target urls from one url pattern to another.


Testing
^^^^^^^

Tests can be run using `py.test <https://pytest.org/>`_ directly, or via
the setup script as `python setup.py test`.  For continuous
integration, enable coverage and xunit output like this::

    py.test --cov=pidservices --cov-report xml --junitxml=tests.xml