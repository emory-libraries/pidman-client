Version Information
===================

Below is a summary of changes to the application.

1.2
---
* New script for allocating a block of pids at once: *allocate_pids*
* Update PidmanRestClient to use python-requests for HTTP calls

1.1.2
-----
* closed connection in _make_request

1.1.1
-----
* Added pid_token field.

1.1.0
-----
* Added a script (migrate_lsdi_arks.py) to migrate LSDI ark to fedora 3.4 format.

1.0.0
-----
Initial release of basic client with minimal functionality that allows it to
interact with the Pidman REST API.

* Can send queries to search PIDs or retrieve a list of most rescently updated
  pids if no search criteria is sent.
* Paging of search results for pid searches.
* Ability to search, retrieve and modify Domains.
* Ability to search, retrieve and modify ARKs and PURLs
* Provides a minimal Django wrapper for inclusion in Django apps.
