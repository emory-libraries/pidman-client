Overview
--------

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


Testing
^^^^^^^

Tests can be run using `py.test <https://pytest.org/>`_ directly, or via
the setup script as `python setup.py test`.  For continuous
integration, enable coverage and xunit output like this::

    py.test --cov=pidservices --cov-report xml --junitxml=tests.xml