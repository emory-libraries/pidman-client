# To change this template, choose Tools | Templates
# and open the template in the editor.

from django.conf import settings

from pidservices.clients import PidmanRestClient

class DjangoPidmanRestClient(PidmanRestClient):
    """
    Wraps :class:`PidmanRestClient` to use Pidman host and connection
    information from the Django settings file instead of having to define it in
    the class call.

    NOTE:  The following values **MUST** be added to your project's django
    settings.py file for this class to work properly::

        PIDMAN_HOST = '' # base url for the pidman server to query. e.g.,
            ``http://pid.emory.edu/``
        PIDMAN_USER = '' # Username for authentication to the pidman app.
        PIDMAN_PASSWORD = '' # Pasword for username above.

    """

    def __init__(self):
        try:
            baseurl = settings.PIDMAN_HOST
            username = settings.PIDMAN_USER
            password = settings.PIDMAN_PASSWORD
            super(DjangoPidmanRestClient, self).__init__(baseurl, username, password)
        except AttributeError: # Raise error if values do not exist.
            errmsg = """
            Configuration Error!  The following values must be set in django
            settings.  PIDMAN_HOST, PIDMAN_USER, PIDMAN_PASSWORD

            See pidmanclient documentation for more information.
            """
            raise RuntimeError(errmsg)